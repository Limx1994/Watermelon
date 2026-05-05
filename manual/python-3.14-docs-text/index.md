# Python 3.14 文档（文本版）索引

> 源文件：Python 3.14 官方文档转换为纯文本格式（.txt），按主题分目录组织。

## 目录结构总览

```
python-3.14-docs-text/
├── contents.txt          # 完整目录（~12K 行，导航核心）
├── glossary.txt          # 术语表
├── license.txt           # 许可证
├── about.txt             # 关于 Python
├── bugs.txt              # 报告 Bug
├── copyright.txt         # 版权信息
├── improve-page.txt      # 改进文档
├── improve-page-nojs.txt # 改进文档（无 JS）
│
├── tutorial/             # 入门教程
├── library/              # 标准库参考（核心，326 个文件）
├── reference/            # 语言参考
├── howto/                # 操作指南
├── c-api/                # C API 参考
├── extending/            # 扩展与嵌入
├── using/                # Python 使用指南
├── installing/           # 安装 Python
├── distributing/         # 分发 Python 包
├── faq/                  # 常见问题
├── whatsnew/             # 版本新特性
└── deprecations/         # 弃用与移除计划
```

---

## 顶层文件

| 文件 | 说明 |
|------|------|
| `contents.txt` | 完整文档目录/大纲（11818 行），是导航的核心入口 |
| `glossary.txt` | 术语表，解释关键术语 |
| `license.txt` | Python 软件基金会许可证 |
| `about.txt` | 关于 Python 的概述 |
| `bugs.txt` | Bug 报告指南 |
| `copyright.txt` | 版权声明 |
| `improve-page.txt` | 如何改进文档 |
| `improve-page-nojs.txt` | 改进文档（无 JavaScript 版本） |

---

## `tutorial/` — Python 入门教程

适合初学者从头学习 Python。

| 文件 | 说明 |
|------|------|
| `index.txt` | 教程索引 |
| `appetite.txt` | 前言：Python 的诱惑 |
| `introduction.txt` | Python 简介 |
| `interpreter.txt` | 解释器使用 |
| `interactive.txt` | 交互模式 |
| `controlflow.txt` | 流程控制 |
| `datastructures.txt` | 数据结构 |
| `modules.txt` | 模块 |
| `inputoutput.txt` | 输入输出 |
| `errors.txt` | 错误与异常 |
| `classes.txt` | 类 |
| `stdlib.txt` | 标准库简介 |
| `stdlib2.txt` | 标准库简介（二） |
| `floatingpoint.txt` | 浮点数算术 |
| `appendix.txt` | 附录 |
| `venv.txt` | 虚拟环境 |
| `whatnow.txt` | 下一步 |

---

## `library/` — 标准库参考（326 个文件）

按功能分类的文件索引：

### 基础与语言服务

| 文件 | 说明 |
|------|------|
| `__future__.txt` | `__future__` — Future 语句定义 |
| `__main__.txt` | `__main__` — 顶层脚本环境 |
| `builtins.txt` | `builtins` — 内建对象 |
| `constants.txt` | 内建常量 |
| `exceptions.txt` | 内建异常 |
| `functions.txt` | 内建函数 |
| `stdtypes.txt` | 内建类型 |
| `keyword.txt` | `keyword` — Python 关键字 |
| `token.txt` | `token` — 令牌常量 |
| `tokenize.txt` | `tokenize` — Python 源码分词器 |
| `symtable.txt` | `symtable` — 符号表访问 |
| `code.txt` | `code` — 解释器基类 |
| `codeop.txt` | `codeop` — 编译 Python 代码 |
| `types.txt` | `types` — 动态类型创建与命名 |
| `inspect.txt` | `inspect` — 活动对象检查 |
| `dis.txt` | `dis` — 字节码反汇编器 |
| `pickle.txt` | `pickle` — Python 对象序列化 |
| `copy.txt` | `copy` — 浅拷贝与深拷贝 |
| `marshal.txt` | `marshal` — 内部对象序列化 |
| `shelve.txt` | `shelve` — Python 对象持久化 |
| `py_compile.txt` | `py_compile` — 编译 Python 源文件 |
| `compileall.txt` | `compileall` — 批量编译 |
| `linecache.txt` | `linecache` — 随机读取文本行 |
| `traceback.txt` | `traceback` — 回溯信息处理 |
| `warnings.txt` | `warnings` — 警告控制 |
| `dataclasses.txt` | `dataclasses` — 数据类 |
| `enum.txt` | `enum` — 枚举类型 |
| `pprint.txt` | `pprint` — 漂亮打印 |
| `textwrap.txt` | `textwrap` — 文本填充与换行 |
| `string.txt` | `string` — 字符串操作 |
| `string.templatelib.txt` | `string.templatelib` — 模板字符串 |
| `re.txt` | `re` — 正则表达式 |

### 数据类型与算法

| 文件 | 说明 |
|------|------|
| `array.txt` | `array` — 高效数值数组 |
| `bisect.txt` | `bisect` — 数组二分查找 |
| `calendar.txt` | `calendar` — 日历相关函数 |
| `collections.txt` | `collections` — 容器数据类型 |
| `collections.abc.txt` | `collections.abc` — 容器抽象基类 |
| `datetime.txt` | `datetime` — 日期时间 |
| `decimal.txt` | `decimal` — 十进制浮点数 |
| `fractions.txt` | `fractions` — 分数 |
| `graphlib.txt` | `graphlib` — 图算法 |
| `hashlib.txt` | `hashlib` — 安全哈希与消息摘要 |
| `heapq.txt` | `heapq` — 堆队列算法 |
| `ipaddress.txt` | `ipaddress` — IP 地址处理 |
| `numbers.txt` | `numbers` — 数值抽象基类 |
| `random.txt` | `random` — 生成伪随机数 |
| `secrets.txt` | `secrets` — 生成安全随机数 |
| `statistics.txt` | `statistics` — 数学统计 |
| `math.txt` | `math` — 数学函数 |
| `cmath.txt` | `cmath` — 复数数学 |
| `itertools.txt` | `itertools` — 迭代器函数 |
| `functools.txt` | `functools` — 高阶函数与操作 |
| `operator.txt` | `operator` — 标准运算符函数 |
| `struct.txt` | `struct` — 解释字节串为打包数据 |
| `difflib.txt` | `difflib` — 差异计算工具 |

### 文件系统与存储

| 文件 | 说明 |
|------|------|
| `os.path.txt` | `os.path` — 路径操作 |
| `pathlib.txt` | `pathlib` — 面向对象文件系统路径 |
| `glob.txt` | `glob` — Unix 风格路径展开 |
| `fnmatch.txt` | `fnmatch` — Unix 文件名匹配 |
| `fileinput.txt` | `fileinput` — 遍历多个文件 |
| `filecmp.txt` | `filecmp` — 文件与目录比较 |
| `tempfile.txt` | `tempfile` — 临时文件/目录 |
| `shutil.txt` | `shutil` — 高级文件操作 |
| `stat.txt` | `stat` — 解释 `stat()` 结果 |
| `zipfile.txt` | `zipfile` — ZIP 归档操作 |
| `tarfile.txt` | `tarfile` — TAR 归档操作 |
| `gzip.txt` | `gzip` — gzip 压缩 |
| `bz2.txt` | `bz2` — bzip2 压缩 |
| `lzma.txt` | `lzma` — LZMA 压缩 |
| `zlib.txt` | `zlib` — zlib 压缩 |
| `zipimport.txt` | `zipimport` — 从 ZIP 导入模块 |
| `mmap.txt` | `mmap` — 内存映射文件 |

### 数据序列化与交换

| 文件 | 说明 |
|------|------|
| `json.txt` | `json` — JSON 编解码 |
| `tomllib.txt` | `tomllib` — TOML 解析 |
| `configparser.txt` | `configparser` — 配置文件解析 |
| `csv.txt` | `csv` — CSV 文件读写 |
| `xml.txt` | XML 处理概述 |
| `xml.dom.txt` | XML DOM API |
| `xml.dom.minidom.txt` | 最小化 DOM 实现 |
| `xml.dom.pulldom.txt` | 拉式 DOM 解析 |
| `xml.etree.elementtree.txt` | ElementTree XML API |
| `xml.sax.txt` | SAX 解析器 |
| `xml.sax.handler.txt` | SAX 处理器基类 |
| `xml.sax.reader.txt` | SAX 解析器接口 |
| `xml.sax.utils.txt` | SAX 工具函数 |
| `html.txt` | HTML 处理概述 |
| `html.parser.txt` | HTML 解析器 |
| `html.entities.txt` | HTML 实体定义 |

### 网络与进程通信

| 文件 | 说明 |
|------|------|
| `socket.txt` | `socket` — 底层网络接口 |
| `ssl.txt` | `ssl` — SSL/TLS 加密 |
| `select.txt` | `select` — I/O 多路复用 |
| `selectors.txt` | `selectors` — 高级 I/O 复用 |
| `asyncio.txt` | `asyncio` — 异步 I/O（主文档） |
| `asyncio-api-index.txt` | asyncio API 索引 |
| `asyncio-dev.txt` | asyncio 开发指南 |
| `asyncio-eventloop.txt` | asyncio 事件循环 |
| `asyncio-exceptions.txt` | asyncio 异常 |
| `asyncio-extending.txt` | 扩展 asyncio |
| `asyncio-future.txt` | asyncio Future |
| `asyncio-graph.txt` | asyncio 设计图 |
| `asyncio-llapi-index.txt` | asyncio 底层 API 索引 |
| `asyncio-platforms.txt` | asyncio 平台支持 |
| `asyncio-policy.txt` | asyncio 策略 |
| `asyncio-protocol.txt` | asyncio 协议 |
| `asyncio-queue.txt` | asyncio 队列 |
| `asyncio-runner.txt` | asyncio Runner |
| `asyncio-stream.txt` | asyncio 流 |
| `asyncio-subprocess.txt` | asyncio 子进程 |
| `asyncio-sync.txt` | asyncio 同步原语 |
| `asyncio-task.txt` | asyncio 任务 |
| `signal.txt` | `signal` — 信号处理 |
| `subprocess.txt` | `subprocess` — 子进程管理 |
| `threading.txt` | `threading` — 线程并行 |
| `concurrency.txt` | 并发执行总览 |
| `concurrent.futures.txt` | `concurrent.futures` — 线程/进程池 |
| `concurrent.interpreters.txt` | `concurrent.interpreters` — 隔离解释器 |
| `multiprocessing.txt` | `multiprocessing` — 进程并行 |
| `multiprocessing.shared_memory.txt` | 共享内存 |
| `queue.txt` | `queue` — 同步队列 |
| `sched.txt` | `sched` — 事件调度器 |
| `contextvars.txt` | `contextvars` — 上下文变量 |

### 互联网协议

| 文件 | 说明 |
|------|------|
| `http.txt` | HTTP 模块概述 |
| `http.client.txt` | HTTP 客户端 |
| `http.server.txt` | HTTP 服务器 |
| `http.cookies.txt` | HTTP Cookie |
| `http.cookiejar.txt` | Cookie Jar |
| `urllib.txt` | URL 处理概述 |
| `urllib.request.txt` | URL 打开与读取 |
| `urllib.parse.txt` | URL 解析 |
| `urllib.error.txt` | URL 异常 |
| `urllib.robotparser.txt` | robots.txt 解析 |
| `ftplib.txt` | FTP 客户端 |
| `poplib.txt` | POP3 客户端 |
| `imaplib.txt` | IMAP4 客户端 |
| `smtplib.txt` | SMTP 客户端 |
| `nntplib.txt` | NNTP 客户端 |
| `telnetlib.txt` | Telnet 客户端 |
| `xmlrpc.txt` | XML-RPC 概述 |
| `xmlrpc.client.txt` | XML-RPC 客户端 |
| `xmlrpc.server.txt` | XML-RPC 服务器 |
| `cgi.txt` | CGI 脚本支持 |
| `socketserver.txt` | 网络服务器框架 |
| `wsgiref.txt` | WSGI 参考 |
| `webbrowser.txt` | 浏览器控制器 |

### 邮件与消息处理

| 文件 | 说明 |
|------|------|
| `email.txt` | 电子邮件处理 |
| `email.charset.txt` | 字符集 |
| `email.compat32-message.txt` | 兼容消息 API |
| `email.contentmanager.txt` | 内容管理器 |
| `email.encoders.txt` | 编码器 |
| `email.errors.txt` | 异常与缺陷 |
| `email.examples.txt` | 示例 |
| `email.generator.txt` | 生成 MIME 文档 |
| `email.header.txt` | 国际化标题 |
| `email.headerregistry.txt` | 标题注册表 |
| `email.iterators.txt` | 迭代器 |
| `email.message.txt` | 消息表示 |
| `email.mime.txt` | MIME 对象 |
| `email.parser.txt` | 解析 |
| `email.policy.txt` | 策略 |
| `email.utils.txt` | 工具函数 |
| `mailbox.txt` | 邮箱操作 |
| `mailcap.txt` | mailcap 处理 |
| `json.txt` | JSON 编解码 |

### 结构化标记处理

| 文件 | 说明 |
|------|------|
| `html.txt` | HTML 处理 |
| `html.parser.txt` | HTML 解析器 |
| `html.entities.txt` | HTML 实体 |
| `xml.txt` | XML 处理 |
| `xml.dom.txt` | DOM API |
| `xml.dom.minidom.txt` | 轻量 DOM |
| `xml.dom.pulldom.txt` | 拉式 DOM |
| `xml.etree.elementtree.txt` | ElementTree |
| `xml.sax.txt` | SAX 解析 |
| `xml.sax.handler.txt` | SAX 处理器 |
| `xml.sax.reader.txt` | SAX 读取器 |
| `xml.sax.utils.txt` | SAX 工具 |

### 多媒体

| 文件 | 说明 |
|------|------|
| `audioop.txt` | `audioop` — 音频数据处理 |
| `aifc.txt` | AIFF 文件读写 |
| `sunau.txt` | Sun AU 文件读写 |
| `wave.txt` | WAV 文件读写 |
| `chunk.txt` | IFF 块读取 |
| `colorsys.txt` | 颜色系统转换 |
| `imghdr.txt` | 图像类型识别 |
| `sndhdr.txt` | 声音文件类型识别 |
| `turtle.txt` | Turtle 图形库 |
| `ossaudiodev.txt` | OSS 音频设备 |

### 国际化

| 文件 | 说明 |
|------|------|
| `locale.txt` | `locale` — 国际化服务 |
| `gettext.txt` | `gettext` — 消息翻译 |
| `unicodedata.txt` | `unicodedata` — Unicode 数据库 |
| `stringprep.txt` | `stringprep` — Unicode 字符串准备 |

### 开发工具

| 文件 | 说明 |
|------|------|
| `pdb.txt` | `pdb` — 调试器 |
| `profile.txt` | `profile` / `cProfile` — 性能分析 |
| `timeit.txt` | `timeit` — 小段代码计时 |
| `trace.txt` | `trace` — 代码执行跟踪 |
| `tracemalloc.txt` | `tracemalloc` — 内存分配跟踪 |
| `devmode.txt` | 开发模式 |
| `doctest.txt` | `doctest` — 文档测试 |
| `unittest.txt` | `unittest` — 单元测试框架 |
| `unittest.mock.txt` | `unittest.mock` — Mock 对象 |
| `unittest.mock-examples.txt` | Mock 使用示例 |
| `test.txt` | `test` — Python 回归测试包 |
| `bdb.txt` | `bdb` — 调试器框架 |
| `faulthandler.txt` | `faulthandler` — 故障处理 |
| `pyclbr.txt` | `pyclbr` — Python 类浏览 |
| `pydoc.txt` | `pydoc` — 文档生成 |
| `venv.txt` | `venv` — 虚拟环境 |
| `ensurepip.txt` | `ensurepip` — pip 安装引导 |
| `zipapp.txt` | `zipapp` — 可执行 ZIP 归档 |

### 调试与诊断

| 文件 | 说明 |
|------|------|
| `audit_events.txt` | 审计事件表 |
| `sys.monitoring.txt` | `sys.monitoring` — 执行监控 |
| `faulthandler.txt` | 故障处理 |
| `tracemalloc.txt` | 内存跟踪 |
| `devmode.txt` | Python 开发模式 |

### 运行时服务

| 文件 | 说明 |
|------|------|
| `sys.txt` | `sys` — 系统参数与函数 |
| `sysconfig.txt` | `sysconfig` — Python 配置 |
| `sys_path_init.txt` | `sys.path` 初始化 |
| `atexit.txt` | `atexit` — 退出处理器 |
| `gc.txt` | `gc` — 垃圾回收器 |
| `site.txt` | `site` — 站点配置 |
| `platform.txt` | `platform` — 平台信息 |
| `errno.txt` | `errno` — 系统错误码 |
| `ctypes.txt` | `ctypes` — C 函数外部调用 |
| `importlib.txt` | `importlib` — 导入系统实现 |
| `importlib.metadata.txt` | 包元数据访问 |
| `importlib.resources.txt` | 包资源访问 |
| `importlib.resources.abc.txt` | 资源抽象基类 |
| `imp.txt` | `imp` — 导入内部（已弃用） |
| `pkgutil.txt` | `pkgutil` — 包扩展工具 |
| `modulefinder.txt` | `modulefinder` — 模块查找器 |
| `runpy.txt` | `runpy` — 脚本执行 |
| `rlcompleter.txt` | `rlcompleter` — readline 补全 |

### 交互式输入与界面

| 文件 | 说明 |
|------|------|
| `readline.txt` | `readline` — GNU Readline |
| `rlcompleter.txt` | 交互补全 |
| `cmd.txt` | `cmd` — 行式命令解释器 |
| `shlex.txt` | `shlex` — Shell 风格词法分析 |
| `getopt.txt` | `getopt` — 命令行选项解析 |
| `optparse.txt` | `optparse` — 弃用的选项解析 |
| `argparse.txt` | `argparse` — 命令行参数解析 |
| `getpass.txt` | `getpass` — 密码输入 |

### Tk GUI

| 文件 | 说明 |
|------|------|
| `tk.txt` | Tk GUI 总览 |
| `tkinter.txt` | Tkinter — Python Tcl/Tk 接口 |
| `tkinter.colorchooser.txt` | 颜色选择 |
| `tkinter.dnd.txt` | 拖放 |
| `tkinter.font.txt` | 字体 |
| `tkinter.messagebox.txt` | 消息框 |
| `tkinter.scrolledtext.txt` | 滚动文本 |
| `tkinter.ttk.txt` | 主题化 Tk 组件 |
| `idle.txt` | IDLE 开发环境 |

### 操作系统接口

| 文件 | 说明 |
|------|------|
| `os.txt` | `os` — 操作系统接口 |
| `io.txt` | `io` — 流式 I/O |
| `time.txt` | `time` — 时间访问与转换 |
| `argparse.txt` | `argparse` — 参数解析 |
| `getopt.txt` | `getopt` — 选项解析 |
| `logging.txt` | `logging` — 日志系统 |
| `logging.config.txt` | 日志配置 |
| `logging.handlers.txt` | 日志处理器 |
| `gettext.txt` | 消息翻译 |
| `locale.txt` | 本地化 |

### Windows 专用

| 文件 | 说明 |
|------|------|
| `msilib.txt` | `msilib` — MSI 安装包创建 |
| `msvcrt.txt` | `msvcrt` — MS VC++ 运行时 |
| `winreg.txt` | `winreg` — Windows 注册表 |
| `winsound.txt` | `winsound` — Windows 音频播放 |

### Unix 专用

| 文件 | 说明 |
|------|------|
| `posix.txt` | `posix` — POSIX 系统调用 |
| `pwd.txt` | `pwd` — 密码数据库 |
| `grp.txt` | `grp` — 组数据库 |
| `spwd.txt` | `spwd` — 影子密码 |
| `termios.txt` | `termios` — POSIX 终端控制 |
| `tty.txt` | `tty` — 终端控制函数 |
| `pty.txt` | `pty` — 伪终端 |
| `fcntl.txt` | `fcntl` — 文件描述符控制 |
| `resource.txt` | `resource` — 资源使用限制 |
| `nis.txt` | `nis` — NIS 接口 |
| `syslog.txt` | `syslog` — Unix syslog |
| `crypt.txt` | `crypt` — 密码验证（已弃用） |
| `pipes.txt` | `pipes` — Shell 管道接口 |

### 其他模块

| 文件 | 说明 |
|------|------|
| `tabnanny.txt` | `tabnanny` — 缩进检查 |
| `pyexpat.txt` | `pyexpat` — Expat XML 解析 |
| `base64.txt` | `base64` — Base16/32/64 编解码 |
| `binascii.txt` | `binascii` — 二进制/ASCII 转换 |
| `quopri.txt` | `quopri` — quoted-printable 编解码 |
| `uu.txt` | `uu` — uuencode 编解码 |
| `binhex.txt` | `binhex` — BinHex 编解码 |
| `xdrlib.txt` | `xdrlib` — XDR 编解码 |
| `mailcap.txt` | `mailcap` — mailcap 处理 |
| `netrc.txt` | `netrc` — netrc 文件处理 |
| `plistlib.txt` | `plistlib` — macOS plist 处理 |
| `uuid.txt` | `uuid` — UUID 生成 |
| `dbm.txt` | `dbm` — Unix 数据库接口 |
| `sqlite3.txt` | `sqlite3` — SQLite 数据库 |
| `__future__.txt` | Future 语句 |
| `__main__.txt` | 顶层脚本环境 |
| `_thread.txt` | 底层线程 API |

### 分类索引文件

| 文件 | 说明 |
|------|------|
| `index.txt` | 模块索引 |
| `allos.txt` | 操作系统服务概览 |
| `archiving.txt` | 归档模块 |
| `binary.txt` | 二进制数据服务 |
| `concurrency.txt` | 并发执行 |
| `compression.txt` | 数据压缩 |
| `compression.zstd.txt` | Zstd 压缩 |
| `constants.txt` | 内建常量 |
| `crypto.txt` | 加密服务 |
| `custominterp.txt` | 自定义解释器 |
| `datatypes.txt` | 数据类型 |
| `debug.txt` | 调试与分析 |
| `development.txt` | 开发工具 |
| `dialog.txt` | 对话框 |
| `distribution.txt` | 软件分发 |
| `filesys.txt` | 文件系统 |
| `fileformats.txt` | 文件格式 |
| `frameworks.txt` | 框架 |
| `functional.txt` | 函数式编程 |
| `i18n.txt` | 国际化 |
| `internet.txt` | 互联网协议 |
| `intro.txt` | 库简介 |
| `ipc.txt` | 进程间通信 |
| `language.txt` | 语言服务 |
| `markup.txt` | 标记处理 |
| `mm.txt` | 多媒体服务 |
| `modules.txt` | 模块导入 |
| `netdata.txt` | 网络数据 |
| `numeric.txt` | 数值与数学 |
| `persistence.txt` | 持久化 |
| `python.txt` | Python 运行时 |
| `removed.txt` | 已移除模块 |
| `security_warnings.txt` | 安全警告 |
| `superseded.txt` | 被取代模块 |
| `text.txt` | 文本处理 |
| `threadsafety.txt` | 线程安全 |
| `tk.txt` | Tk GUI |
| `unix.txt` | Unix 服务 |
| `windows.txt` | Windows 服务 |

---

## `reference/` — 语言参考

| 文件 | 说明 |
|------|------|
| `index.txt` | 语言参考索引 |
| `introduction.txt` | 引言 |
| `lexical_analysis.txt` | 词法分析 |
| `datamodel.txt` | 数据模型 |
| `executionmodel.txt` | 执行模型 |
| `import.txt` | 导入系统 |
| `expressions.txt` | 表达式 |
| `simple_stmts.txt` | 简单语句 |
| `compound_stmts.txt` | 复合语句 |
| `toplevel_components.txt` | 顶层组件 |
| `grammar.txt` | 语法文件 |

---

## `howto/` — 操作指南

| 文件 | 说明 |
|------|------|
| `index.txt` | 指南索引 |
| `a-conceptual-overview-of-asyncio.txt` | asyncio 概念概述 |
| `annotations.txt` | 注解最佳实践 |
| `argparse.txt` | 命令行解析教程 |
| `argparse-optparse.txt` | argparse 到 optparse 迁移 |
| `clinic.txt` | Argument Clinic |
| `cporting.txt` | C 扩展移植 |
| `curses.txt` | Curses 编程 |
| `descriptor.txt` | 描述符指南 |
| `enum.txt` | 枚举指南 |
| `free-threading-extensions.txt` | 自由线程 C 扩展 |
| `free-threading-python.txt` | 自由线程 Python |
| `functional.txt` | 函数式编程 |
| `gdb_helpers.txt` | GDB 辅助 |
| `instrumentation.txt` | 插桩 |
| `ipaddress.txt` | IP 地址指南 |
| `isolating-extensions.txt` | 隔离 C 扩展 |
| `logging.txt` | 日志指南 |
| `logging-cookbook.txt` | 日志食谱 |
| `mro.txt` | MRO 解析顺序 |
| `perf_profiling.txt` | 性能分析 |
| `pyporting.txt` | Python 2→3 移植 |
| `regex.txt` | 正则表达式指南 |
| `remote_debugging.txt` | 远程调试 |
| `sockets.txt` | Socket 编程 |
| `sorting.txt` | 排序技巧 |
| `timerfd.txt` | 定时器文件描述符 |
| `unicode.txt` | Unicode 指南 |
| `urllib2.txt` | urllib 使用 |

---

## `c-api/` — C API 参考

| 文件 | 说明 |
|------|------|
| `abstract.txt` | 抽象对象层 |
| `allocation.txt` | 内存分配 |
| `apiabiversion.txt` | API/ABI 版本 |
| `arg.txt` | 参数解析 |
| `bool.txt` | 布尔对象 |
| `buffer.txt` | Buffer 协议 |
| `bytearray.txt` | Bytearray 对象 |
| `bytes.txt` | Bytes 对象 |
| `call.txt` | 调用协议 |
| `capsule.txt` | Capsule 对象 |
| `cell.txt` | Cell 对象 |
| `code.txt` | Code 对象 |
| `codec.txt` | 编解码器 |
| `complex.txt` | 复数对象 |
| `concrete.txt` | 具体对象层 |
| `contextvars.txt` | 上下文变量 |
| `conversion.txt` | 类型转换 |
| `coro.txt` | 协程对象 |
| `curses.txt` | Curses C API |
| `datetime.txt` | 日期时间 C API |
| `descriptor.txt` | 描述符对象 |
| `dict.txt` | 字典对象 |
| `exceptions.txt` | 异常处理 |
| `extension-modules.txt` | 扩展模块 |
| `file.txt` | 文件对象 |
| `float.txt` | 浮点对象 |
| `frame.txt` | 帧对象 |
| `function.txt` | 函数对象 |
| `gcsupport.txt` | 垃圾回收支持 |
| `gen.txt` | 生成器对象 |
| `import.txt` | 导入 API |
| `init.txt` | 初始化 |
| `int.txt` | 整数对象 |
| `intro.txt` | C API 引言 |
| `iter.txt` | 迭代器协议 |
| `list.txt` | 列表对象 |
| `long.txt` | 长整数对象 |
| `mapping.txt` | 映射协议 |
| `marshal.txt` | Marshal C API |
| `memory.txt` | 内存管理 |
| `memoryview.txt` | 内存视图 |
| `method.txt` | 方法对象 |
| `module.txt` | 模块对象 |
| `none.txt` | None 对象 |
| `numbers.txt` | 数字协议 |
| `obj.txt` | 对象协议 |
| `object.txt` | 对象实现 |
| `perf_profiling.txt` | 性能分析 |
| `refcounting.txt` | 引用计数 |
| `reflection.txt` | 反射 |
| `sequence.txt` | 序列协议 |
| `set.txt` | Set 对象 |
| `slice.txt` | Slice 对象 |
| `stable.txt` | 稳定 ABI |
| `str.txt` | 字符串对象 |
| `struct.txt` | 结构体成员 |
| `structures.txt` | 结构体类型 |
| `sys.txt` | 系统调用 |
| `thread.txt` | 线程支持 |
| `traceback.txt` | 回溯对象 |
| `transports.txt` | 传输 |
| `tuple.txt` | 元组对象 |
| `type.txt` | 类型对象 |
| `typeobj.txt` | 类型对象实现 |
| `unicode.txt` | Unicode C API |
| `vars.txt` | 变量 |
| `weakref.txt` | 弱引用 |

---

## `extending/` — 扩展与嵌入

| 文件 | 说明 |
|------|------|
| `index.txt` | 扩展与嵌入索引 |
| `extending.txt` | 用 C 扩展 Python |
| `embedding.txt` | 在其他应用嵌入 Python |
| `building.txt` | 构建 C/C++ 扩展 |
| `newtypes.txt` | 创建新类型 |
| `newtypes_tutorial.txt` | 新类型教程 |
| `windows.txt` | Windows 编译 |

---

## `using/` — Python 使用指南

| 文件 | 说明 |
|------|------|
| `index.txt` | 使用指南索引 |
| `cmdline.txt` | 命令行与环境 |
| `windows.txt` | Windows 使用 |
| `mac.txt` | macOS 使用 |
| `unix.txt` | Unix 使用 |
| `editors.txt` | 编辑器支持 |
| `android.txt` | Android 使用 |
| `ios.txt` | iOS 使用 |
| `configure.txt` | 编译配置 |

---

## `installing/` — 安装指南

| 文件 | 说明 |
|------|------|
| `index.txt` | 安装指南索引 |

---

## `distributing/` — 分发指南

| 文件 | 说明 |
|------|------|
| `index.txt` | 分发指南索引 |

---

## `faq/` — 常见问题

| 文件 | 说明 |
|------|------|
| `index.txt` | FAQ 索引 |
| `general.txt` | 通用问题 |
| `programming.txt` | 编程问题 |
| `design.txt` | 设计与历史 |
| `library.txt` | 库与模块 |
| `extending.txt` | 扩展问题 |
| `windows.txt` | Windows 相关 |
| `gui.txt` | GUI 相关 |
| `installed.txt` | 安装问题 |

---

## `whatsnew/` — 版本新特性

| 文件 | 说明 |
|------|------|
| `index.txt` | 新特性索引 |
| `3.14.txt` | Python 3.14 新特性 |
| `3.13.txt` | Python 3.13 新特性 |
| `3.12.txt` | Python 3.12 新特性 |
| `3.11.txt` | Python 3.11 新特性 |
| `3.10.txt` | Python 3.10 新特性 |
| `3.9.txt` ～ `3.0.txt` | Python 3.x 各版本新特性 |
| `2.7.txt` ～ `2.0.txt` | Python 2.x 各版本新特性 |
| `changelog.txt` | 更新日志 |

---

## `deprecations/` — 弃用与移除计划

| 文件 | 说明 |
|------|------|
| `index.txt` | 弃用索引 |
| `pending-removal-in-3.14.txt` | Python 3.14 将移除 |
| `pending-removal-in-3.15.txt` | Python 3.15 将移除 |
| `pending-removal-in-3.16.txt` | Python 3.16 将移除 |
| `pending-removal-in-3.17.txt` | Python 3.17 将移除 |
| `pending-removal-in-3.18.txt` | Python 3.18 将移除 |
| `pending-removal-in-3.19.txt` | Python 3.19 将移除 |
| `pending-removal-in-future.txt` | 未来将移除 |
| `pending-removal-in-3.13.txt` | Python 3.13 已移除 |
| `c-api-pending-removal-in-3.14.txt` | C API 3.14 将移除 |
| `c-api-pending-removal-in-3.15.txt` | C API 3.15 将移除 |
| `c-api-pending-removal-in-3.16.txt` | C API 3.16 将移除 |
| `c-api-pending-removal-in-3.18.txt` | C API 3.18 将移除 |
| `c-api-pending-removal-in-future.txt` | C API 未来将移除 |

---

## 快速导航建议

| 目标 | 入口 |
|------|------|
| 查找某个模块文档 | `library/` 下对应 `<module>.txt` |
| Python 语法规范 | `reference/` |
| 学习 Python | `tutorial/` |
| 解决具体问题 | `howto/` |
| 编写 C 扩展 | `c-api/` + `extending/` |
| 查看新特性 | `whatsnew/3.14.txt` |
| 完整索引 | `contents.txt` |
| 术语查询 | `glossary.txt` |
| 弃用检查 | `deprecations/` |
