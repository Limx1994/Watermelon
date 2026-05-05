# prompt_toolkit 3.0.52 API 参考手册

> **prompt_toolkit** 是一个用于构建强大交互式命令行应用的 Python 库，可替代 GNU readline，支持语法高亮、多行编辑、代码补全、Vi/Emacs 快捷键、鼠标支持等功能。

## 目录

- [1. 快速入门与顶层 API](#1-快速入门与顶层-api)
- [2. 核心类](#2-核心类)
- [3. 高级 API（Shortcuts）](#3-高级-apishortcuts)
- [4. 布局系统](#4-布局系统)
- [5. 快捷键系统](#5-快捷键系统)
- [6. 过滤器](#6-过滤器)
- [7. 样式系统](#7-样式系统)
- [8. 补全系统](#8-补全系统)
- [9. 格式化文本](#9-格式化文本)
- [10. 预置组件（Widgets）](#10-预置组件widgets)
- [11. 输入/输出](#11-输入输出)
- [12. 验证、历史、自动建议、词法分析器](#12-验证历史自动建议词法分析器)
- [13. 其他模块](#13-其他模块)

---

## 1. 快速入门与顶层 API

```python
from prompt_toolkit import prompt

# 最简单的用法
result = prompt("请输入: ")
print(f"你输入了: {result}")
```

### 顶层导出（`prompt_toolkit.__init__`）

| 名称 | 类型 | 说明 |
|------|------|------|
| `Application` | class | 核心应用类，管理事件循环、布局、渲染 |
| `prompt()` | function | 快捷函数，创建 PromptSession 并调用 prompt() |
| `PromptSession` | class | 会话式输入，跨调用保持状态（历史等） |
| `print_formatted_text()` | function | 在应用之上打印格式化文本 |
| `HTML` | class | 用 HTML 标签定义格式化文本 |
| `ANSI` | class | 用 ANSI 转义序列定义格式化文本 |
| `choice()` | function | 从选项列表中选择 |
| `confirm()` | function | 是/否确认提示 |
| `__version__` | str | 版本号，如 `"3.0.52"` |
| `VERSION` | tuple | 版本元组，如 `(3, 0, 52)` |

### 最简示例

```python
from prompt_toolkit import prompt, HTML, print_formatted_text

# 基本输入
text = prompt("> ")
# 带默认值
text = prompt("> ", default="hello")
# 密码输入
text = prompt("Password: ", is_password=True)
# 多行输入
text = prompt("> ", multiline=True)
# 带样式的提示
text = prompt(HTML("<b>Name:</b> "))
# 格式化输出
print_formatted_text(HTML("<ansired>错误信息</ansired>"))
```

---

## 2. 核心类

### 2.1 `Application` 类

**类型**: 泛型类 `Application[_AppResult]`  
**路径**: `prompt_toolkit.application.Application`  
**说明**: prompt_toolkit 的核心，管理事件循环、布局、渲染、快捷键等所有全局状态。不直接使用 `prompt()` 而构建全屏应用时必须使用此类。

#### 构造参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `layout` | `Layout \| None` | `None` | 布局实例 |
| `style` | `BaseStyle \| None` | `None` | 样式定义 |
| `include_default_pygments_style` | `FilterOrBool` | `True` | 是否包含默认 Pygments 样式 |
| `style_transformation` | `StyleTransformation \| None` | `None` | 运行时样式变换 |
| `key_bindings` | `KeyBindingsBase \| None` | `None` | 自定义快捷键 |
| `clipboard` | `Clipboard \| None` | `None` | 剪贴板（默认 InMemoryClipboard） |
| `full_screen` | `bool` | `False` | 是否使用备用屏幕缓冲区 |
| `color_depth` | `ColorDepth \| Callable \| None` | `None` | 色彩深度 |
| `mouse_support` | `FilterOrBool` | `False` | 鼠标支持 |
| `enable_page_navigation_bindings` | `FilterOrBool \| None` | `None` | 页面导航快捷键 |
| `paste_mode` | `FilterOrBool` | `False` | 粘贴模式 |
| `editing_mode` | `EditingMode` | `EMACS` | 编辑模式（VI 或 EMACS） |
| `erase_when_done` | `bool` | `False` | 完成后清除输出 |
| `reverse_vi_search_direction` | `FilterOrBool` | `False` | 反转 Vi 搜索方向 |
| `min_redraw_interval` | `float \| int \| None` | `None` | 最小重绘间隔（秒） |
| `max_render_postpone_time` | `float \| int \| None` | `0.01` | 渲染最大推迟时间 |
| `refresh_interval` | `float \| None` | `None` | 自动刷新间隔 |
| `terminal_size_polling_interval` | `float \| None` | `0.5` | 终端大小轮询间隔 |
| `cursor` | `AnyCursorShapeConfig` | `None` | 光标形状配置 |
| `on_reset` | `Callable` | `None` | 重置时回调 |
| `on_invalidate` | `Callable` | `None` | 失效时回调 |
| `before_render` | `Callable` | `None` | 渲染前回调 |
| `after_render` | `Callable` | `None` | 渲染后回调 |
| `input` | `Input \| None` | `None` | 输入对象 |
| `output` | `Output \| None` | `None` | 输出对象 |

#### 主要方法

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `run(pre_run, set_exception_handler, handle_sigint, in_thread, inputhook)` | `_AppResult` | 阻塞运行应用 |
| `run_async(pre_run, set_exception_handler, handle_sigint, slow_callback_duration)` | `_AppResult` | 异步运行 |
| `exit(result=None, exception=None, style="")` | - | 退出应用 |
| `invalidate()` | - | 触发重绘（线程安全） |
| `reset()` | - | 重置所有状态 |
| `create_background_task(coroutine)` | `Task` | 创建后台协程（自动取消） |
| `cancel_and_wait_for_background_tasks()` | - | 取消并等待后台任务 |
| `run_system_command(command, wait_for_enter=True, ...)` | - | 运行系统命令 |
| `suspend_to_background(suspend_group=True)` | - | 暂停进程（SIGTSTP） |
| `get_used_style_strings()` | `list[str]` | 返回使用的样式（调试用） |
| `print_text(text, style=None)` | - | 在输出上打印文本 |

#### 主要属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `layout` | `Layout` | 布局对象 |
| `renderer` | `Renderer` | 渲染器 |
| `current_buffer` | `Buffer` | 当前聚焦的 Buffer |
| `current_search_state` | `SearchState` | 搜索状态 |
| `color_depth` | `ColorDepth` | 当前色彩深度 |
| `is_running` | `bool` | 应用是否运行中 |
| `is_done` | `bool` | 是否已完成 |
| `invalidated` | `bool` | 是否已计划重绘 |
| `vi_state` | `ViState` | Vi 模式状态 |
| `emacs_state` | `EmacsState` | Emacs 模式状态 |

#### 示例

```python
from prompt_toolkit import Application
from prompt_toolkit.layout import Layout, Window, FormattedTextControl

app = Application(
    layout=Layout(Window(FormattedTextControl("Hello World"))),
    full_screen=True,
)
app.run()
```

### 2.2 应用辅助函数

**路径**: `prompt_toolkit.application`

| 函数/类 | 说明 |
|---------|------|
| `get_app()` | 获取当前运行的 `Application` 实例 |
| `get_app_or_none()` | 获取当前应用或 `None` |
| `set_app(app)` | 临时设置当前应用（上下文管理器） |
| `create_app_session(input, output)` | 创建并激活 `AppSession` |
| `create_app_session_from_tty()` | 从 TTY 创建 `AppSession` |
| `get_app_session()` | 获取当前 `AppSession` |
| `AppSession` | 表示与一个终端的交互会话，包含 `input` 和 `output` 属性 |
| `DummyApplication` | 无操作的空应用，用于没有运行应用时返回 |
| `in_terminal()` | 异步上下文管理器，在应用上方运行代码 |
| `run_in_terminal(func)` | 在应用上方运行函数 |

### 2.3 `Buffer` 类

**路径**: `prompt_toolkit.buffer.Buffer`  
**说明**: 核心数据类，保存输入文本和光标位置，实现所有文本操作（插入、删除、移动、补全、搜索、撤销等）。

#### 构造参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `completer` | `Completer \| None` | `None` | 补全器 |
| `auto_suggest` | `AutoSuggest \| None` | `None` | 自动建议 |
| `history` | `History \| None` | `None` | 历史记录（默认 InMemoryHistory） |
| `validator` | `Validator \| None` | `None` | 验证器 |
| `tempfile_suffix` | `str \| Callable` | `""` | "在编辑器中打开"的临时文件后缀 |
| `tempfile` | `str \| Callable` | `""` | 临时文件路径 |
| `name` | `str` | `""` | Buffer 名称 |
| `complete_while_typing` | `FilterOrBool` | `False` | 输入时自动补全 |
| `validate_while_typing` | `FilterOrBool` | `False` | 输入时自动验证 |
| `enable_history_search` | `FilterOrBool` | `False` | 上箭头部分匹配历史 |
| `document` | `Document \| None` | `None` | 初始文档 |
| `accept_handler` | `Callable` | `None` | 接受输入时调用，返回 bool |
| `read_only` | `FilterOrBool` | `False` | 只读模式 |
| `multiline` | `FilterOrBool` | `True` | 多行模式 |
| `max_number_of_completions` | `int` | `10000` | 最大补全数 |
| `on_text_changed` | `Callable` | `None` | 文本改变事件 |
| `on_text_insert` | `Callable` | `None` | 文本插入事件 |
| `on_cursor_position_changed` | `Callable` | `None` | 光标移动事件 |
| `on_completions_changed` | `Callable` | `None` | 补全改变事件 |
| `on_suggestion_set` | `Callable` | `None` | 建议设置事件 |

#### 主要属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `text` | `str` | 当前文本（可设置，只读时抛出 EditReadOnlyBuffer） |
| `document` | `Document` | 当前文档（文本+光标+选择） |
| `cursor_position` | `int` | 光标位置 |
| `complete_state` | `CompletionState \| None` | 补全状态 |
| `validation_state` | `ValidationState` | 验证状态枚举（VALID/INVALID/UNKNOWN） |
| `validation_error` | `ValidationError \| None` | 验证错误 |
| `suggestion` | `Suggestion \| None` | 当前建议 |
| `selection_state` | `SelectionState \| None` | 选择状态 |
| `is_returnable` | `bool` | 是否有 accept_handler |
| `working_index` | `int` | 在历史中的位置 |
| `history_search_text` | `str` | 历史搜索过滤文本 |

#### 文本操作方法

| 方法 | 说明 |
|------|------|
| `insert_text(data, overwrite=False, move_cursor=True, fire_event=True)` | 在光标处插入文本 |
| `delete(count=1)` | 删除光标后字符，返回删除的文本 |
| `delete_before_cursor(count=1)` | 删除光标前字符 |
| `cursor_left(count=1)` | 光标左移 |
| `cursor_right(count=1)` | 光标右移 |
| `cursor_up(count=1)` | 光标上移（多行） |
| `cursor_down(count=1)` | 光标下移（多行） |
| `auto_up(count=1, ...)` | 上移或历史后退 |
| `auto_down(count=1, ...)` | 下移或历史前进 |
| `newline(copy_margin=True)` | 插入换行 |
| `insert_line_above(copy_margin=True)` | 在上方插入行 |
| `insert_line_below(copy_margin=True)` | 在下方插入行 |
| `join_next_line(separator=" ")` | 合并下一行 |
| `join_selected_lines(separator=" ")` | 合并选中的行 |
| `swap_characters_before_cursor()` | 交换光标前两字符 |
| `undo()` | 撤销 |
| `redo()` | 重做 |
| `transform_region(from_, to, transform_callback)` | 转换指定区域 |
| `transform_lines(line_index_iterator, transform_callback)` | 转换指定行 |
| `transform_current_line(transform_callback)` | 转换当前行 |

#### 补全方法

| 方法 | 说明 |
|------|------|
| `start_completion(select_first, select_last, insert_common_part, complete_event)` | 启动异步补全 |
| `complete_next(count=1, disable_wrap_around=False)` | 下一个补全项 |
| `complete_previous(count=1, disable_wrap_around=False)` | 上一个补全项 |
| `cancel_completion()` | 取消补全 |
| `go_to_completion(index)` | 跳转到指定补全项 |
| `apply_completion(completion)` | 应用指定补全 |

#### 选择与剪贴板

| 方法 | 说明 |
|------|------|
| `start_selection(selection_type)` | 开始选择 |
| `copy_selection(_cut=False)` | 复制选中文本 |
| `cut_selection()` | 剪切选中文本 |
| `paste_clipboard_data(data, paste_mode, count)` | 粘贴剪贴板数据 |
| `exit_selection()` | 退出选择状态 |

#### 搜索与历史

| 方法 | 说明 |
|------|------|
| `history_backward(count=1)` | 历史后退 |
| `history_forward(count=1)` | 历史前进 |
| `go_to_history(index)` | 跳转到指定历史项 |
| `apply_search(search_state, include_current_position, count)` | 搜索 |
| `get_search_position(search_state, include_current_position, count)` | 获取搜索位置 |
| `yank_nth_arg(n, _yank_last_arg)` | 从历史中获取第 n 个参数 |
| `yank_last_arg(n)` | 获取历史最后一个参数 |

#### 其他方法

| 方法 | 说明 |
|------|------|
| `reset(document, append_to_history)` | 重置缓冲区 |
| `validate(set_cursor=False)` | 同步验证，返回 bool |
| `validate_and_handle()` | 验证并接受输入 |
| `append_to_history()` | 追加当前文本到历史 |
| `open_in_editor(validate_and_handle)` | 在外部编辑器中打开 |

### 2.4 `Document` 类

**路径**: `prompt_toolkit.document.Document`  
**说明**: 不可变的文本快照，包含文本和光标位置。提供大量文本查询方法。

#### 构造参数

```python
Document(text="", cursor_position=None, selection=None)
```

#### 主要属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `text` | `str` | 完整文本 |
| `cursor_position` | `int` | 光标位置 |
| `selection` | `SelectionState \| None` | 选择状态 |
| `current_char` | `str` | 光标所在字符 |
| `char_before_cursor` | `str` | 光标前字符 |
| `text_before_cursor` | `str` | 光标前文本 |
| `text_after_cursor` | `str` | 光标后文本 |
| `current_line_before_cursor` | `str` | 当前行光标前部分 |
| `current_line_after_cursor` | `str` | 当前行光标后部分 |
| `lines` | `list[str]` | 所有行（缓存） |
| `line_count` | `int` | 行数 |
| `current_line` | `str` | 光标所在行文本 |
| `leading_whitespace_in_current_line` | `str` | 当前行前导空白 |
| `on_first_line` | `bool` | 是否在第一行 |
| `on_last_line` | `bool` | 是否在最后一行 |
| `cursor_position_row` | `int` | 光标行号（0 基） |
| `cursor_position_col` | `int` | 光标列号（0 基） |
| `is_cursor_at_the_end` | `bool` | 是否在文本末尾 |
| `is_cursor_at_the_end_of_line` | `bool` | 是否在行末 |

#### 主要方法

| 方法 | 说明 |
|------|------|
| `translate_index_to_position(index)` | 将索引转为 `(行, 列)` |
| `translate_row_col_to_index(row, col)` | 将 `(行, 列)` 转为索引 |
| `has_match_at_current_position(sub)` | 检查光标处是否匹配 |
| `find(sub, in_current_line, include_current_position, ignore_case, count)` | 向后搜索，返回相对位置 |
| `find_all(sub, ignore_case)` | 搜索所有匹配，返回绝对位置列表 |
| `find_backwards(sub, in_current_line, ignore_case, count)` | 向前搜索 |
| `get_word_before_cursor(WORD=False)` | 获取光标前单词 |
| `find_start_of_previous_word(count, WORD)` | 前一个词开始位置 |
| `find_boundaries_of_current_word(WORD, ...)` | 当前词边界 |
| `get_word_under_cursor(WORD=False)` | 获取光标下单词 |
| `find_next_word_beginning(count, WORD)` | 下一个词开始 |
| `find_next_word_ending(count, WORD)` | 下一个词结束 |
| `find_previous_word_beginning(count, WORD)` | 前一个词开始 |
| `find_previous_word_ending(count, WORD)` | 前一个词结束 |
| `find_enclosing_bracket_right(left_ch, right_ch)` | 找到匹配的右括号 |
| `find_enclosing_bracket_left(left_ch, right_ch)` | 找到匹配的左括号 |
| `find_matching_bracket_position(start_pos, end_pos)` | 找到匹配括号位置 |
| `get_cursor_left_position(count)` | 光标左移后的相对位置 |
| `get_cursor_right_position(count)` | 光标右移后的相对位置 |
| `get_cursor_up_position(count, preferred_column)` | 光标上移后的相对位置 |
| `get_cursor_down_position(count, preferred_column)` | 光标下移后的相对位置 |
| `get_start_of_document_position()` | 文档开始相对位置 |
| `get_end_of_document_position()` | 文档结束相对位置 |
| `get_start_of_line_position(after_whitespace)` | 行首相对位置 |
| `get_end_of_line_position()` | 行尾相对位置 |
| `last_non_blank_of_current_line_position()` | 行末非空白字符位置 |
| `selection_range()` | 选择范围 `(起始, 结束)` |
| `selection_ranges()` | 多选择范围（块选择时） |
| `selection_range_at_line(row)` | 指定行的选择范围 |
| `cut_selection()` | 剪切选择，返回 (新 Document, ClipboardData) |
| `paste_clipboard_data(data, paste_mode, count)` | 粘贴后返回新 Document |
| `empty_line_count_at_the_end()` | 末尾空行数 |
| `start_of_paragraph(count, before)` | 段落开始 |
| `end_of_paragraph(count, after)` | 段落结束 |
| `insert_after(text)` | 追加文本，返回新 Document |
| `insert_before(text)` | 前置文本，返回新 Document |

### 2.5 `EditReadOnlyBuffer` 异常

**说明**: 尝试编辑只读 Buffer 时抛出的异常。

### 2.6 `ValidationState` 枚举

**路径**: `prompt_toolkit.buffer.ValidationState`

| 值 | 说明 |
|----|------|
| `VALID` | 验证通过 |
| `INVALID` | 验证失败 |
| `UNKNOWN` | 未验证 |

### 2.7 `CompletionState`

**说明**: 表示 Buffer 的当前补全状态（内部类，通常不需要直接使用）。

---

## 3. 高级 API（Shortcuts）

### 3.1 `prompt()` 函数

**路径**: `prompt_toolkit.shortcuts.prompt`  
**说明**: 最常用的快捷函数，创建一个临时的 PromptSession 并调用 prompt()，返回用户输入的文本。所有参数都是可选的，除了 `message`。

#### 参数分类

**基本**:
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `message` | `AnyFormattedText` | - | 提示文本（支持 HTML/ANSI 格式） |
| `default` | `str` | `""` | 默认输入文本 |
| `accept_default` | `bool` | `False` | 是否直接接受默认值 |
| `multiline` | `FilterOrBool` | `False` | 多行输入 |
| `wrap_lines` | `FilterOrBool` | `True` | 自动换行 |
| `is_password` | `FilterOrBool` | `False` | 密码模式 |

**编辑**:
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `editing_mode` | `EditingMode` | `EMACS` | 编辑模式 |
| `vi_mode` | `bool` | `False` | 是否启用 Vi 模式（快捷方式） |
| `mouse_support` | `FilterOrBool` | `False` | 鼠标支持 |
| `cursor` | `AnyCursorShapeConfig` | `None` | 光标形状 |

**补全**:
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `completer` | `Completer \| None` | `None` | 补全器 |
| `complete_while_typing` | `FilterOrBool` | `False` | 输入时自动补全 |
| `complete_style` | `CompleteStyle` | `COLUMN` | 补全菜单样式 |
| `reserve_space_for_menu` | `int` | `0` | 为补全菜单预留行数 |

**验证**:
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `validator` | `Validator \| None` | `None` | 验证器 |
| `validate_while_typing` | `FilterOrBool` | `False` | 输入时验证 |

**历史**:
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `history` | `History \| None` | `None` | 历史记录 |
| `enable_history_search` | `FilterOrBool` | `False` | 启用历史搜索 |

**样式**:
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `style` | `BaseStyle \| None` | `None` | 样式定义 |
| `style_transformation` | `StyleTransformation \| None` | `None` | 样式变换 |
| `color_depth` | `ColorDepth \| None` | `None` | 色彩深度 |
| `lexer` | `Lexer \| None` | `None` | 语法高亮词法分析器 |
| `include_default_pygments_style` | `FilterOrBool` | `True` | 默认 Pygments 样式 |

**工具栏**:
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `bottom_toolbar` | `AnyFormattedText \| None` | `None` | 底部工具栏文本 |
| `rprompt` | `AnyFormattedText \| None` | `None` | 右侧提示文本 |
| `prompt_continuation` | `AnyFormattedText \| Callable` | `None` | 多行续行提示 |
| `placeholder` | `AnyFormattedText \| None` | `None` | 占位文本 |

**快捷键**:
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `key_bindings` | `KeyBindingsBase \| None` | `None` | 自定义快捷键 |
| `enable_system_prompt` | `FilterOrBool` | `False` | 启用系统命令 |
| `enable_suspend` | `FilterOrBool` | `False` | 启用暂停（Ctrl+Z） |
| `enable_open_in_editor` | `FilterOrBool` | `False` | 启用编辑器中打开 |

**执行**:
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `pre_run` | `Callable \| None` | `None` | 运行前回调 |
| `in_thread` | `bool` | `False` | 在后台线程中运行 |
| `inputhook` | `InputHook \| None` | `None` | 输入钩子（用于 GUI 集成） |

**文件**:
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `tempfile_suffix` | `str \| Callable` | `""` | 临时文件后缀 |
| `tempfile` | `str \| Callable` | `""` | 临时文件路径 |

#### 使用示例

```python
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.validation import Validator

# 基本输入
name = prompt("你的名字: ")

# 带补全
completer = WordCompleter(["apple", "banana", "cherry"])
fruit = prompt("水果: ", completer=completer)

# 带验证
def is_number(text):
    if not text.isdigit():
        raise ValueError("请输入数字")

validator = Validator.from_callable(is_number, error_message="请输入数字")
age = prompt("年龄: ", validator=validator)

# 带默认值
city = prompt("城市: ", default="北京")

# 密码模式
pwd = prompt("密码: ", is_password=True)

# Vi 模式
cmd = prompt("命令: ", vi_mode=True)
```

### 3.2 `PromptSession` 类

**路径**: `prompt_toolkit.shortcuts.PromptSession`  
**说明**: 会话式提示，跨多次 prompt 调用保持状态（历史、缓冲区等）。参数与 `prompt()` 相同，但可设置会话级默认值。

#### 构造参数

与 `prompt()` 函数参数相同，额外增加：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `interrupt_exception` | `Type[BaseException]` | `KeyboardInterrupt` | Ctrl+C 时抛出的异常 |
| `eof_exception` | `Type[BaseException]` | `EOFError` | Ctrl+D 时抛出的异常 |

#### 方法

| 方法 | 说明 |
|------|------|
| `prompt(message=None, **kwargs)` | 阻塞调用，返回输入文本 |
| `prompt_async(message=None, **kwargs)` | 异步调用 |

`prompt()` 额外的按次调用参数（不影响会话状态）：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `default` | `str \| Document` | `""` | 默认输入 |
| `accept_default` | `bool` | `False` | 直接接受默认值 |
| `pre_run` | `Callable \| None` | `None` | 运行前回调 |

#### 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `app` | `Application` | 底层 Application 实例 |
| `input` | `Input` | 当前输入 |
| `output` | `Output` | 当前输出 |
| `editing_mode` | `EditingMode` | 编辑模式（可设置） |
| `default_buffer` | `Buffer` | 默认缓冲区 |

#### 使用示例

```python
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory

# 保持历史跨调用持续
session = PromptSession(history=FileHistory("~/.my_history"))

while True:
    try:
        text = session.prompt("> ")
        print(f"你输入了: {text}")
    except (EOFError, KeyboardInterrupt):
        break
```

### 3.3 `CompleteStyle` 枚举

| 值 | 说明 |
|----|------|
| `COLUMN` | 单列垂直列表 |
| `MULTI_COLUMN` | 多列网格 |
| `READLINE_LIKE` | 类似 readline 的行内显示 |

### 3.4 `confirm()` 函数

**路径**: `prompt_toolkit.shortcuts.confirm`  
**说明**: 是/否确认提示，返回 `bool`。

```python
from prompt_toolkit import confirm

if confirm("确认删除?", suffix=" [y/N] "):
    print("已删除")
else:
    print("取消")
```

### 3.5 `choice()` 函数

**路径**: `prompt_toolkit.shortcuts.choice`  
**说明**: 让用户从选项列表中选择一项。

```python
from prompt_toolkit import choice

option = choice(
    "选择颜色:",
    options=[
        ("r", "红色"),
        ("g", "绿色"),
        ("b", "蓝色"),
    ],
)
print(f"你选择了: {option}")
```

### 3.6 对话框

**路径**: `prompt_toolkit.shortcuts`

所有对话框函数返回 `Application[_T]`，需要调用 `.run()` 来执行。

#### `input_dialog()`

```python
input_dialog(title="对话框标题", text="请输入内容:", ok_text="确定", cancel_text="取消")
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `title` | `AnyFormattedText` | 弹窗标题 |
| `text` | `AnyFormattedText` | 提示文本 |
| `ok_text` | `str` | 确定按钮文本 |
| `cancel_text` | `str` | 取消按钮文本 |
| `completer` | `Completer \| None` | 补全器 |
| `validator` | `Validator \| None` | 验证器 |
| `password` | `bool` | 密码模式 |
| `style` | `BaseStyle \| None` | 样式 |

#### `message_dialog()`

```python
message_dialog(title="提示", text="操作成功完成!")
```

| 参数 | 说明 |
|------|------|
| `title` | 弹窗标题 |
| `text` | 提示文本 |
| `ok_text` | 确定按钮文本（默认 "OK"） |

#### `yes_no_dialog()`

```python
result = yes_no_dialog(title="确认", text="是否继续?").run()
# result 为 True 或 False
```

#### `button_dialog()`

```python
result = button_dialog(
    title="选择操作",
    text="请选择一个选项:",
    buttons=[("保存", "save"), ("不保存", "discard"), ("取消", None)],
).run()
```

| 参数 | 说明 |
|------|------|
| `buttons` | `list[tuple[str, _T]]`，每个按钮为 (显示文本, 返回值) |

#### `checkboxlist_dialog()`

```python
result = checkboxlist_dialog(
    title="选择兴趣",
    text="请选择:",
    values=[("py", "Python"), ("js", "JavaScript"), ("rs", "Rust")],
    default_values=["py"],
).run()
# result 为选中项的 value 列表
```

#### `radiolist_dialog()`

```python
result = radiolist_dialog(
    title="选择语言",
    text="请选择:",
    values=[("py", "Python"), ("js", "JavaScript")],
    default="py",
).run()
# result 为选中项的 value
```

#### `progress_dialog()`

```python
import time
from prompt_toolkit.shortcuts import progress_dialog

def run(set_percentage, log_text):
    for i in range(100):
        time.sleep(0.05)
        set_percentage(i + 1)
        log_text(f"处理中 {i+1}%")

progress_dialog(
    title="进度",
    text="正在处理...",
    run_callback=run,
).run()
```

### 3.7 进度条

**路径**: `prompt_toolkit.shortcuts.ProgressBar`

#### `ProgressBar` 类

上下文管理器，用于显示循环进度。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `title` | `AnyFormattedText` | `""` | 标题 |
| `formatters` | `list[Formatter]` | `None` | 自定义格式化器 |
| `bottom_bar` | `AnyFormattedText \| None` | `None` | 底部栏 |
| `style` | `BaseStyle \| None` | `None` | 样式 |
| `cancel_callback` | `Callable \| None` | `None` | 取消回调 |
| `key_bindings` | `KeyBindingsBase \| None` | `None` | 快捷键 |

```python
from prompt_toolkit.shortcuts import ProgressBar
import time

with ProgressBar(title="下载中...") as pb:
    for i in pb(range(100), label="处理"):
        time.sleep(0.03)
```

#### `ProgressBarCounter` 类

自动为迭代器创建的计数器。

| 属性/方法 | 说明 |
|-----------|------|
| `items_completed` | 已完成项数 |
| `value` | 当前值 |
| `done` | 是否完成 |
| `label` | 标签 |
| `set_amount(value)` | 设置当前进度 |

#### 预置格式化器

**路径**: `prompt_toolkit.shortcuts.progress_bar.formatters`

| 类 | 说明 |
|----|------|
| `Text` | 静态文本 |
| `Label` | 标签 |
| `Percentage` | 百分比 |
| `Bar` | 可视进度条 |
| `Progress` | `值/最大值` |
| `TimeElapsed` | 已用时间 |
| `TimeLeft` | 估计剩余时间 |
| `IterationsPerSecond` | 每秒迭代次数 |
| `SpinningWheel` | 旋转动画 |
| `Rainbow` | 彩虹色进度条 |

### 3.8 `print_formatted_text()` 函数

**路径**: `prompt_toolkit.shortcuts.print_formatted_text`  
**说明**: 在应用运行时上方打印格式化文本（不会破坏 UI）。

```python
from prompt_toolkit import print_formatted_text, HTML

print_formatted_text(HTML("<b>粗体</b> <ansired>红色</ansired>"))
print_formatted_text("普通文本", style="bg:ansigreen fg:ansiwhite")
```

### 3.9 其他快捷工具

| 函数 | 说明 |
|------|------|
| `clear()` | 清除终端屏幕 |
| `set_title(title)` | 设置终端标题 |
| `clear_title()` | 清除终端标题 |
| `print_container(container, file, style, ...)` | 非交互式打印容器布局 |

---

## 4. 布局系统

**路径**: `prompt_toolkit.layout`

布局系统是 prompt_toolkit 最强大也最复杂的部分。它采用容器的层次结构：

- **容器**（Container）包含子容器或控件，决定尺寸和排列
- **控件**（UIControl）负责渲染实际内容
- **Window** 是将容器和控件连接起来的桥梁（一个 Window 包含一个 UIControl）

### 4.1 `Layout` 类

布局的根容器。

```python
from prompt_toolkit.layout import Layout, HSplit, Window, BufferControl

layout = Layout(HSplit([Window(BufferControl()), Window(BufferControl())]))
```

| 方法 | 说明 |
|------|------|
| `focus(value)` | 聚焦指定元素（str 缓冲区名 / Buffer / UIControl / Window） |
| `has_focus(value)` | 检查元素是否聚焦 |
| `focus_next()` | 聚焦下一个可见/可聚焦的 Window |
| `focus_previous()` | 聚焦上一个 |
| `focus_last()` | 聚焦上一个控制 |
| `walk(container)` | 遍历所有容器（函数，非方法） |

| 属性 | 说明 |
|------|------|
| `container` | 根容器 |
| `current_control` | 当前聚焦的 UIControl |
| `current_window` | 当前聚焦的 Window |
| `current_buffer` | 当前聚焦的 Buffer |

### 4.2 容器类型

**路径**: `prompt_toolkit.layout.containers`

#### `HSplit`

水平分割，子容器垂直堆叠。

| 参数 | 类型 | 说明 |
|------|------|------|
| `children` | `list[AnyContainer]` | 子元素列表 |
| `padding` | `AnyDimension` | 内边距尺寸 |
| `padding_char` | `str` | 内边距填充字符 |
| `padding_style` | `str` | 内边距样式 |
| `width` | `AnyDimension` | 宽度 |
| `height` | `AnyDimension` | 高度 |
| `align` | `VerticalAlign` | 垂直对齐 |
| `style` | `str` | 样式 |
| `key_bindings` | `KeyBindingsBase \| None` | 快捷键 |

#### `VSplit`

垂直分割，子容器水平排列。参数同 `HSplit`。

```python
from prompt_toolkit.layout import VSplit, HSplit, Window, FormattedTextControl

split = VSplit([
    Window(FormattedTextControl("左侧")),
    Window(width=1, char="|"),  # 分隔线
    Window(FormattedTextControl("右侧")),
])
```

#### `Window`

**唯一可以渲染 `UIControl` 的容器**。每个控件必须包裹在 Window 中。

| 参数 | 类型 | 说明 |
|------|------|------|
| `content` | `UIControl` | 要渲染的控件 |
| `width` | `AnyDimension` | 宽度 |
| `height` | `AnyDimension` | 高度 |
| `style` | `str` | 样式 |
| `wrap_lines` | `bool` | 自动换行 |
| `left_margins` | `list[Margin]` | 左边距 |
| `right_margins` | `list[Margin]` | 右边距 |
| `scroll_offsets` | `ScrollOffsets` | 滚动偏移 |
| `align` | `WindowAlign` | 内容对齐 |
| `dont_extend_height` | `bool` | 不扩展高度 |
| `dont_extend_width` | `bool` | 不扩展宽度 |
| `get_line_prefix` | `Callable` | 行前缀（用于续行提示） |
| `cursor` | `str` | 光标样式 |
| `allow_scroll_beyond_bottom` | `bool` | 允许滚到底部以下 |
| `always_hide_cursor` | `bool` | 始终隐藏光标 |
| `key_bindings` | `KeyBindingsBase \| None` | 快捷键 |

#### `FloatContainer` 和 `Float`

浮层容器，允许在内容之上叠加悬浮元素（如菜单、弹出层）。

```python
from prompt_toolkit.layout import FloatContainer, Float, Window, FormattedTextControl

layout = FloatContainer(
    content=Window(FormattedTextControl("主内容")),
    floats=[
        Float(content=Window(FormattedTextControl("浮动层")), xcursor=5, ycursor=3),
    ],
)
```

`Float` 参数:

| 参数 | 类型 | 说明 |
|------|------|------|
| `left` / `right` / `top` / `bottom` | `int \| None` | 偏移量（绝对定位） |
| `xcursor` / `ycursor` | `int \| None` | 光标相对位置 |
| `width` / `height` | `int \| None` | 尺寸 |
| `transparent` | `bool` | 是否透明 |
| `allow_cover_content` | `bool` | 允许覆盖内容 |
| `attach_to_window` | `bool` | 是否附着到父窗口 |

#### `ConditionalContainer`

根据 Filter 条件显示不同的容器。

| 参数 | 说明 |
|------|------|
| `content` | 条件为真时显示 |
| `filter` | 条件过滤器 |
| `alternative_content` | 条件为假时显示（可选） |

#### `DynamicContainer`

通过可调用对象动态解析容器。

```python
DynamicContainer(get_container=lambda: my_container)
```

#### `ScrollablePane`

可滚动的容器面板。

| 参数 | 说明 |
|------|------|
| `content` | 包含的内容 |
| `scroll_offsets` | 滚动偏移 |
| `keep_cursor_visible` | 保持光标可见 |

#### 其他类型

| 类型 | 说明 |
|------|------|
| `WindowAlign` | 枚举: `LEFT`, `CENTER`, `RIGHT` |
| `HorizontalAlign` | 枚举: `LEFT`, `CENTER`, `RIGHT` |
| `VerticalAlign` | 枚举: `TOP`, `CENTER`, `BOTTOM` |
| `ScrollOffsets(top, bottom, left, right)` | 滚动偏移配置 |
| `ColorColumn(position)` | 高亮列 |
| `WindowRenderInfo` | Window 渲染信息 |

#### 工具函数

| 函数 | 说明 |
|------|------|
| `to_container(value)` | 将各种类型转为 Container |
| `to_window(value)` | 转为 Window |
| `is_container(value)` | 类型检查 |

### 4.3 控件类型

**路径**: `prompt_toolkit.layout.controls`

#### `BufferControl`

渲染一个 `Buffer` 的控件，是编辑文本的主要方式。

| 参数 | 类型 | 说明 |
|------|------|------|
| `buffer` | `Buffer \| str \| None` | Buffer 实例或名称 |
| `input_processors` | `list[Processor]` | 输入处理器列表 |
| `include_default_input_processors` | `bool` | 包含默认处理器 |
| `lexer` | `Lexer \| None` | 词法分析器 |
| `preview_search` | `bool` | 预览搜索匹配 |
| `focusable` | `bool` | 可否聚焦 |
| `focus_on_click` | `bool` | 点击聚焦 |
| `key_bindings` | `KeyBindingsBase \| None` | 快捷键 |

#### `FormattedTextControl`

渲染静态格式化文本（不可编辑）。

| 参数 | 类型 | 说明 |
|------|------|------|
| `text` | `AnyFormattedText` | 格式化文本 |
| `style` | `str` | 默认样式 |
| `focusable` | `bool` | 可否聚焦 |
| `focus_on_click` | `bool` | 点击聚焦 |
| `key_bindings` | `KeyBindingsBase \| None` | 快捷键 |
| `show_cursor` | `bool` | 显示光标 |
| `modal` | `bool` | 模态控件 |

```python
from prompt_toolkit.layout import Window, FormattedTextControl
from prompt_toolkit import HTML

Window(FormattedTextControl(HTML("<b>标题</b> <ansired>内容</ansired>")))
```

#### `SearchBufferControl`

搜索输入框控件。

#### `DummyControl`

空控件，不渲染任何内容。

### 4.4 `Dimension` 类

**路径**: `prompt_toolkit.layout.dimension.Dimension`  
**说明**: 用于指定容器或控件的尺寸（宽度/高度）。

```python
from prompt_toolkit.layout import Dimension

# 固定大小
Dimension.exact(10)

# 权重（按比例分配空间）
Dimension(weight=1)

# 带最小/最大约束
Dimension(min=5, max=20, preferred=10)
```

| 类方法 | 说明 |
|--------|------|
| `exact(amount)` | 固定尺寸 |
| `zero()` | 零尺寸 |

| 属性 | 说明 |
|------|------|
| `min` | 最小值 |
| `max` | 最大值 |
| `weight` | 权重（比例分配） |
| `preferred` | 首选值 |

| 工具函数 | 说明 |
|----------|------|
| `D` | Dimension 别名 |
| `to_dimension(value)` | 将 int/None/Callable 转为 Dimension |
| `sum_layout_dimensions(dims)` | 合并多个 Dimension |
| `max_layout_dimensions(dims)` | 取多个 Dimension 的最大值 |
| `is_dimension(value)` | 类型检查 |

### 4.5 边距类型

**路径**: `prompt_toolkit.layout.margins`

| 类 | 说明 |
|----|------|
| `NumberedMargin(relative, display_tildes)` | 行号边距，支持相对行号 |
| `ScrollbarMargin(display_arrows)` | 滚动条 |
| `ConditionalMargin(margin, filter)` | 条件显示边距 |
| `PromptMargin` | （已弃用）提示文本边距 |

```python
from prompt_toolkit.layout import Window, BufferControl, NumberedMargin, ScrollbarMargin

Window(
    BufferControl(),
    left_margins=[NumberedMargin()],
    right_margins=[ScrollbarMargin()],
)
```

### 4.6 补全菜单

**路径**: `prompt_toolkit.layout.menus`

| 类 | 说明 |
|----|------|
| `CompletionsMenu` | 单列补全菜单 |
| `MultiColumnCompletionsMenu` | 多列补全菜单 |

### 4.7 布局处理器

**路径**: `prompt_toolkit.layout.processors`

处理器在渲染前对文本行进行转换（如高亮搜索匹配、追加自动建议等）。

| 处理器 | 说明 |
|--------|------|
| `Processor` | 处理器抽象基类 |
| `HighlightSearchProcessor` | 高亮搜索匹配 |
| `HighlightIncrementalSearchProcessor` | 高亮渐进搜索匹配 |
| `HighlightSelectionProcessor` | 高亮选中文本 |
| `PasswordProcessor` | 用 `*` 替换字符 |
| `HighlightMatchingBracketProcessor` | 高亮匹配括号 |
| `DisplayMultipleCursors` | 显示多光标 |
| `BeforeInput(text, style)` | 在输入前插入文本 |
| `AfterInput(text, style)` | 在输入后插入文本 |
| `ShowArg` | 显示重复计数参数 |
| `AppendAutoSuggestion` | 追加自动建议 |
| `ConditionalProcessor(processor, filter)` | 条件处理器 |
| `ShowLeadingWhiteSpaceProcessor` | 可视化前导空白 |
| `ShowTrailingWhiteSpaceProcessor` | 可视化尾部空白 |
| `TabsProcessor(tabstop)` | 制表符转空格 |
| `ReverseSearchProcessor` | 反向搜索指示器 |
| `DynamicProcessor(get_processor)` | 动态解析处理器 |
| `merge_processors(processors)` | 合并多个处理器 |

处理器使用示例：

```python
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.layout.processors import (
    BeforeInput,
    AppendAutoSuggestion,
    HighlightSearchProcessor,
    ConditionalProcessor,
)
from prompt_toolkit.filters import vi_mode

BufferControl(
    input_processors=[
        BeforeInput(">>> "),       # 在每个输入行前加 ">>> "
        AppendAutoSuggestion(),    # 显示自动建议
        HighlightSearchProcessor(),  # 高亮搜索匹配
        ConditionalProcessor(
            HighlightMatchingBracketProcessor(),
            filter=vi_mode,  # 仅在 Vi 模式下高亮括号
        ),
    ]
)
```
---

## 5. 快捷键系统

### 5.1 `Keys` 枚举

**路径**: `prompt_toolkit.keys.Keys`  
**说明**: 定义所有可能的键盘按键。字符串枚举。

**控制键**: `Keys.ControlA` ~ `Keys.ControlZ`  
**功能键**: `Keys.F1` ~ `Keys.F24`  
**导航键**: `Keys.Left`, `Keys.Right`, `Keys.Up`, `Keys.Down`, `Keys.Home`, `Keys.End`, `Keys.Insert`, `Keys.Delete`, `Keys.PageUp`, `Keys.PageDown`  
**特殊键**: `Keys.Escape`, `Keys.BackTab`  
**鼠标/事件**: `Keys.ScrollUp`, `Keys.ScrollDown`, `Keys.SIGINT`, `Keys.CPRResponse`, `Keys.Vt100MouseEvent`, `Keys.WindowsMouseEvent`, `Keys.BracketedPaste`, `Keys.Ignore`  
**通配符**: `Keys.Any`（匹配任何按键）

**常用别名**:

| 别名 | 原值 |
|------|------|
| `Keys.Tab` | `Keys.ControlI` |
| `Keys.Enter` | `Keys.ControlM` |
| `Keys.Backspace` | `Keys.ControlH` |
| `Keys.ControlSpace` | `Keys.ControlAt` |

### 5.2 `KeyBindings` 类

**路径**: `prompt_toolkit.key_binding.KeyBindings`  
**说明**: 快捷键注册中心。通常作为装饰器使用。

```python
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys

kb = KeyBindings()

# 注册快捷键（装饰器方式）
@kb.add("c-c")
def exit_(event):
    event.app.exit()

# 多个键组合
@kb.add("c-x", "c-s")
def save(event):
    text = event.app.current_buffer.text
    # 保存 text...

# 带过滤器
@kb.add("enter", filter=~vi_mode)
def accept(event):
    buff = event.app.current_buffer
    buff.validate_and_handle()
```

#### `add()` 方法参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `*keys` | `str \| Keys` | - | 按键序列，如 `"c-c"`, `"enter"`, `Keys.F1` |
| `filter` | `FilterOrBool` | `True` | 激活条件 |
| `eager` | `FilterOrBool` | `False` | 是否优先匹配 |
| `is_global` | `FilterOrBool` | `False` | 全局绑定 |
| `save_before` | `Callable` | `lambda e: True` | 保存状态的回调 |
| `record_in_macro` | `FilterOrBool` | `True` | 是否记录到宏 |

#### 其他方法

| 方法 | 说明 |
|------|------|
| `remove(*keys)` | 移除快捷键绑定 |
| `get_bindings_for_keys(keys)` | 获取匹配的绑定列表 |
| `get_bindings_starting_with_keys(keys)` | 获取以指定键开始的绑定 |

### 5.3 `KeyPressEvent` 类

传递给快捷键处理函数的事件对象。

| 属性 | 类型 | 说明 |
|------|------|------|
| `key_sequence` | `list[KeyPress]` | 按下的键序列 |
| `key` | `KeyPress` | 最近按下的键 |
| `data` | `str` | 原始数据 |
| `app` | `Application` | 当前应用 |
| `is_repeat` | `bool` | 是否重复按键 |

### 5.4 `KeyPress` 类

| 属性 | 说明 |
|------|------|
| `key` | 按键（Keys 枚举或 str） |
| `data` | 原始字符串数据 |

### 5.5 辅助快捷键类

| 类 | 说明 |
|----|------|
| `ConditionalKeyBindings(key_bindings, filter)` | 按条件启用/禁用一组快捷键 |
| `DynamicKeyBindings(get_key_bindings)` | 通过可调用对象动态返回快捷键 |
| `GlobalOnlyKeyBindings(key_bindings)` | 只暴露全局绑定 |
| `merge_key_bindings(bindings)` | 合并多个 KeyBindings 对象 |

### 5.6 默认快捷键模块

prompt_toolkit 内置了大量默认快捷键（Vi 和 Emacs 模式），位于 `prompt_toolkit.key_binding.bindings`：

| 模块 | 内容 |
|------|------|
| `vi.py` | Vi 模式全部快捷键（导航、插入、替换、可视等） |
| `emacs.py` | Emacs 模式全部快捷键 |
| `basic.py` | 基本快捷键（Tab 补全、Ctrl+C 复制等） |
| `completion.py` | 补全菜单快捷键 |
| `search.py` | 搜索模式快捷键 |
| `auto_suggest.py` | 自动建议快捷键 |
| `named_commands.py` | 具名命令（类似 readline 函数） |
| `mouse.py` | 鼠标事件处理 |
| `focus.py` | 焦点切换快捷键 |

---

## 6. 过滤器

**路径**: `prompt_toolkit.filters`  
**说明**: 过滤器是布尔条件，用于控制快捷键、样式、布局元素等的激活状态。支持 `&`（与）、`|`（或）和 `~`（非）运算组合。

### 6.1 基础类

#### `Filter`（抽象基类）

| 操作 | 说明 |
|------|------|
| `filter1 & filter2` | 逻辑与 |
| `filter1 \| filter2` | 逻辑或 |
| `~filter` | 逻辑非 |

#### `Always`

始终返回 `True`。

#### `Never`

始终返回 `False`。

#### `Condition`

从可调用对象创建过滤器。

```python
from prompt_toolkit.filters import Condition

@Condition
def is_verbose():
    return debug_mode

# 或者直接传入 callable
is_debug = Condition(lambda: debug_mode)
```

#### `FilterOrBool`

类型别名：`Union[Filter, bool]` — `True` 相当于 `Always()`，`False` 相当于 `Never()`。

#### 工具函数

| 函数 | 说明 |
|------|------|
| `is_true(value)` | 计算过滤器或布尔值 |
| `to_filter(value)` | 将 `bool` 或 `Filter` 转为 `Filter` |

### 6.2 预置应用过滤器

**路径**: `prompt_toolkit.filters.app`

#### 编辑模式

| 过滤器 | 说明 |
|--------|------|
| `vi_mode` | Vi 模式激活时 |
| `vi_navigation_mode` | Vi 导航模式 |
| `vi_insert_mode` | Vi 插入模式 |
| `vi_insert_multiple_mode` | Vi 多光标插入模式 |
| `vi_replace_mode` | Vi 替换模式 |
| `vi_selection_mode` | Vi 选择模式 |
| `vi_waiting_for_text_object_mode` | 等待文本对象 |
| `vi_digraph_mode` | Vi 组合字符输入模式 |
| `vi_recording_macro` | Vi 录制宏 |
| `emacs_mode` | Emacs 模式激活时 |
| `emacs_insert_mode` | Emacs 插入模式 |
| `emacs_selection_mode` | Emacs 选择模式 |
| `shift_selection_mode` | Shift 选择模式 |
| `in_editing_mode(editing_mode)` | 检查是否指定编辑模式 |

#### 焦点

| 过滤器 | 说明 |
|--------|------|
| `has_focus(value)` | 指定元素是否聚焦（参数为 str 缓冲区名/Buffer/UIControl/Container） |
| `buffer_has_focus` | BufferControl 是否聚焦 |

#### 补全

| 过滤器 | 说明 |
|--------|------|
| `has_completions` | 当前缓冲区有补全项 |
| `completion_is_selected` | 已选中特定补全项 |

#### 搜索

| 过滤器 | 说明 |
|--------|------|
| `is_searching` | 搜索模式激活 |
| `control_is_searchable` | 当前控件支持搜索 |
| `vi_search_direction_reversed` | Vi 搜索方向反转 |

#### 缓冲区状态

| 过滤器 | 说明 |
|--------|------|
| `is_read_only` | 当前缓冲区只读 |
| `is_multiline` | 当前缓冲区多行 |
| `has_selection` | 有选中文本 |
| `has_suggestion` | 有自动建议 |
| `has_validation_error` | 有验证错误 |

#### 应用状态

| 过滤器 | 说明 |
|--------|------|
| `is_done` | 应用正在退出 |
| `renderer_height_is_known` | 已知终端高度 |
| `has_arg` | 输入处理器有重复参数 |

#### 其他

| 过滤器 | 说明 |
|--------|------|
| `in_paste_mode` | 粘贴模式激活 |

#### 使用示例

```python
from prompt_toolkit.filters import vi_mode, vi_navigation_mode, Condition
from prompt_toolkit.key_binding import KeyBindings

kb = KeyBindings()

# 仅在 Vi 导航模式下有效
@kb.add("j", "j", filter=vi_navigation_mode)
def exit_insert(event):
    event.app.current_buffer.cursor_right()

# 组合过滤器
@kb.add("enter", filter=vi_mode & ~vi_insert_mode)
def vi_accept(event):
    event.app.current_buffer.validate_and_handle()

# 自定义条件
@Condition
def is_empty():
    return event.app.current_buffer.text == ""

@kb.add("c-d", filter=is_empty)
def delete_buffer(event):
    event.app.exit()
```

---

## 7. 样式系统

**路径**: `prompt_toolkit.styles`

### 7.1 `Style` 类

**说明**: 定义颜色和样式属性。使用类名选择器匹配 UI 元素。

```python
from prompt_toolkit.styles import Style

style = Style.from_dict({
    # 语法：'fg:<颜色> bg:<颜色> <属性>'
    "prompt": "fg:ansiblue bold",
    "prompt.text": "fg:ansired",
    "status-bar": "bg:ansigreen fg:ansiwhite",
    "status-bar.key": "fg:ansiyellow",
})
```

**样式字符串语法**: `fg:<color> bg:<color> [bold] [italic] [underline] [blink] [reverse] [hidden] [dim]`

### 7.2 颜色格式

| 格式 | 示例 | 说明 |
|------|------|------|
| ANSI 色名 | `ansired`, `ansigreen`, `ansiblue` | 16 种标准 ANSI 颜色 |
| 命名 CSS 颜色 | `red`, `coral`, `darkorange` | 140+ 种 CSS 颜色名 |
| 十六进制 | `#ff0000`, `#f00` | 6 位或 3 位十六进制 |

完整 ANSI 色名: `ansidefault`, `ansiblack`, `ansired`, `ansigreen`, `ansiyellow`, `ansiblue`, `ansimagenta`, `ansicyan`, `ansigray`, `ansibrightblack`, `ansibrightred`, `ansibrightgreen`, `ansibrightyellow`, `ansibrightblue`, `ansibrightmagenta`, `ansibrightcyan`, `ansibrightwhite`

### 7.3 工具函数

| 函数 | 说明 |
|------|------|
| `merge_styles(styles)` | 合并多个样式，后者覆盖前者 |
| `parse_color(text)` | 解析/验证颜色格式，返回十六进制 |
| `style_from_pygments_cls(cls)` | 从 Pygments 样式类创建样式 |
| `style_from_pygments_dict(d)` | 从 Pygments 字典创建样式 |
| `pygments_token_to_classname(token)` | Pygments 令牌转类名 |

### 7.4 预置样式

| 函数 | 说明 |
|------|------|
| `default_ui_style()` | 返回默认 UI 样式定义 |
| `default_pygments_style()` | 返回默认 Pygments 兼容样式 |

### 7.5 `Attrs` 类

样式属性的具名元组: `color`, `bgcolor`, `bold`, `italic`, `underline`, `strike`, `blink`, `reverse`, `hidden`, `dim`

### 7.6 样式变换

运行时修改样式（如切换主题）。

| 类 | 说明 |
|----|------|
| `StyleTransformation` | 抽象基类 |
| `SwapLightAndDarkStyleTransformation` | 交换明/暗颜色 |
| `ReverseStyleTransformation` | 反转前景/背景色 |
| `SetDefaultColorStyleTransformation` | 设置默认前景/背景色 |
| `AdjustBrightnessStyleTransformation(brightness)` | 调整亮度 |
| `ConditionalStyleTransformation(transformation, filter)` | 条件变换 |
| `DummyStyleTransformation` | 恒等变换 |
| `DynamicStyleTransformation(get_transformation)` | 动态解析 |
| `merge_style_transformations(transformations)` | 链式合并多个变换 |

### 7.7 颜色常量

| 常量 | 说明 |
|------|------|
| `ANSI_COLOR_NAMES` | 16 个 ANSI 色名列表 |
| `NAMED_COLORS` | 140+ CSS 颜色名到十六进制的映射字典 |
| `DEFAULT_ATTRS` | 默认 `Attrs` 实例 |
---

## 8. 补全系统

**路径**: `prompt_toolkit.completion`

### 8.1 核心类型

#### `Completion`

单个补全项数据。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `text` | `str` | - | 要插入的文本 |
| `start_position` | `int` | `0` | 相对光标位置（<=0） |
| `display` | `AnyFormattedText` | `None` | 菜单显示文本 |
| `display_meta` | `AnyFormattedText` | `None` | 额外元信息 |
| `style` | `str` | `""` | 补全项样式 |
| `selected_style` | `str` | `""` | 选中时样式 |

#### `Completer`（抽象基类）

| 方法 | 说明 |
|------|------|
| `get_completions(document, complete_event)` | 生成 `Completion`（抽象方法） |
| `get_completions_async(document, complete_event)` | 异步版本，默认包装同步版 |

#### `CompleteEvent`

补全事件信息。

| 属性 | 类型 | 说明 |
|------|------|------|
| `text_inserted` | `bool` | 是否因输入触发 |
| `completion_requested` | `bool` | 是否用户主动请求（如 Tab） |

### 8.2 补全器实现

| 补全器 | 说明 |
|--------|------|
| `WordCompleter(words, ignore_case, match_middle, sentence)` | 从单词列表补全 |
| `FuzzyCompleter(completer, ...)` | 模糊匹配包装器 |
| `FuzzyWordCompleter(words, ...)` | 从单词列表模糊补全 |
| `NestedCompleter.from_nested_dict(data)` | 树形嵌套补全 |
| `PathCompleter(only_directories, expanduser, get_paths)` | 文件路径补全 |
| `ExecutableCompleter` | 可执行文件名补全 |
| `DeduplicateCompleter(completer)` | 去重补全器 |

```python
from prompt_toolkit.completion import WordCompleter, NestedCompleter

# 简单单词补全
completer = WordCompleter(["apple", "banana", "cherry"], ignore_case=True)

# 树形嵌套补全
completer = NestedCompleter.from_nested_dict({
    "show": {
        "version": None,
        "clock": None,
        "ip": {"brief": None, "detail": None},
    },
    "exit": None,
    "help": None,
})
```

### 8.3 包装器

| 类 | 说明 |
|----|------|
| `ThreadedCompleter(completer)` | 在后台线程中运行补全 |
| `ConditionalCompleter(completer, filter)` | 按条件启用 |
| `DynamicCompleter(get_completer)` | 动态解析 |
| `DummyCompleter` | 无补全 |
| `merge_completers(completers)` | 合并多个补全器 |
| `get_common_complete_suffix(document, completions)` | 获取共同前缀 |

---

## 9. 格式化文本

**路径**: `prompt_toolkit.formatted_text`

### 9.1 核心类型

#### `FormattedText`

`(style, text)` 元组列表。

```python
from prompt_toolkit.formatted_text import FormattedText

text = FormattedText([
    ("class:header", "标题\n"),
    ("fg:red bold", "警告信息\n"),
    ("", "普通文本"),
])
```

#### `AnyFormattedText`

类型别名：`Union[str, HTML, ANSI, FormattedText, Callable, None]`

#### `StyleAndTextTuples`

类型别名：`List[Tuple[str, str]]` — 每个元组为 `(样式, 文本)`。

### 9.2 格式化类

#### `HTML`

用 HTML 风格标签定义格式化文本。

```python
from prompt_toolkit import HTML

# 标签名自动映射为样式类
html = HTML("<b>粗体</b> <i>斜体</i> <u>下划线</u> <s>删除线</s>")

# 自定义颜色
html = HTML('<style fg="ansired" bg="ansiwhite">红色背景白字</style>')

# 元素名作为样式类名
html = HTML('<warning>警告</warning> <success>成功</success>')
```

#### `ANSI`

从 ANSI 转义序列解析格式化文本。

```python
from prompt_toolkit import ANSI

ansi = ANSI("\x1b[31m红色\x1b[0m \x1b[1m粗体\x1b[0m")
```

#### `PygmentsTokens`

将 Pygments 令牌列表转为格式化文本。

### 9.3 `Template`

字符串模板，支持 `{}` 占位符。

```python
from prompt_toolkit.formatted_text import Template
from prompt_toolkit import HTML

template = Template("  {}  ")
result = template.format(HTML("<b>标题</b>"))
```

### 9.4 工具函数

| 函数 | 说明 |
|------|------|
| `to_formatted_text(value, style, auto_convert)` | 将各种类型转为格式化文本 |
| `is_formatted_text(value)` | 类型检查 |
| `merge_formatted_text(texts)` | 合并多个格式化文本 |
| `fragment_list_len(fragments)` | 格式化文本显示长度（不计零宽字符） |
| `fragment_list_width(fragments)` | 格式化文本显示宽度 |
| `fragment_list_to_text(fragments)` | 还原为纯文本 |
| `split_lines(fragments)` | 按换行分割 |
| `to_plain_text(value)` | 任何格式化文本转为纯文本 |

---

## 10. 预置组件（Widgets）

**路径**: `prompt_toolkit.widgets`

### 10.1 `TextArea`

多功能文本输入组件（约 20 个参数）。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `text` | `str` | `""` | 初始文本 |
| `multiline` | `bool` | `True` | 多行模式 |
| `password` | `bool` | `False` | 密码模式 |
| `lexer` | `Lexer \| None` | `None` | 词法分析器 |
| `auto_suggest` | `AutoSuggest \| None` | `None` | 自动建议 |
| `completer` | `Completer \| None` | `None` | 补全器 |
| `complete_while_typing` | `bool` | `True` | 输入时补全 |
| `validator` | `Validator \| None` | `None` | 验证器 |
| `accept_handler` | `Callable \| None` | `None` | 接受回调 |
| `history` | `History \| None` | `None` | 历史记录 |
| `focusable` | `bool` | `True` | 可否聚焦 |
| `wrap_lines` | `bool` | `True` | 自动换行 |
| `read_only` | `bool` | `False` | 只读 |
| `width` | `AnyDimension` | `None` | 宽度 |
| `height` | `AnyDimension` | `None` | 高度 |
| `dont_extend_height` | `bool` | `False` | 不扩展高度 |
| `dont_extend_width` | `bool` | `False` | 不扩展宽度 |
| `line_numbers` | `bool` | `False` | 显示行号 |
| `scrollbar` | `bool` | `False` | 滚动条 |
| `style` | `str` | `""` | 样式 |
| `search_field` | `TextArea \| None` | `None` | 搜索框 |
| `preview_search` | `bool` | `True` | 预览搜索 |
| `prompt` | `AnyFormattedText` | `""` | 提示文本 |
| `input_processors` | `list` | `None` | 输入处理器 |
| `name` | `str` | `""` | 缓冲区名称 |

```python
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.layout import Window
from prompt_toolkit.lexers import PygmentsLexer
from pygments.lexers import PythonLexer

textarea = TextArea(
    text="print('hello')",
    multiline=True,
    lexer=PygmentsLexer(PythonLexer),
    line_numbers=True,
    scrollbar=True,
    style="bg:#222222 fg:#ffffff",
)
```

### 10.2 基础组件

| 组件 | 参数 | 说明 |
|------|------|------|
| `Label(text, style, width)` | `text: AnyFormattedText` | 静态文本显示 |
| `Button(text, handler, width)` | `handler: Callable` | 可点击按钮 |
| `Frame(title, body, style, width, height)` | `body: AnyContainer` | 带边框的框架 |
| `Shadow(body)` | `body: AnyContainer` | 阴影效果 |
| `Box(body, padding, style, width, height)` | `padding` 可各边独立设置 | 内边距容器 |
| `VerticalLine` | - | 竖线分隔符 |
| `HorizontalLine` | - | 横线分隔符 |

```python
from prompt_toolkit.widgets import Label, Button, Frame, Box, Shadow, Dialog
from prompt_toolkit.layout import HSplit, Window, FormattedTextControl

content = HSplit([
    Label(text="这是一个标签", style="bold"),
    Button(text="确定", handler=lambda: print("点击")),
])

frame = Frame(title="窗口", body=Box(body=content, padding=1))
```

### 10.3 选择组件

| 组件 | 说明 |
|------|------|
| `CheckboxList(values, default_values)` | 多选列表，`values` 为 `[(value, display), ...]` |
| `RadioList(values, default)` | 单选列表 |

```python
from prompt_toolkit.widgets import RadioList, CheckboxList

# 单选
radio = RadioList(
    values=[("a", "选项A"), ("b", "选项B"), ("c", "选项C")],
    default="a",
)

# 多选
checkbox = CheckboxList(
    values=[("py", "Python"), ("js", "JavaScript")],
    default_values=["py"],
)
```

### 10.4 `Dialog` 组件

| 参数 | 说明 |
|------|------|
| `title` | 弹窗标题 |
| `body` | 弹窗主体内容 |
| `buttons` | `list[Button]` 按钮列表 |
| `modal` | 是否模态 |
| `width` | 宽度 |
| `with_background` | 是否带背景层 |

```python
from prompt_toolkit.widgets import Dialog, Button, Label, TextArea
from prompt_toolkit.layout import HSplit

dialog = Dialog(
    title="编辑",
    body=TextArea(text="内容", multiline=False),
    buttons=[
        Button(text="确定", handler=lambda: print("确定")),
        Button(text="取消", handler=lambda: print("取消")),
    ],
    width=60,
)
```

### 10.5 菜单

| 组件 | 说明 |
|------|------|
| `MenuContainer(body, menu_items, floats)` | 菜单栏容器 |
| `MenuItem(text, handler, children)` | 菜单项，支持子菜单 |

```python
from prompt_toolkit.widgets import MenuContainer, MenuItem

menu = MenuContainer(
    body=TextArea("内容"),
    menu_items=[
        MenuItem("文件", children=[
            MenuItem("新建", handler=lambda: ...),
            MenuItem("保存", handler=lambda: ...),
            MenuItem("退出", handler=lambda: ...),
        ]),
        MenuItem("编辑", children=[
            MenuItem("撤销", handler=lambda: ...),
            MenuItem("重做", handler=lambda: ...),
        ]),
    ],
)
```

### 10.6 工具栏

| 组件 | 说明 |
|------|------|
| `ArgToolbar` | Vi 重复计数参数显示 |
| `CompletionsToolbar` | 补全状态信息 |
| `FormattedTextToolbar(text, style)` | 自定义文本工具栏 |
| `SearchToolbar` | 渐进搜索工具栏 |
| `SystemToolbar(prompt)` | 系统命令工具栏 |
| `ValidationToolbar` | 验证错误信息显示 |

---

## 11. 输入/输出

### 11.1 输入系统

**路径**: `prompt_toolkit.input`

#### `Input`（抽象基类）

| 方法 | 说明 |
|------|------|
| `fileno()` | 文件描述符 |
| `read()` | 读取输入 |
| `close()` | 关闭 |
| `isatty()` | 是否为 TTY |
| `typeahead_hash()` | 类型预判哈希 |

#### 具体实现

| 类 | 说明 |
|----|------|
| `PipeInput` | 可通过 `send_text(text)` 编程式输入 |
| `DummyInput` | 立即返回 EOF |
| `create_input(stdin, always_prefer_tty)` | 自动创建平台合适的输入 |
| `create_pipe_input()` | 上下文管理器，创建 PipeInput |

```python
from prompt_toolkit.input import create_pipe_input

with create_pipe_input() as inp:
    inp.send_text("hello\n")
    result = prompt("> ", input=inp)
```

### 11.2 输出系统

**路径**: `prompt_toolkit.output`

#### `Output`（抽象基类）

终端控制方法（约 20+）：

| 方法 | 说明 |
|------|------|
| `write(data)` | 写入数据 |
| `flush()` | 刷新 |
| `fileno()` | 文件描述符 |
| `encoding()` | 编码 |
| `set_title(title)` | 设置终端标题 |
| `clear_title()` | 清除标题 |
| `erase_screen()` | 擦除屏幕 |
| `enter_alternate_screen()` | 进入备用屏幕 |
| `quit_alternate_screen()` | 退出备用屏幕 |
| `enable_mouse_support()` | 启用鼠标 |
| `disable_mouse_support()` | 禁用鼠标 |
| `erase_end_of_line()` | 擦除行尾 |
| `reset_attributes()` | 重置属性 |
| `cursor_goto(row, col)` | 移动光标 |
| `cursor_up/down/forward/backward(amount)` | 光标移动 |
| `hide_cursor()` / `show_cursor()` | 光标显隐 |
| `set_cursor_shape(shape)` | 设置光标形状 |
| `get_size()` | 获取终端尺寸 |
| `ask_for_cpr()` | 请求光标位置报告 |

#### 具体实现

| 类/函数 | 说明 |
|---------|------|
| `DummyOutput` | 丢弃所有输出 |
| `create_output(stdout, always_prefer_tty)` | 自动创建平台合适的输出 |

### 11.3 `ColorDepth` 枚举

| 值 | 别名 | 说明 |
|----|------|------|
| `DEPTH_1_BIT` | `MONOCHROME` | 单色 |
| `DEPTH_4_BIT` | `ANSI_COLORS_ONLY` | 16 色 |
| `DEPTH_8_BIT` | `DEFAULT` | 256 色 |
| `DEPTH_24_BIT` | `TRUE_COLOR` | 真彩色 |

| 方法 | 说明 |
|------|------|
| `from_env()` | 从环境变量检测色彩深度 |
| `default()` | 返回默认值 |

---

## 12. 验证、历史、自动建议、词法分析器

### 12.1 验证

**路径**: `prompt_toolkit.validation`

#### `Validator`（抽象基类）

| 方法 | 说明 |
|------|------|
| `validate(document)` | 验证文档，不通过则抛出 `ValidationError`（抽象） |
| `validate_async(document)` | 异步验证，默认包装同步版 |

#### `Validator.from_callable()` 类方法

从简单函数快速创建验证器。

```python
from prompt_toolkit.validation import Validator

# 快速创建
validator = Validator.from_callable(
    lambda text: len(text) >= 3,
    error_message="至少输入 3 个字符",
    move_cursor_to_end=True,
)
```

#### `ValidationError`

| 属性 | 说明 |
|------|------|
| `cursor_position` | 错误位置 |
| `message` | 错误消息 |

#### 辅助验证器

| 类 | 说明 |
|----|------|
| `ThreadedValidator(validator)` | 在后台线程中验证 |
| `DummyValidator` | 接受所有输入 |
| `ConditionalValidator(validator, filter)` | 按条件验证 |
| `DynamicValidator(get_validator)` | 动态解析 |

### 12.2 历史

**路径**: `prompt_toolkit.history`

#### `History`（抽象基类）

| 方法 | 说明 |
|------|------|
| `load()` | 加载历史（异步生成器） |
| `get_strings()` | 获取已加载的字符串（旧→新） |
| `append_string(string)` | 追加字符串 |
| `load_history_strings()` | 加载历史字符串（抽象，新→旧） |
| `store_string(string)` | 持久化存储（抽象） |

#### 实现

| 类 | 说明 |
|----|------|
| `InMemoryHistory(history_strings)` | 内存历史 |
| `FileHistory(filename)` | 文件历史（每行一个条目，`+` 开头，`#` 记录时间戳） |
| `ThreadedHistory(history)` | 后台线程加载 |
| `DummyHistory` | 无操作 |

```python
from prompt_toolkit.history import FileHistory

session = PromptSession(history=FileHistory("~/.my_history"))
```

### 12.3 自动建议

**路径**: `prompt_toolkit.auto_suggest`

#### `Suggestion`

| 属性 | 说明 |
|------|------|
| `text` | 建议文本 |

#### `AutoSuggest`（抽象基类）

| 方法 | 说明 |
|------|------|
| `get_suggestion(buffer, document)` | 获取建议（同步，抽象） |
| `get_suggestion_async(buffer, document)` | 获取建议（异步） |

#### 实现

| 类 | 说明 |
|----|------|
| `AutoSuggestFromHistory` | 基于历史记录的自动建议 |
| `ThreadedAutoSuggest(auto_suggest)` | 后台线程中运行 |
| `DummyAutoSuggest` | 无建议 |
| `ConditionalAutoSuggest(auto_suggest, filter)` | 按条件启用 |
| `DynamicAutoSuggest(get_auto_suggest)` | 动态解析 |

```python
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

session = PromptSession(
    auto_suggest=AutoSuggestFromHistory(),
)
```

### 12.4 词法分析器

**路径**: `prompt_toolkit.lexers`

#### `Lexer`（抽象基类）

| 方法 | 说明 |
|------|------|
| `lex_document(document)` | 返回 `Callable[[int], StyleAndTextTuples]`（抽象） |
| `invalidation_hash()` | 失效哈希 |

#### 实现

| 类 | 说明 |
|----|------|
| `SimpleLexer(style)` | 全文本统一样式 |
| `PygmentsLexer(pygments_lexer_cls)` | 使用 Pygments 词法分析器 |
| `DynamicLexer(get_lexer)` | 动态解析 |

```python
from prompt_toolkit.lexers import PygmentsLexer
from pygments.lexers import PythonLexer, JsonLexer, HtmlLexer

lexer = PygmentsLexer(PythonLexer)
```

#### 语法同步策略

| 策略 | 说明 |
|------|------|
| `SyntaxSync` | 抽象基类 |
| `SyncFromStart` | 从文档开头开始同步 |
| `RegexSync(pattern)` | 从匹配正则的位置同步 |

---

## 13. 其他模块

### 13.1 剪贴板

**路径**: `prompt_toolkit.clipboard`

| 类 | 说明 |
|----|------|
| `Clipboard` | 抽象基类（set_data, get_data, rotate） |
| `ClipboardData(text, type)` | 剪贴板数据（SelectionType） |
| `InMemoryClipboard(data)` | 内存剪贴板 |
| `DummyClipboard` | 空剪贴板 |
| `DynamicClipboard(get_clipboard)` | 动态解析 |

### 13.2 事件系统

**路径**: `prompt_toolkit.utils.Event`

```python
from prompt_toolkit.utils import Event

event = Event(sender)
event += handler    # 注册
event -= handler    # 注销
event.fire()        # 触发
```

### 13.3 `patch_stdout`

**路径**: `prompt_toolkit.patch_stdout`

重定向 `sys.stdout`，使打印内容不会破坏 prompt_toolkit UI。

```python
from prompt_toolkit import prompt
from prompt_toolkit.patch_stdout import patch_stdout

with patch_stdout():
    text = prompt("> ")  # 此期间 print() 正常输出
```

### 13.4 枚举与数据结构

#### `EditingMode`

| 值 | 说明 |
|----|------|
| `EditingMode.VI` | Vi 编辑模式 |
| `EditingMode.EMACS` | Emacs 编辑模式 |

#### `SelectionType`

| 值 | 说明 |
|----|------|
| `SelectionType.CHARACTERS` | 字符选择 |
| `SelectionType.LINES` | 行选择 |
| `SelectionType.BLOCK` | 块选择 |

#### `PasteMode`

| 值 | 说明 |
|----|------|
| `PasteMode.EMACS` | Emacs 粘贴 |
| `PasteMode.VI_AFTER` | Vi 光标后粘贴 |
| `PasteMode.VI_BEFORE` | Vi 光标前粘贴 |

#### `SearchDirection`

| 值 | 说明 |
|----|------|
| `SearchDirection.FORWARD` | 向前搜索 |
| `SearchDirection.BACKWARD` | 向后搜索 |

#### `SearchState`

| 属性 | 类型 | 说明 |
|------|------|------|
| `text` | `str` | 搜索文本 |
| `direction` | `SearchDirection` | 搜索方向 |
| `ignore_case` | `FilterOrBool` | 忽略大小写 |

#### `CursorShape`

| 值 | 说明 |
|----|------|
| `BLOCK`, `BEAM`, `UNDERLINE` | 块状/竖线/下划线 |
| `BLINKING_BLOCK`, `BLINKING_BEAM`, `BLINKING_UNDERLINE` | 闪烁变体 |

#### `CursorShapeConfig`

| 类 | 说明 |
|----|------|
| `SimpleCursorShapeConfig(cursor_shape)` | 固定光标形状 |
| `ModalCursorShapeConfig` | 根据编辑模式自动切换（Vi 导航=块，Vi 插入/Emacs=竖线） |
| `DynamicCursorShapeConfig(get_config)` | 动态解析 |

#### `Point` / `Size`

```python
from prompt_toolkit.data_structures import Point, Size

Point(x=0, y=5)
Size(rows=24, columns=80)
```

### 13.5 事件循环工具

**路径**: `prompt_toolkit.eventloop`

| 函数/类 | 说明 |
|---------|------|
| `run_in_executor_with_context(func, *args)` | 在线程池中运行（保留 contextvars） |
| `call_soon_threadsafe(func)` | 线程安全回调调度 |
| `get_traceback_from_context(context)` | 从异常上下文提取回溯 |
| `InputHook` | GUI 事件循环集成钩子类型 |
| `InputHookContext` | 输入钩子上下文 |
| `new_eventloop_with_inputhook(inputhook)` | 创建带输入钩子的事件循环 |
| `generator_to_async_generator(gen)` | 同步生成器转异步生成器 |
| `aclosing(agen)` | 安全关闭异步生成器 |

### 13.6 `contrib` 扩展

#### 正则语言

**路径**: `prompt_toolkit.contrib.regular_languages`

```python
from prompt_toolkit.contrib.regular_languages import compile

# 编译正则语言语法
grammar = compile(r"(?P<command>\w+)\s+(?P<argument>\w+)")

# 检查匹配
m = grammar.match("show version")
if m:
    variables = m.variables()  # {"command": "show", "argument": "version"}
```

支持自动从语法生成补全器、验证器、词法分析器。

#### SSH 服务器

**路径**: `prompt_toolkit.contrib.ssh`

| 类 | 说明 |
|----|------|
| `PromptToolkitSSHServer(interact, server_host_keys)` | SSH 服务器，通过 asyncssh 运行 prompt_toolkit 应用 |
| `PromptToolkitSSHSession` | 单个 SSH 会话 |

```python
from prompt_toolkit.contrib.ssh import PromptToolkitSSHServer
from prompt_toolkit import prompt

async def interact():
    result = await prompt("SSH> ").prompt_async()
    print(f"Received: {result}")

server = PromptToolkitSSHServer(
    interact=interact,
    server_host_keys=["/etc/ssh/ssh_host_rsa_key"],
)
```

#### Telnet 服务器

**路径**: `prompt_toolkit.contrib.telnet`

| 类 | 说明 |
|----|------|
| `TelnetServer(interact, port, host)` | Telnet 服务器 |

#### 系统命令补全

**路径**: `prompt_toolkit.contrib.completers`

| 补全器 | 说明 |
|--------|------|
| `SystemCompleter(get_paths, get_environ_vars)` | 系统可执行文件和路径补全 |
