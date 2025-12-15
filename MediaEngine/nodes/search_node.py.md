```markdown
# MediaEngine/nodes/search_node.py 业务逻辑说明

本文档面向开发者与 AI 代码助手，介绍 `FirstSearchNode` 与 `ReflectionNode`（位于 `MediaEngine/nodes/search_node.py`）的职责、输入/输出契约、实现细节、调用示例与变更建议。

概述
- 位置：`MediaEngine/nodes/search_node.py`
- 目的：
  - `FirstSearchNode`：为段落生成首次搜索查询（`search_query`）及其推理（`reasoning`）。
  - `ReflectionNode`：基于段落当前状态（包括 `paragraph_latest_state`）进行“反思”，生成补充/改进的搜索查询及推理。
- 依赖：
  - `llm_client`：注入的 LLM 客户端，需实现 `stream_invoke_to_string(system_prompt, message)`。
  - 提示词：`SYSTEM_PROMPT_FIRST_SEARCH`, `SYSTEM_PROMPT_REFLECTION`（位于 `MediaEngine/prompts`）。
  - 文本清洗工具：`remove_reasoning_from_output`, `clean_json_tags`, `extract_clean_response`, `fix_incomplete_json`（位于 `MediaEngine/utils/text_processing.py`）。

输入 / 输出 契约
- `FirstSearchNode.run(input_data)`：
  - 输入：JSON 字符串或 dict，必须包含 `title` 和 `content` 字段。
  - 输出：dict，至少包含 `search_query`（str）和 `reasoning`（str，可空）。若无法从模型获得有效查询，会返回默认查询：`{"search_query": "相关主题研究", "reasoning": "由于解析失败，使用默认搜索查询"}`。

- `ReflectionNode.run(input_data)`：
  - 输入：JSON 字符串或 dict，必须包含 `title`, `content`, `paragraph_latest_state`。
  - 输出：dict，结构同上。默认反思查询为：`{"search_query": "深度研究补充信息", "reasoning": "由于解析失败，使用默认反思搜索查询"}`。

主要方法与行为
- 初始化（`__init__(llm_client)`）
  - 仅注入 `llm_client` 并调用 `BaseNode` 构造，节点名称分别为 `FirstSearchNode` 与 `ReflectionNode`。

- `validate_input(input_data)`
  - 对字符串形式先尝试 `json.loads`，再检查必需字段；对 dict 直接检查键存在性。
  - 若校验失败，`run` 会抛出 `ValueError`。

- `run(input_data, **kwargs)`
  - 将输入（dict 或 JSON）规范化为字符串（`json.dumps(..., ensure_ascii=False)`）作为 LLM 的用户消息。
  - 调用 LLM：`response = self.llm_client.stream_invoke_to_string(SYSTEM_PROMPT_*, message)`。
  - 对 LLM 的输出调用 `process_output` 并返回处理后的 `{search_query, reasoning}`。
  - 全程记录日志（`logger.info`/`logger.exception`），在异常时抛出或返回默认查询（视实现路径）。

- `process_output(output)`
  - 清洗：调用 `remove_reasoning_from_output(output)`（移除模型显式的“思考”段落）和 `clean_json_tags`（去除常见的包装标签）。
  - 尝试 `json.loads(cleaned_output)`。若解析失败：
    1. 使用 `extract_clean_response(cleaned_output)`（更强的抽取/解析尝试）。
    2. 若结果仍包含 `error`，调用 `fix_incomplete_json(cleaned_output)` 进行修复并重试 `json.loads`。
    3. 若仍失败，退回到 `_get_default_search_query()` / `_get_default_reflection_query()`。
  - 验证解析结果包含 `search_query`；若缺失则使用默认查询。
  - 捕获所有异常并返回默认查询（`FirstSearchNode` 使用 `_get_default_search_query`，`ReflectionNode` 使用 `_get_default_reflection_query`）。

健壮性设计要点
- 容错性的 JSON 处理链：管线采用多层策略（清洗 → 直接解析 → 抽取 → 修复 → 降级默认）以最大化从模型输出中恢复结构化结果的概率。
- 日志可追溯性：节点在每个关键步骤记录清理后的输出和解析错误，有助于定位提示词或模型输出问题。
- 明确降级策略：在解析失败时使用明确的默认查询，保证后续搜索流程不会因缺少查询而中断。

示例调用
```py
from MediaEngine.nodes.search_node import FirstSearchNode, ReflectionNode
from MediaEngine.llms.base import LLMClient
from config import settings

llm = LLMClient(settings.MEDIA_ENGINE_API_KEY, settings.MEDIA_ENGINE_MODEL_NAME, settings.MEDIA_ENGINE_BASE_URL)
first_node = FirstSearchNode(llm)
reflection_node = ReflectionNode(llm)

paragraph = {"title": "舆情背景", "content": "关于武汉大学近期的舆情讨论..."}

# 生成首次搜索查询
result = first_node.run(paragraph)
print(result['search_query'], result.get('reasoning'))

# 反思阶段（需要 paragraph_latest_state）
paragraph_state = {
  "title": "舆情背景",
  "content": "关于武汉大学近期的舆情讨论...",
  "paragraph_latest_state": "已收集到的证据与摘要文本"
}
new_query = reflection_node.run(paragraph_state)
print(new_query['search_query'], new_query.get('reasoning'))
```

测试与调试建议
- 单元测试应覆盖：
  - 合法 JSON 返回（包含 `search_query` 与 `reasoning`）
  - 模型返回被包装/多行/带额外文本的 JSON（测试 `extract_clean_response` 的效果）
  - 模型返回非法 JSON 且 `fix_incomplete_json` 无法修复（节点应返回默认查询）
  - `validate_input` 的边界值（字符串、dict、缺失字段）
- 调试提示：替换 `llm_client` 为假的实现（返回预设字符串），直接调用 `process_output` 来模拟各种模型输出场景。

变更建议与注意事项
- prompt-first 改动：修改 `SYSTEM_PROMPT_FIRST_SEARCH` 或 `SYSTEM_PROMPT_REFLECTION` 会直接改变模型输出格式，请同时更新相关单元测试与清洗逻辑。
- 可注入解析策略：建议将 `extract_clean_response` 和 `fix_incomplete_json` 抽象成可替换的策略对象，便于在需要更强修复工具（例如调用专门的解析 LLM）时替换。
- 默认查询配置化：把默认查询文本抽取到配置文件或常量模块，便于产品化调整而不是修改逻辑代码。
- 日志敏感信息：避免将完整用户内容或模型输出直接写入长期可见日志（可记录摘要或哈希以便排查）。

注意
- 节点不应在模块导入时做 I/O 或启动线程；所有外部依赖都应通过构造器注入，保证可测试性。
- 如果决定更改默认查询或返回结构，请确保下游搜索/爬虫代码兼容 `search_query` 字段。

---

需要我为 `process_output` 编写一组示例单元测试（覆盖成功、包装 JSON、修复失败等场景）吗？
```