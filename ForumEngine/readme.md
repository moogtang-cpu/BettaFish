**ForumEngine — 目录说明与运行指南**

本文件为 `ForumEngine` 目录的架构与业务流程说明，基于代码阅读（`llm_host.py`、`monitor.py`）整理而成，便于维护、集成与调试。

**概要**
- **目的**: 监听Insight/Media/Query三套引擎的 `SummaryNode`/`ReportFormattingNode` 输出，将有价值的段落抽取到统一的 `forum.log`，并在必要时由一个 LLM 驱动的“主持人”生成引导性发言。
- **主要功能**: 实时文件监控、Summary JSON 捕获与修复、去重/清理输出、主持人发言触发与写入。

**目录核心文件**
- **`llm_host.py`**: [ForumEngine/llm_host.py](ForumEngine/llm_host.py#L1-L263)
  - 提供 `ForumHost` 类与简洁接口 `generate_host_speech(forum_logs: List[str])`。
  - 使用配置中的 LLM 凭据（`FORUM_HOST_API_KEY` / `FORUM_HOST_BASE_URL` / `FORUM_HOST_MODEL_NAME`），通过 `OpenAI` 客户端调用 chat completion 生成主持人发言。
  - 主要职责：解析传入的 agent 日志、构建系统与用户 prompt（包含发言结构要求）、调用 LLM、格式化输出。
- **`monitor.py`**: [ForumEngine/monitor.py](ForumEngine/monitor.py#L1-L859)
  - 提供 `LogMonitor` 类与启动/停止辅助函数 (`start_forum_monitoring`, `stop_forum_monitoring`)。
  - 连续监控三个日志文件：`insight.log`、`media.log`、`query.log`（默认 `logs/` 目录）。
  - 职责细化：检测目标节点输出（多种识别策略）、捕获多行 JSON、修复常见 JSON 格式问题、过滤错误块、写入 `forum.log`、维护主持人发言缓冲并触发 `llm_host`。

**主要概念与设计要点**
- **目标节点识别**: 通过类名、模块路径、关键标识文本等多模式识别 `SummaryNode` 的输出，兼容旧/新日志格式。
- **JSON 捕获与修复**: 支持单行与多行 JSON；在解析失败时尝试 `fix_json_string`（状态机方式转义未处理的双引号）；仅解析目标节点的 JSON。
- **错误块处理**: 基于日志级别（检测 `| ERROR |` 等）进入 ERROR 块期间会暂停 JSON 捕获，避免污染数据。
- **主持人触发机制**: 将被抽取的 agent 发言缓存在 `agent_speeches_buffer`，达到阈值（默认 5 条）会同步触发 `ForumHost.generate_host_speech`，并把主持人输出写回 `forum.log`。
- **线程与并发**: 监控采用后台线程；对 `forum.log` 写入使用 `Lock` 以保证线程安全。

**业务流程（高层，步骤化）**
1. 启动监控：调用 `start_forum_monitoring()`，内部创建并启动 `LogMonitor.monitor_logs` 后台线程。
2. 基线记录：监控器在启动时记录每个被监控日志的当前行数和文件位置。
3. 变更检测：循环中按秒检测三份日志的增长或缩短。
4. FirstSummary 触发会话：当检测到首次段落（如 `FirstSummaryNode` 或包含“正在生成首次段落总结”）时，进入会话模式，`clear_forum_log()` 重置 `forum.log` 并写入开始标记。
5. 捕获内容：对新增行，使用 `is_target_log_line` + `is_json_start_line` 判断；若是 JSON 开始则进入多行捕获并在结束后解析；若是有价值的纯文本则直接抽取并清理标签。
6. 写入与缓冲：将清理后的内容以单行（将换行转义为 `\\n`）写入 `forum.log`，并把时间戳 + 来源标签（INSIGHT/MEDIA/QUERY）添加到 `agent_speeches_buffer`。
7. 主持人生成：当缓冲达到阈值，调用 `generate_host_speech`（传入最近若干条发言），将主持人文本写入 `forum.log`（来源为 HOST），并从缓冲中移除已处理发言。
8. 会话结束：如果日志被截断（缩短）或长期无活动（超时计数器），监控器会结束当前会话并写入结束标记。

ASCII 流程示意：

INSIGHT.log / MEDIA.log / QUERY.log  --(监控检测)--> LogMonitor.process_lines_for_json
    --> 捕获/修复 JSON 或 抽取纯文本 --> 写入 forum.log（并入缓冲）
    --> 达到阈值 --> 调用 llm_host.generate_host_speech --> 写入 HOST 到 forum.log

**配置项**
- 配置来源: 全局 `config.py`（或各引擎的 utils/config.py）中包含以下字段：
  - **FORUM_HOST_API_KEY**: 主持人 LLM API 密钥。[config.py](config.py#L70-L72)
  - **FORUM_HOST_BASE_URL**: 主机 LLM Base URL（如果使用非公开 endpoint）。
  - **FORUM_HOST_MODEL_NAME**: LLM 模型标识（如 Qwen3/…）。

示例环境变量（参考）:
```
FORUM_HOST_API_KEY=sk-xxxxx
FORUM_HOST_BASE_URL=https://api.siliconflow.cn/v1
FORUM_HOST_MODEL_NAME=Qwen/Qwen3-235B-A22B-Instruct-2507
```

**运行与集成示例**
- 以代码方式启动监控：
```
from ForumEngine import LogMonitor

mon = LogMonitor(log_dir='logs')
mon.start_monitoring()
# 运行中按需调用 mon.stop_monitoring()
```
- 或使用模块级快捷函数：
```
from ForumEngine.monitor import start_forum_monitoring, stop_forum_monitoring
start_forum_monitoring()
# ...
stop_forum_monitoring()
```

**日志与文件格式说明**
- `forum.log` 每条记录为单行，内部将实际换行转换为 `\\n`，格式示例：
  - `[HH:MM:SS] [INSIGHT] 首次总结: ...` 或 `[HH:MM:SS] [HOST] 主持人发言内容`
- 监控器支持两种来源日志格式：旧的 `[HH:MM:SS] ...` 和基于 `loguru` 的 `YYYY-MM-DD HH:mm:ss.SSS | LEVEL | module - ...`。

**常见问题与故障排查**
- 主持人未生成发言：检查 `FORUM_HOST_API_KEY` 与 `FORUM_HOST_BASE_URL` 是否正确、`HOST_AVAILABLE` 是否为 True（`llm_host` 导入失败会降级为纯监控模式）。
- JSON 解析频繁失败：查看日志中是否存在未转义双引号或控制字符，`monitor.fix_json_string` 会尝试修复常见情况，但极端损坏可能无法自动恢复。
- 捕获不到内容：确认被监控的引擎是否在 `SummaryNode` 中打印了可识别的标识（类名、模块路径或关键文本）。可调整 `target_node_patterns` 以兼容更多格式。

**扩展建议 / 下一步**
- 将 `target_node_patterns` 配置化以支持运行时扩展与热更新。
- 提供可选的异步主持人生成（将 `generate_host_speech` 放入独立线程/任务队列），以避免阻塞监控主循环。
- 将 `forum.log` 持久化到 DB 或增加 rotation/压缩策略，便于长期分析与归档。

---
文件实现参考：
- `ForumEngine/llm_host.py` — 主持人实现与 prompt 构造。
- `ForumEngine/monitor.py` — 日志监控、JSON 捕获与会话管理。

如果你希望我把 README 翻译为英文、增加示意图（SVG/PlantUML）或把 `target_node_patterns` 提取为可配置变量，我可以继续实现。
