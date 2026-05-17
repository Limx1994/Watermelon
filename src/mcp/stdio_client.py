"""Generic MCP stdio client - connects to MCP servers via subprocess stdin/stdout"""

import json
import logging
import os
import queue
import shutil
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional

from .base import BaseMCPClient
from .protocol import MCPProtocol, MCPError

logger = logging.getLogger(__name__)

# Stdio client constants
JSON_PARSE_FAIL_THRESHOLD = 10


class StdioMCPClient(BaseMCPClient):
    """MCP client that communicates with a server subprocess via stdin/stdout.

    Spawns a child process (e.g. via uvx, npx, node, python -m) and communicates
    using the MCP JSON-RPC 2.0 protocol over stdin/stdout.
    """

    def __init__(self, server_config: Dict[str, Any]):
        super().__init__(server_config)
        self.command: str = server_config.get("command", "")
        self.args: List[str] = server_config.get("args", [])
        self.env_override: Dict[str, str] = server_config.get("env", {})
        self.timeout: int = server_config.get("timeout", 30)
        self.auto_restart: bool = server_config.get("auto_restart", True)
        self._max_restart_attempts: int = server_config.get("max_restart_attempts", 10)

        # Runtime state
        self._process: Optional[subprocess.Popen] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._stderr_thread: Optional[threading.Thread] = None
        self._response_queue: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        self._stdin_lock: threading.Lock = threading.Lock()
        self._next_id: int = 0
        self._id_lock: threading.Lock = threading.Lock()
        self._connected: bool = False
        self._tools: List[Dict[str, Any]] = []
        self._restarting: bool = False
        self._shutdown: bool = False
        self._consecutive_json_failures: int = 0
        self._restart_count: int = 0
        self._last_restart_time: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        """Start the subprocess and perform MCP initialize handshake."""
        if self._connected:
            return True

        if not self.command:
            logger.error(f"MCP stdio client '{self.name}': no command configured")
            return False

        try:
            self._start_process()
            self._start_reader_thread()
            self._perform_handshake()
            self._discover_tools()
            self._connected = True
            # Successful connection resets restart counter
            self._restart_count = 0
            logger.info(f"MCP stdio client '{self.name}' connected (command: {self.command})")
            return True
        except Exception as e:
            logger.error(f"MCP stdio client '{self.name}' connection failed: {e}")
            self._cleanup(signal_reader=False)
            return False

    def disconnect(self) -> None:
        """Disconnect from the MCP server gracefully."""
        logger.info(f"MCP stdio client '{self.name}' disconnecting")
        self._connected = False
        self._shutdown = True  # Permanently disable auto-restart
        self._cleanup()

    def is_connected(self) -> bool:
        """Check if the MCP server is connected and healthy."""
        if not self._connected:
            return False

        if self._process and self._process.poll() is not None:
            rc = self._process.returncode
            logger.warning(f"MCP stdio server '{self.name}' exited (rc={rc})")
            self._connected = False
            self._tools = []
            self._cleanup()

            if self.auto_restart and not self._restarting and not self._shutdown:
                self._restart_count += 1
                if self._restart_count > self._max_restart_attempts:
                    logger.error(
                        f"MCP stdio server '{self.name}' exceeded max restart attempts "
                        f"({self._max_restart_attempts}), giving up"
                    )
                    return False

                # Exponential backoff: 1s, 2s, 4s, 8s, ... capped at 30s
                backoff = min(2 ** (self._restart_count - 1), 30)
                logger.info(
                    f"Auto-restarting MCP server '{self.name}' "
                    f"(attempt {self._restart_count}/{self._max_restart_attempts}, "
                    f"backoff={backoff}s, rc={rc})"
                )
                self._restarting = True
                self._last_restart_time = time.monotonic()
                time.sleep(backoff)
                try:
                    return self.connect()
                finally:
                    self._restarting = False

            return False

        return True

    def list_tools(self) -> List[Dict[str, Any]]:
        """Return cached tools discovered during connect()."""
        return list(self._tools)

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server and return the result."""
        if not self.is_connected():
            return {
                "success": False,
                "content": "",
                "error": f"MCP client '{self.name}' is not connected"
            }

        try:
            result = self._send_request("tools/call", {
                "name": tool_name,
                "arguments": arguments
            }, timeout=self.timeout)
            logger.info(f"MCP stdio call_tool: {tool_name} -> success={result.get('isError', False) is False}")

            # Parse MCP content items (array of {type, text, ...})
            content_items = result.get("content", [])
            text_parts = []
            for item in content_items:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))

            content = "\n".join(text_parts)
            is_error = result.get("isError", False)

            return {
                "success": not is_error,
                "content": content,
                "error": result.get("error") if is_error else None
            }
        except Exception as e:
            logger.error(f"MCP stdio call_tool '{tool_name}' failed: {type(e).__name__}: {e}")
            return {
                "success": False,
                "content": "",
                "error": str(e)
            }

    def get_all_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get tool definitions in OpenAI function-calling format."""
        tools = self.list_tools()
        return [
            {
                "type": "function",
                "function": {
                    "name": t.get("name", ""),
                    "description": t.get("description", ""),
                    "parameters": self._ensure_schema(
                        t.get("input_schema") or t.get("inputSchema")
                    )
                }
            }
            for t in tools
        ]

    # ------------------------------------------------------------------
    # Subprocess lifecycle
    # ------------------------------------------------------------------

    def _start_process(self) -> None:
        """Spawn the MCP server subprocess."""
        cmd = self._resolve_command(self.command)
        if cmd == self.command and not shutil.which(cmd):
            raise FileNotFoundError(
                f"MCP server command '{self.command}' not found in PATH. "
                f"Install it or remove '{self.name}' from mcp.json."
            )
        cmd_parts = [cmd] + self.args
        logger.info(f"MCP stdio spawning: {cmd_parts}")

        env = None
        if self.env_override:
            env = {**os.environ, **self.env_override}

        self._process = subprocess.Popen(
            cmd_parts,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env
        )

    @staticmethod
    def _resolve_command(command: str) -> str:
        """Resolve a command name to an executable path.

        On Windows, npm global scripts are .cmd files. subprocess.Popen
        doesn't resolve them via PATHEXT, so we use shutil.which() to
        find the actual file.
        """
        resolved = shutil.which(command)
        if resolved:
            return resolved
        # On Windows, try appending .cmd for npm global scripts
        if os.name == "nt":
            cmd_try = shutil.which(command + ".cmd")
            if cmd_try:
                return cmd_try
        return command

    def _start_reader_thread(self) -> None:
        """Start the daemon thread that reads stdout from the subprocess."""
        self._shutdown = False
        self._reader_thread = threading.Thread(
            target=self._reader_loop,
            daemon=True,
            name=f"mcp-reader-{self.name}"
        )
        self._reader_thread.start()

        # Start stderr reader to capture server-side diagnostic output
        if self._process and self._process.stderr:
            self._stderr_thread = threading.Thread(
                target=self._stderr_reader_loop,
                daemon=True,
                name=f"mcp-stderr-{self.name}"
            )
            self._stderr_thread.start()

    def _reader_loop(self) -> None:
        """Daemon thread: continuously read and parse JSON-RPC messages from stdout."""
        while not self._shutdown and self._process and self._process.stdout:
            try:
                line = self._process.stdout.readline()
                if not line:
                    # EOF - process has exited
                    break

                line = line.strip()
                if not line:
                    continue

                msg = json.loads(line)
                self._response_queue.put(msg)
                self._consecutive_json_failures = 0
            except json.JSONDecodeError:
                self._consecutive_json_failures += 1
                if self._consecutive_json_failures > JSON_PARSE_FAIL_THRESHOLD:
                    logger.error(f"MCP stdio '{self.name}': too many consecutive JSON parse failures ({self._consecutive_json_failures}), stopping reader")
                    break
                logger.warning(f"MCP stdio '{self.name}': malformed JSON received ({self._consecutive_json_failures}/{JSON_PARSE_FAIL_THRESHOLD}), skipping: {line[:100]}")
                continue
            except (BrokenPipeError, OSError, ValueError) as e:
                logger.warning(f"MCP stdio '{self.name}': reader stopped ({type(e).__name__}: {e})")
                break

    def _stderr_reader_loop(self) -> None:
        """Daemon thread: read stderr from subprocess and log it."""
        while not self._shutdown and self._process and self._process.stderr:
            try:
                line = self._process.stderr.readline()
                if not line:
                    break
                line = line.rstrip('\n').rstrip('\r')
                if line:
                    logger.warning(f"MCP server '{self.name}' stderr: {line}")
            except (BrokenPipeError, OSError, ValueError):
                break

    def _cleanup(self, signal_reader: bool = True) -> None:
        """Clean up subprocess resources.

        Args:
            signal_reader: If True, set _shutdown to stop reader threads.
                          False when called from connect() failure to allow auto-restart.
        """
        if signal_reader:
            self._shutdown = True
        proc = self._process
        if proc is None:
            return

        logger.info(f"Cleaning up MCP stdio '{self.name}', pid={proc.pid}")
        self._process = None

        # Close stdin to signal EOF to the process
        try:
            if proc.stdin:
                proc.stdin.close()
        except OSError:
            pass

        # Graceful termination
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
                proc.wait(timeout=3)
            except Exception:
                pass

        # Wait for reader threads to finish
        for thread in (self._reader_thread, self._stderr_thread):
            if thread and thread.is_alive():
                thread.join(timeout=2)

    # ------------------------------------------------------------------
    # MCP protocol: handshake and communication
    # ------------------------------------------------------------------

    def _perform_handshake(self) -> None:
        """Perform MCP initialize handshake with the server."""
        logger.debug(f"MCP stdio '{self.name}': performing handshake")
        request = MCPProtocol.create_initialize_request(
            client_info={"name": "AGImyCLI", "version": "1.0.0"},
            request_id=self._next_request_id()
        )
        result = self._send_raw_request(request, timeout=10)

        # Send initialized notification (no response expected)
        notification = MCPProtocol.create_initialized_notification()
        self._send_raw_notification(notification)

    def _discover_tools(self) -> None:
        """Discover available tools via tools/list."""
        result = self._send_request("tools/list", timeout=10)
        self._tools = result.get("tools", [])
        tool_names = [t.get("name", "?") for t in self._tools]
        logger.info(f"MCP stdio discovered {len(self._tools)} tools: {tool_names}")

    def _send_request(self, method: str, params: Any = None, timeout: Optional[int] = None) -> Any:
        """Send a JSON-RPC request and wait for the response."""
        request = MCPProtocol.create_request(method, params, request_id=self._next_request_id())
        return self._send_raw_request(request, timeout=timeout or self.timeout)

    def _send_raw_request(self, request: Dict[str, Any], timeout: int) -> Any:
        """Write a request dict to stdin and wait for the matching response."""
        if not self._process or not self._process.stdin:
            raise ConnectionError("MCP subprocess not available")

        req_id = request.get("id")
        payload = json.dumps(request, ensure_ascii=False)

        with self._stdin_lock:
            self._process.stdin.write(payload + "\n")
            self._process.stdin.flush()

        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                # Do NOT drain the queue — messages may belong to other concurrent requests.
                # The reader thread will continue populating the queue, and other callers
                # will consume their own matching responses.
                logger.warning(
                    f"MCP request timed out after {timeout}s "
                    f"(method: {request.get('method')}, req_id={req_id})"
                )
                raise TimeoutError(f"MCP request timed out after {timeout}s (method: {request.get('method')})")

            try:
                msg = self._response_queue.get(timeout=min(0.1, remaining))
            except queue.Empty:
                continue

            # Skip notifications (no id)
            if MCPProtocol.is_notification(msg):
                continue

            # Skip responses that don't match our request id
            if msg.get("id") != req_id:
                continue

            # Check for JSON-RPC error
            if MCPProtocol.is_error_response(msg):
                err = msg["error"]
                raise MCPError(
                    message=err.get("message", "Unknown error"),
                    code=err.get("code", -1),
                    data=err.get("data")
                )

            return msg.get("result")

    def _send_raw_notification(self, notification: Dict[str, Any]) -> None:
        """Write a notification dict to stdin (no response expected)."""
        if not self._process or not self._process.stdin:
            return

        payload = json.dumps(notification, ensure_ascii=False)
        try:
            with self._stdin_lock:
                self._process.stdin.write(payload + "\n")
                self._process.stdin.flush()
        except (BrokenPipeError, OSError) as e:
            logger.warning(f"MCP stdio '{self.name}': notification failed ({type(e).__name__}: {e})")

    def _next_request_id(self) -> int:
        """Get the next monotonically increasing request ID."""
        with self._id_lock:
            self._next_id += 1
            return self._next_id
