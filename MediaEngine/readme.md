# MediaEngine — 目录说明与运行指南

本文件为 `MediaEngine` 目录的架构与业务流程说明，基于代码阅读（`agent.py`、`nodes/*.py`、`tools/search.py`、`prompts/*.py`）整理而成，便于维护、集成与调试。

## 概要

- **目的**: 基于多模态搜索（网页、图片、视频、结构化数据），对用户查询进行深度迭代分析与报告生成。通过多轮搜索与反思循环，不断补充和深化对主题的理解，最终生成完整的研究报告。
- **主要功能**: 
  - 报告结构生成（分段落设计）
  - 多轮迭代搜索（初始搜索 + 反思搜索循环）
  - 动态总结与更新（逐步补充段落内容）
  - 多模态搜索工具集成（Bocha API / Anspire API）
  - 最终报告格式化与持久化

## 目录核心文件

### `agent.py` - 主编排器

[MediaEngine/agent.py](MediaEngine/agent.py#L1-L508)

主要类：
- **`DeepSearchAgent`**: 核心agent类，整合所有模块，实现完整的深度搜索流程。
- **`AnspireSearchAgent`**: 继承自 `DeepSearchAgent`，使用 Anspire 搜索引擎替代 Bocha。

**职责**:
- 初始化 LLM 客户端、搜索工具、处理节点和状态
- 协调报告结构生成、段落处理、反思循环和报告最终化
- 管理进度、保存/加载状态

### `nodes/` - 处理节点

| 文件 | 类 | 职责 |
|------|----|----|
| `base_node.py` | `BaseNode` / `StateMutationNode` | 定义所有节点的基础接口与状态修改能力 |
| `report_structure_node.py` | `ReportStructureNode` | 从查询生成报告的段落结构与大纲 |
| `search_node.py` | `FirstSearchNode` / `ReflectionNode` | 生成初始和反思搜索查询、选择合适的搜索工具 |
| `summary_node.py` | `FirstSummaryNode` / `ReflectionSummaryNode` | 根据搜索结果生成和更新段落总结 |
| `formatting_node.py` | `ReportFormattingNode` | 将所有段落总结整合成最终markdown报告 |

### `tools/search.py` - 多模态搜索工具

[MediaEngine/tools/search.py](MediaEngine/tools/search.py#L1-L519)

**核心类**:
- **`BochaMultimodalSearch`**: 封装 Bocha API，提供5种搜索工具
  - `comprehensive_search`: 全面搜索（网页 + 图片 + AI总结 + 可选模态卡）
  - `web_search_only`: 纯网页搜索
  - `search_for_structured_data`: 结构化数据查询（天气、股票等）
  - `search_last_24_hours`: 24小时内最新信息
  - `search_last_week`: 周内主要报道
  
- **`AnspireAISearch`**: 替代性搜索引擎集成

**数据结构**:
- `BochaResponse`: 封装完整搜索结果（网页、图片、AI总结、模态卡）
- `ModalCardResult`: 特殊的结构化数据返回（如天气、股票价格）
- `WebpageResult` / `ImageResult`: 单个结果对象

### `prompts/prompts.py` - 提示词与JSON Schema

[MediaEngine/prompts/prompts.py](MediaEngine/prompts/prompts.py#L1-L451)

包含每个处理阶段的：
- **系统提示词** (SYSTEM_PROMPT_*): LLM的角色与指令
- **输入/输出 JSON Schema**: 数据验证与强制结构化输出
- **示例提示** (EXAMPLE_*): Few-shot学习样本

### `state/state.py` - 状态管理

定义 `State` 类，维护：
- 报告标题与查询
- 段落列表（每个段落包含搜索历史、总结、反思计数）
- 最终报告内容
- 进度跟踪与完成状态

### `llms/` - LLM 客户端

[MediaEngine/llms/base.py](MediaEngine/llms/base.py) 定义 `LLMClient`，提供：
- `invoke`: 同步调用
- `stream_invoke_to_string`: 流式调用并聚合为字符串
- 统一的错误处理与重试机制

### `utils/` - 工具函数

- **`config.py`**: 配置管理（从环境或文件读取）
- **`text_processing.py`**: 文本清理、JSON解析修复、去重等

## 主要概念与设计要点

### 1. 报告结构生成

- **输入**: 用户查询
- **处理**: LLM 生成多个段落的标题和初始内容描述
- **输出**: `Paragraph` 对象列表，每个包含 `title` 和 `content`

### 2. 迭代搜索循环（关键特性）

对每个段落执行：

```
循环 i = 1 到 MAX_REFLECTIONS:
  1. 初始搜索 (i=0) 或 反思搜索 (i>0)
  2. 执行网络搜索
  3. 生成或更新段落总结
```

- **初始搜索**: 基于段落标题与内容生成初始查询
- **反思搜索**: 基于已有总结提出新角度，进行深化搜索
- **搜索工具选择**: 由 LLM 决策（可选 5 种工具中的任一）

### 3. 状态修改节点模式

- 某些节点实现 `StateMutationNode` 接口
- 提供 `mutate_state(input_data, state) -> State` 方法
- 对状态的修改是**增量的**，保留历史（不覆盖）

### 4. 多模态搜索集成

Bocha API 特色：
- 可返回网页、图片、AI总结、**模态卡**（结构化数据）
- 模态卡适用场景: 天气、股票、汇率、医疗百科等
- Agent 可根据查询意图选择合适的搜索工具

### 5. 线程与并发

- 单线程串行处理（不使用并发）
- 所有 I/O 操作通过 LLMClient 统一管理
- 搜索调用包含 retry 装饰器以处理暂时性失败

### 6. 错误处理与降级

- JSON 解析失败时调用 `fix_incomplete_json` 尝试修复
- LLM 输出格式不符时尝试正则提取或备用方案
- Anspire 搜索不可用时降级到 Bocha

## 业务流程（步骤化）

### Step 1: 初始化

```python
agent = DeepSearchAgent(config)
# 初始化: LLM客户端、搜索工具、节点对象、状态
```

### Step 2: 生成报告结构

```
输入: query = "华为芯片技术发展现状"
  ↓
ReportStructureNode.run(query)
  ↓
LLM 生成段落列表，例如:
  - "芯片架构与设计创新"
  - "工艺制程与代工合作"
  - "操作系统与生态构建"
  - "行业挑战与未来展望"
  ↓
更新 state.paragraphs
```

### Step 3: 处理每个段落（迭代搜索）

```
FOR 每个段落 i:
  
  ===== 初始搜索 (i=0) =====
  段落信息 → FirstSearchNode → 生成 search_query_0
              + 选择搜索工具
  
  search_query_0 → BochaMultimodalSearch.comprehensive_search()
                 → 获取网页、图片、AI总结
  
  segment_info + search_results_0 → FirstSummaryNode
                                  → 生成 paragraph_summary_0
                                  → 更新 state.paragraphs[i].research.latest_summary
  
  ===== 反思循环 (j=1 to MAX_REFLECTIONS) =====
  FOR j=1 to MAX_REFLECTIONS:
    
    paragraph + paragraph_summary_{j-1} → ReflectionNode
                                        → 生成 search_query_j
                                        → 选择搜索工具
    
    search_query_j → BochaMultimodalSearch.<选中工具>()
                   → 获取搜索结果
    
    paragraph + paragraph_summary_{j-1} + search_results_j 
              → ReflectionSummaryNode
              → 生成 paragraph_summary_j
              → 更新 state.paragraphs[i].research.latest_summary
              → 更新 state.paragraphs[i].research.reflection_count++
```

### Step 4: 最终报告生成

```
所有段落的 paragraph_latest_state 
  ↓
ReportFormattingNode.run(report_data)
  ↓
LLM 整合所有段落成 Markdown 报告
  ↓
state.final_report = report_content
```

### Step 5: 保存与返回

```
最终报告写入文件: 
  output_dir/deep_search_report_{query}_{timestamp}.md

中间状态（可选）:
  output_dir/state_{query}_{timestamp}.json
```

### ASCII 流程图

```
查询 (query)
  ↓
[ReportStructureNode] → 生成报告大纲 (段落列表)
  ↓
FOR 每个段落 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ├─ [FirstSearchNode] → 生成初始搜索查询
  ├─ [BochaMultimodalSearch] → 执行搜索
  ├─ [FirstSummaryNode] → 生成初始总结
  │
  └─ 反思循环 (i = 1 to MAX_REFLECTIONS)
     ├─ [ReflectionNode] → 生成反思查询
     ├─ [BochaMultimodalSearch] → 执行反思搜索
     └─ [ReflectionSummaryNode] → 更新总结
  
[ReportFormattingNode] → 整合所有段落
  ↓
最终报告 (Markdown)
  ↓
保存文件 + 返回内容
```

## 配置项

配置来源: [config.py](config.py) 或 [MediaEngine/utils/config.py](MediaEngine/utils/config.py)

关键字段:

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `MEDIA_ENGINE_API_KEY` | Media Agent LLM API 密钥 | None |
| `MEDIA_ENGINE_MODEL_NAME` | LLM 模型标识 | None |
| `MEDIA_ENGINE_BASE_URL` | LLM Base URL | None |
| `BOCHA_API_KEY` | Bocha 搜索 API 密钥 | None |
| `BOCHA_WEB_SEARCH_API_KEY` | Bocha 备用 API 密钥 | None |
| `ANSPIRE_API_KEY` | Anspire 搜索 API 密钥 | None |
| `SEARCH_TOOL_TYPE` | 搜索引擎选择："BochaAPI" 或 "AnspireAPI" | "BochaAPI" |
| `MAX_REFLECTIONS` | 每个段落的最大反思轮数 | 2 |
| `OUTPUT_DIR` | 报告输出目录 | "media_engine_streamlit_reports" |
| `SAVE_INTERMEDIATE_STATES` | 是否保存中间状态 JSON | True |
| `SEARCH_CONTENT_MAX_LENGTH` | 搜索结果摘要的最大长度 | 1500 |

示例环境变量：

```bash
MEDIA_ENGINE_API_KEY=sk-xxxxx
MEDIA_ENGINE_MODEL_NAME=gpt-4o  # 或其他模型
MEDIA_ENGINE_BASE_URL=https://api.openai.com/v1
BOCHA_API_KEY=bocha_key_xxxxx
MAX_REFLECTIONS=3
OUTPUT_DIR=/path/to/reports
```

## 使用示例

### 基本使用

```python
from MediaEngine import DeepSearchAgent

# 创建agent
agent = DeepSearchAgent()

# 执行深度研究
query = "华为芯片技术发展现状"
final_report = agent.research(query, save_report=True)

# 查看进度
progress = agent.get_progress_summary()
print(progress)
```

### 使用 Anspire 搜索引擎

```python
from MediaEngine.agent import AnspireSearchAgent

agent = AnspireSearchAgent()
report = agent.research("某个查询")
```

### 状态保存与加载

```python
# 保存中间状态
agent.save_state("checkpoint.json")

# 加载并继续处理
agent.load_state("checkpoint.json")
final_report = agent._generate_final_report()
```

### 自定义搜索工具选择

在 `nodes/search_node.py` 中可见 LLM 自动选择搜索工具的逻辑，支持以下工具：

- `"comprehensive_search"`: 全面搜索（默认）
- `"web_search_only"`: 纯网页搜索（快速）
- `"search_for_structured_data"`: 结构化数据（天气、股票等）
- `"search_last_24_hours"`: 实时新闻
- `"search_last_week"`: 周内报道

## 节点深入理解

### FirstSearchNode vs ReflectionNode

| 特性 | FirstSearchNode | ReflectionNode |
|------|-----------------|-----------------|
| **输入** | {title, content} | {title, content, **paragraph_latest_state**} |
| **职责** | 基于段落描述生成初始搜索 | 基于已有总结提出新角度 |
| **调用时机** | 每个段落一次（最开始） | 反思循环中（最多MAX_REFLECTIONS次） |
| **搜索策略** | 广泛覆盖 | 深度探索已知信息的盲点 |

### FirstSummaryNode vs ReflectionSummaryNode

| 特性 | FirstSummaryNode | ReflectionSummaryNode |
|------|-----------------|----------------------|
| **输入** | {title, content, search_query, search_results} | {..., **paragraph_latest_state**} |
| **职责** | 从搜索结果生成初始总结 | 将新搜索结果与旧总结融合 |
| **总结内容** | 新的发现与信息 | 更新、补充、对比、深化 |
| **调用时机** | 初始搜索后 | 反思搜索后（每个反思一次） |

## 常见问题与故障排查

### 1. 搜索工具不可用

**症状**: "搜索失败" 或 "API返回格式异常"

**检查**:
- 验证 `BOCHA_API_KEY` 或 `ANSPIRE_API_KEY` 是否正确
- 检查网络连接
- 查看日志中的 HTTP 状态码和响应

**解决**:
- 更换搜索引擎（从 Bocha 改用 Anspire）
- 增加重试次数（修改 `SEARCH_API_RETRY_CONFIG`）

### 2. LLM 输出格式错误

**症状**: "JSON 解析失败" 或 "输出不符合 Schema"

**检查**:
- 查看日志中的 "清理后的输出" 
- 验证 LLM 模型是否支持结构化输出
- 检查 prompt 中的 JSON Schema 是否正确

**解决**:
- 尝试更换 LLM 模型（例如 gpt-4o）
- 在 `fix_incomplete_json` 中增加修复规则
- 调整 system prompt 中的指令

### 3. 报告内容不完整

**症状**: 某些段落内容为空或重复

**检查**:
- 增加 `MAX_REFLECTIONS` 的值
- 检查搜索结果质量（日志中的结果数量）
- 验证 LLM 是否将信息正确融合

**解决**:
- 手动调整 prompt 中的融合指令
- 选择不同的搜索工具
- 验证网络搜索的可用性

### 4. 性能与超时

**症状**: 运行时间过长或超时

**优化**:
- 减少 `MAX_REFLECTIONS` 的值
- 使用 `web_search_only` 工具替代 `comprehensive_search`
- 减少 `SEARCH_CONTENT_MAX_LENGTH` 以加快 LLM 处理
- 增加 LLM 并发请求数（修改客户端配置）

## 与其他引擎的关系

- **与 InsightEngine 的区别**:
  - MediaEngine 侧重于**多模态搜索**（网页、图片、视频、结构化数据）
  - InsightEngine 侧重于**私有数据库查询**与情感分析
  
- **与 QueryEngine 的区别**:
  - MediaEngine 强调**多轮反思与迭代**
  - QueryEngine 可能更侧重于**精准查询**

- **与 ForumEngine 的关系**:
  - MediaEngine 的 `SummaryNode` 输出被 ForumEngine 监听并汇总
  - ForumEngine 可基于 MediaEngine 的输出触发主持人发言

## 扩展建议 / 下一步

1. **异步处理**: 将段落处理改为并发，加快整体速度
2. **缓存机制**: 对相同查询缓存搜索结果以避免重复调用
3. **反馈循环**: 从最终报告质量反馈调整搜索策略
4. **可视化**: 添加进度条、段落处理时间分析等
5. **A/B 测试**: 对比不同 LLM 和搜索工具的组合效果

## 文件实现参考

- `MediaEngine/agent.py` — 主编排与流程控制
- `MediaEngine/nodes/*.py` — 各个处理节点
- `MediaEngine/tools/search.py` — 多模态搜索工具集
- `MediaEngine/prompts/prompts.py` — 提示词与 Schema 定义
- `MediaEngine/state/state.py` — 状态管理

---

如果你希望我增加可视化流程图、提取更多配置为可配置变量、或详细讲解某个特定节点的实现，我可以继续完善本文档。
