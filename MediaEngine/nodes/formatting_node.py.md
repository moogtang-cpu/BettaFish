```markdown
# MediaEngine/nodes/formatting_node.py 业务逻辑说明

此文档面向工程师与AI代码助手，介绍 `ReportFormattingNode` 的职责、输入/输出契约、关键行为、调用示例和改动建议。风格与仓库内其他 `*.md` 分析文档保持一致。

概述
- 位置：`MediaEngine/nodes/formatting_node.py`
- 目的：将 Report/章节级的中间表示（段落列表）通过 LLM 或手动逻辑格式化为最终的 Markdown 报告。支持流式 LLM 输出的安全拼接，并提供纯 Python 的备用手动格式化方法。
- 依赖：
  - `llm_client`：一个兼容的 LLM 客户端（提供 `stream_invoke_to_string`），通常由上层 Agent 注入。
  - `..prompts.SYSTEM_PROMPT_REPORT_FORMATTING`：LLM 的系统提示模板。
  - 工具函数：`remove_reasoning_from_output`, `clean_markdown_tags`（位于 `MediaEngine/utils/text_processing.py`），用于清洗 LLM 输出中的推理痕迹与不规范 Markdown 标签。

输入/输出契约
- 输入（`run` 的 `input_data`）：
  - 接受 JSON 字符串或 Python 列表。
  - 必需：每个段落项为 dict，包含 `title`（段落标题）和 `paragraph_latest_state`（段落文本）字段。
  - `validate_input` 对字符串会尝试 `json.loads`，对列表会直接验证各项结构。
- 输出：
  - 返回一个 Markdown 格式的字符串（`str`）。
  - 若 LLM 生成为空或失败，`process_output` 会返回一个带错误提示的 Markdown 文本（例如 `# 报告生成失败`）。

主要方法详解
- `__init__(self, llm_client)`
  - 构造函数把 `llm_client` 注入到 `BaseNode`。期望 `llm_client` 支持 `stream_invoke_to_string(system_prompt, message)`。

- `validate_input(self, input_data)`
  - 校验规则：每个条目必须是 dict 且含 `title` 与 `paragraph_latest_state`。
  - 对 JSON 字符串会尝试解析并校验返回结构。

- `run(self, input_data, **kwargs)`
  - 流程：
    1. 验证输入格式，若不合法抛出 `ValueError`。
    2. 将输入转为 JSON 字符串（若原本是列表则调用 `json.dumps(..., ensure_ascii=False)`）。
    3. 使用 `self.llm_client.stream_invoke_to_string(SYSTEM_PROMPT_REPORT_FORMATTING, message)` 调用 LLM（流式、安全拼接）。
    4. 将 LLM 输出传入 `process_output` 做清洗与结构保障后返回。
  - 错误处理：捕获 Exception，记录日志并再次抛出，调用者应做好上层捕获。

- `process_output(self, output)`
  - 先调用 `remove_reasoning_from_output`（去掉模型的“思考性”或中间推理文本）。
  - 再调用 `clean_markdown_tags` 清理不规范或多余的 Markdown 标签。
  - 如果结果为空，返回 `# 报告生成失败` 的占位 Markdown；如果输出缺少标题（不以 `#` 开头），自动在前面加 `# 深度研究报告`。
  - `process_output` 在出现异常时会记录错误并返回 `# 报告处理失败` 的占位文本。

- `format_report_manually(self, paragraphs_data, report_title="深度研究报告")`
  - 备用的本地格式化器，不依赖 LLM。用于：测试、离线环境、LLM 返回不可靠时的回退。
  - 构建规则：
    - 报告以 `# {report_title}` 开头，段落按顺序添加 `## {title}` 与段落内容，段落之间用 `---` 分隔。
    - 若段落数大于 1，自动附加 `## 结论` 节，总结性文字为模板化内容。
  - 出错时同样记录日志并返回错误占位 Markdown。

异常与日志
- 使用 `loguru.logger` 记录关键步骤与错误（例如 `正在格式化最终报告` / `成功生成格式化报告` / `报告格式化失败`）。
- `run` 捕获所有异常后会 `logger.exception(...)` 并抛出，保证栈信息被记录。

调用示例
```py
from MediaEngine.nodes.formatting_node import ReportFormattingNode
from MediaEngine.llms.base import LLMClient
from config import settings

llm = LLMClient(settings.MEDIA_ENGINE_API_KEY, settings.MEDIA_ENGINE_MODEL_NAME, settings.MEDIA_ENGINE_BASE_URL)
node = ReportFormattingNode(llm)

# 假设 paragraphs 是符合结构的列表
markdown = node.run(paragraphs)
print(markdown)

# 无 LLM 环境下，使用手动格式化
manual = node.format_report_manually(paragraphs, report_title='自定义报告')
```

测试与调试提示
- 单元测试：参考 `tests/test_report_engine_sanitization.py`（若存在）以理解格式化器期望的输出样式。
- 本地调试：可直接构造一个符合 `validate_input` 的小列表并调用 `format_report_manually` 来验证模板化输出。
- 若 LLM 输出中出现多余的推理或无关元信息，首选调整 `SYSTEM_PROMPT_REPORT_FORMATTING`（位于 `MediaEngine/prompts`）以约束模型输出格式，或增强 `remove_reasoning_from_output` 的清洗规则。

变更建议
- 扩展 LLM 参数：如果需要 `max_tokens`、`stop`、或其他模型特性，建议在 `llm_client` 的调用方统一传参并在 `LLMClient` 中允许这些参数通过（参考 `MediaEngine/llms/base.py`）。
- 提供可插拔的清洗器：把 `remove_reasoning_from_output` 与 `clean_markdown_tags` 抽象成可注入的清洗策略，便于在不同场景下替换或扩展解析规则。
- 更严格的结构校验：考虑在 `validate_input` 中增加 schema 检查（例如使用 `pydantic`），以便更早捕获字段错误。

注意事项
- 不要在模块导入时启动长生命周期线程或进行 I/O 操作；该节点应为可复用、无副作用的类。
- 修改 `SYSTEM_PROMPT_REPORT_FORMATTING` 时要同时检查 `tests/` 中与报告生成相关的用例以避免行为回归。

---

如果你想，我可以把该说明并入 `MediaEngine/nodes/README.md`（如果有），或为 `ReportEngine` 的测试添加一个针对该节点的示例测试用例。欢迎指示下一步。```
