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
from .protocol import MCPProtocol


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

        # Runtime state
        self._process: Optional[subprocess.Popen] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._response_queue: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        self._stdin_lock: threading.Lock = threading.Lock()
        self._next_id: int = 0
        self._connected: bool = False
        self._tools: List[Dict[str, Any]] = []
        self._server_info: Dict[str, Any] = {}
        self._server_capabilities: Dict[str, Any] = {}
        self._restarting: bool = False
        self._shutdown: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        """Start the subprocess and perform MCP initialize handshake."""
        if self._connected:
            return True

        if not self.command:
            logging.error(f"MCP stdio client '{self.name}': no command configured")
            return False

        try:
            self._start_process()
            self._start_reader_thread()
            self._perform_handshake()
            self._discover_tools()
            self._connected = True
            logging.info(f"MCP stdio client '{self.name}' connected (command: {self.command})")
            return True
        except Exception as e:
            logging.error(f"MCP stdio client '{self.name}' connection failed: {e}")
            self._cleanup()
            return False

    def disconnect(self) -> None:
        """Disconnect from the MCP server gracefully."""
        self._connected = False
        self._shutdown = True
        self._cleanup()

    def is_connected(self) -> bool:
        """Check if the MCP server is connected and healthy."""
        if not self._connected:
            return False

        if self._process and self._process.poll() is not None:
            rc = self._process.returncode
            logging.warning(f"MCP stdio server '{self.name}' exited (rc={rc})")
            self._connected = False
            self._tools = []
            self._cleanup()

            if self.auto_restart and not self._restarting and not self._shutdown:
                self._restarting = True
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
        cmd_parts = [cmd] + self.args

        env = None
        if self.env_override:
            env = {**os.environ, **self.env_override}

        self._process = subprocess.Popen(
            cmd_parts,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
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
            except json.JSONDecodeError:
                logging.warning(f"MCP stdio '{self.name}': malformed JSON received, skipping: {line[:100]}")
                continue
            except (BrokenPipeError, OSError, ValueError):
                break

    def _cleanup(self) -> None:
        """Clean up subprocess resources."""
        proc = self._process
        if proc is None:
            return

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

    # ------------------------------------------------------------------
    # MCP protocol: handshake and communication
    # ------------------------------------------------------------------

    def _perform_handshake(self) -> None:
        """Perform MCP initialize handshake with the server."""
        request = MCPProtocol.create_initialize_request(
            client_info={"name": "AGImyCLI", "version": "1.0.0"},
            request_id=self._next_request_id()
        )
        result = self._send_raw_request(request, timeout=10)
        self._server_info = result.get("serverInfo", {})
        self._server_capabilities = result.get("capabilities", {})

        # Send initialized notification (no response expected)
        notification = MCPProtocol.create_initialized_notification()
        self._send_raw_notification(notification)

    def _discover_tools(self) -> None:
        """Discover available tools via tools/list."""
        result = self._send_request("tools/list", timeout=10)
        self._tools = result.get("tools", [])

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
        except (BrokenPipeError, OSError):
            pass

    def _next_request_id(self) -> int:
        """Get the next monotonically increasing request ID."""
        self._next_id += 1
        return self._next_id
