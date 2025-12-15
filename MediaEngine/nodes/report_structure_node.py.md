```markdown
# MediaEngine/nodes/report_structure_node.py 业务逻辑说明

此文档面向工程师与 AI 代码助手，概述 `ReportStructureNode` 的职责、输入/输出契约、关键实现细节、常见调用示例与变更建议。

概述
- 位置：`MediaEngine/nodes/report_structure_node.py`
- 作用：根据用户查询（`query`）调用 LLM 生成报告的整体结构（段落列表），并能将生成的结构写入 `State`（通过 `mutate_state`）。
- 依赖：
  - `llm_client`（需要实现 `stream_invoke_to_string` 方法，通常注入 `MediaEngine/llms/base.LLMClient` 的实例）。
  - 提示模板：`SYSTEM_PROMPT_REPORT_STRUCTURE`（位于 `MediaEngine/prompts`）。
  - 文本/JSON 清洗工具：`remove_reasoning_from_output`, `clean_json_tags`, `extract_clean_response`, `fix_incomplete_json`（位于 `MediaEngine/utils/text_processing.py`）。
  - 状态模型：`..state.state.State`，提供 `add_paragraph(title, content)` 方法。

输入/输出契约
- 初始化参数：`llm_client`, `query: str`（必须为非空字符串）。
- `run()` 返回：一个 `List[Dict[str, str]]`，每个 dict 包含 `title` 和 `content`。这是报告的段落结构列表。
- `mutate_state(state)`：接收或创建 `State` 对象，将 `query` 和 `report_title` 写入状态，并将每个段落通过 `state.add_paragraph` 添加到状态中，最终返回更新后的 `State`。

主要方法详解
- `__init__(self, llm_client, query: str)`
  - 保存 `llm_client` 与 `query`，并将节点类型设置为 `ReportStructureNode`（继承自 `StateMutationNode`）。

- `validate_input(self, input_data: Any) -> bool`
  - 验证 `self.query` 是非空字符串。该节点的运行不依赖 `input_data` 参数，而是使用初始化时的 `query`。

- `run(self, input_data: Any = None, **kwargs) -> List[Dict[str, str]]`
  - 调用 LLM：`response = self.llm_client.stream_invoke_to_string(SYSTEM_PROMPT_REPORT_STRUCTURE, self.query)`。
  - 将 LLM 原始输出传给 `process_output` 进行清洗和结构化。
  - 返回经过验证的段落结构列表，或在异常情况下抛出异常。

- `process_output(self, output: str) -> List[Dict[str, str]]`
  - 清洗：先用 `remove_reasoning_from_output` 去除模型的思考性文本，然后用 `clean_json_tags` 去掉常见包装/标签。
  - 解析 JSON：尝试 `json.loads`，若失败则：
    - 先尝试 `extract_clean_response(cleaned_output)`（更强的抽取逻辑）；
    - 若仍包含错误，调用 `fix_incomplete_json(cleaned_output)` 修复不完整 JSON；
    - 修复成功后重试 `json.loads`；否则退回到 `_generate_default_structure()`。
  - 规范化：确保解析结果为 `list`，若是 `dict` 则包装成列表；否则使用默认结构。
  - 验证每个段落的结构：每个段落必须为 `dict` 且包含 `title` 和 `content`。缺失或不合规范的段落会被跳过。
  - 如果没有有效段落，返回 `_generate_default_structure()`。

- `_generate_default_structure(self) -> List[Dict[str,str]]`
  - 返回一个小的默认结构（示例：`研究概述`和`深度分析`），用于降级或解析失败时保证后续流程有基础数据。

- `mutate_state(self, input_data: Any = None, state: State = None, **kwargs) -> State`
  - 负责将 `run()` 生成的段落结构写入状态：
    - 若 `state` 为 `None`，会创建一个新的 `State()`。
    - 将 `state.query` 设置为当前 `query`。
    - 若 `state.report_title` 为空，则设置为 `关于'{query}'的深度研究报告`。
    - 遍历段落并调用 `state.add_paragraph(title=..., content=...)`。
  - 错误时记录日志并向上抛出异常。

鲁棒性与设计要点
- 多阶段 JSON 修复：节点容忍 LLM 产生的非标准 JSON，通过 `extract_clean_response` 与 `fix_incomplete_json` 进行二次处理，尽可能还原结构化输出，避免单点失败。
- 防护降级：任何解析/验证失败都将导致返回预设的默认结构，从而保证管道下游仍能运行。
- 日志细粒度：使用 `loguru` 打印清理后的输出、解析错误和逐段验证警告，有助于离线调试 LLM 输出质量。
- 纯函数风格处理：`process_output` 侧重输入->输出转换，`mutate_state` 负责副作用（写入 State）。这种分离有利于单元测试。

调用示例

```py
from MediaEngine.nodes.report_structure_node import ReportStructureNode
from MediaEngine.llms.base import LLMClient
from config import settings

llm = LLMClient(settings.MEDIA_ENGINE_API_KEY, settings.MEDIA_ENGINE_MODEL_NAME, settings.MEDIA_ENGINE_BASE_URL)
node = ReportStructureNode(llm, query="武汉大学 品牌 舆情")

# 直接生成结构
structure = node.run()
print(structure)

# 将结构写入状态
from MediaEngine.state.state import State
state = State()
state = node.mutate_state(state=state)
```

测试与调试建议
- 单元测试要点：
  - 对 `process_output` 编写多个用例：合法 JSON、被包装的 JSON、分多行的 JSON、以及无法修复的非 JSON 文本，验证返回值和日志行为。
  - 测试 `mutate_state` 是否正确设置 `state.query`、`state.report_title` 以及调用 `state.add_paragraph` 的次数和参数。
- 手动调试：将不同变体的 LLM 输出写入一个临时字符串，直接调用 `process_output` 以观察解析与修复路径。
- 若要模拟 LLM 行为，可替换 `llm_client` 为一个具有 `stream_invoke_to_string` 的假实现，返回预设字符串。

变更建议（对 Copilot / PR 的约束）
- 更严格的 schema 验证：考虑引入 `pydantic` 模型来定义段落 schema（`title: str`, `content: str`），在 `process_output` 验证阶段使用它来提供更明确的错误信息。
- 抽象化提取器：将 `extract_clean_response` 与 `fix_incomplete_json` 封装为可注入的策略对象，便于在不同场景下替换或增强（例如使用正则增强、或调用第三方清洗服务）。
- 可观测性改进：记录 LLM 原始响应的哈希或片段以便关联日志与模型输出，同时避免记录可能包含敏感信息的完整内容。
- 可配置的降级策略：将 `_generate_default_structure` 的默认段落置入配置或模板文件，便于产品级定制而不改代码。

注意事项
- 请不要在模块导入时启动网络请求或长生命周期的任务；节点应保持易测试和无副作用。
- 修改 `SYSTEM_PROMPT_REPORT_STRUCTURE`（提示词）时务必同步更新测试样例，因为提示改变会直接影响 LLM 输出格式与可解析性。

---

如果你想，我可以：
- 为 `process_output` 写一组单元测试样例（包括常见的坏输出），或
- 把默认结构抽成配置文件并创建一个小的迁移 PR。

请选择下一步。```
