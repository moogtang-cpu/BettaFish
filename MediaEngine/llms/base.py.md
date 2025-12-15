```markdown
# MediaEngine/llms/base.py 业务逻辑说明

该文件实现了 MediaEngine 使用的一个轻量、OpenAI 兼容的 LLM 客户端封装 `LLMClient`，负责同步与流式调用、重试、超时管理和响应拼接（流式安全解码）。本说明以开发者/AI 代码助手为对象，说明它的职责、关键行为、常见调用方式与注意事项。

核心职责
- 提供一个统一的、OpenAI-style 的聊天接口 (`invoke`, `stream_invoke`, `stream_invoke_to_string`)。
- 读取环境变量以决定请求超时时间：`LLM_REQUEST_TIMEOUT` 或 `MEDIA_ENGINE_REQUEST_TIMEOUT`（优先级同代码）。
- 使用仓库的 `utils/retry_helper.py` 中提供的 `with_retry` 装饰器（如存在）为关键调用添加重试策略。
- 在流式模式下，逐块产出响应，并提供 `stream_invoke_to_string` 以字节方式拼接所有块，避免 UTF-8 多字节截断问题。

关键类与方法概览
- `LLMClient(api_key: str, model_name: str, base_url: Optional[str]=None)`
  - 必需参数：`api_key`（必须）、`model_name`（必须）。
  - 读取超时配置并实例化 `openai.OpenAI` 客户端（或兼容的 OpenAI 客户端）。

- `invoke(system_prompt: str, user_prompt: str, **kwargs) -> str`
  - 同步调用：将 `system` + `user` 消息列表发送到 `client.chat.completions.create`。
  - 自动在用户提示前追加当前时间前缀（格式 `今天的实际时间是YYYY年MM月DD日HH时MM分`），使模型对当前时间敏感。
  - 支持的额外参数：`temperature, top_p, presence_penalty, frequency_penalty, stream`。
  - 使用 `with_retry(LLM_RETRY_CONFIG)` 包装（如果 `retry_helper` 存在），并返回经 `validate_response` 清洗后的字符串。

- `stream_invoke(system_prompt: str, user_prompt: str, **kwargs) -> Generator[str, None, None]`
  - 流式调用：强制 `stream=True` 并将客户端返回的迭代流逐块处理。
  - 从每个 chunk 中取 `chunk.choices[0].delta.content` 并 `yield` 出（与 OpenAI 流式 API 的 delta 模式兼容）。
  - 对异常做日志记录并将异常向上抛出，调用端负责捕获。

- `stream_invoke_to_string(system_prompt: str, user_prompt: str, **kwargs) -> str`
  - 以字节为单位收集 `stream_invoke` 的所有块，最后将字节拼接后一次性用 UTF-8 解码（errors='replace'），避免多字节字符被截断导致的乱码。
  - 使用 `with_retry` 包裹以提高鲁棒性。

- `validate_response(response: Optional[str]) -> str`
  - 简单清理：如果 `None` 则返回空字符串，否则 `strip()` 并返回。

- `get_model_info() -> Dict[str, Any]`
  - 返回当前客户端的元信息（provider、model、api_base），供监控或 debug 使用。

实现细节与注意事项
- 重试：该模块依赖 `utils/retry_helper.py` 导出的 `with_retry` 装饰器与 `LLM_RETRY_CONFIG`。若 `retry_helper` 不存在，模块会回退为无重试版本（见文件顶部的安全导入）：因此在引入修改时注意不要假定 `with_retry` 一定具有特定行为。
- 超时来源：优先读取 `LLM_REQUEST_TIMEOUT`，其次 `MEDIA_ENGINE_REQUEST_TIMEOUT`，若不可解析则使用默认 `1800` 秒。调用 API 时可通过 `timeout` 参数覆盖。
- 流式语义：`stream_invoke` 期望后端返回与 OpenAI 类似的流式迭代对象，每个 chunk 包含 `choices[0].delta.content`。若后端返回不同结构（例如直接返回 text 块），需要适配解析逻辑。
- 字节拼接：`stream_invoke_to_string` 使用 `chunk.encode('utf-8')` 收藏字节片段并最终 `b''.join(...).decode('utf-8', errors='replace')`，这保证了跨块多字节字符正确拼接。
- 日志：模块使用 `loguru.logger` 记录异常与错误（例如流式失败会记录 `流式请求失败`），遵循项目风格，新增日志时请使用 `logger` 并记录尽量多的上下文信息以便排查。

典型调用示例

```py
from MediaEngine.llms.base import LLMClient
from config import settings

client = LLMClient(
    api_key=settings.MEDIA_ENGINE_API_KEY,
    model_name=settings.MEDIA_ENGINE_MODEL_NAME,
    base_url=settings.MEDIA_ENGINE_BASE_URL,
)

# 同步调用
resp = client.invoke(system_prompt='You are an assistant.', user_prompt='Summarize the text', temperature=0.2)

# 流式调用（逐段处理）
for chunk in client.stream_invoke('system prompt', 'user prompt'):
    process_chunk(chunk)

# 流式调用并收集完整字符串
full = client.stream_invoke_to_string('system prompt', 'user prompt')

# 获取模型信息
meta = client.get_model_info()
```

变更建议（对 Copilot / PR 的约束说明）
- 若需要支持额外的模型参数或供应商特性（例如 `max_tokens`、`stop`），请在 `allowed_keys` 中添加并小心兼容性。
- 若要支持非 OpenAI 兼容的后端（不同流式格式），请把解析逻辑封装成可替换的适配器（strategy），并保持当前的 `stream_invoke` 行为不变以避免调用代码侵入性更改。
- 增强监控：若添加请求/响应计数或延迟监控，应使用 `get_model_info()` 返回的元信息，并在 `invoke`/`stream_invoke_to_string` 等关键路径记录微观指标。

总结
---
`MediaEngine/llms/base.py` 是 MediaEngine 与外部 LLM 服务之间的桥梁。它保持轻量、面向 OpenAI 兼容接口、并对流式/同步调用、超时与重试、以及多字节安全拼接做了实际的工程处理。对该文件的任何修改都应优先考虑向后兼容性（尤其是流式数据结构与 `with_retry` 行为）。

```
