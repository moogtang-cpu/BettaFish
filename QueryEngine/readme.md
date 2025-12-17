# QueryEngine — 目录说明与运行指南

本文件为 `QueryEngine` 目录的架构与业务流程说明，基于代码阅读（`agent.py`、`nodes/*.py`、`tools/search.py`、`prompts/*.py`）整理而成，便于维护、集成与调试。

## 概要

- **目的**: 基于**新闻舆情搜索**，对用户查询进行深度迭代分析与报告生成。通过多轮新闻搜索与反思循环，不断补充和深化对主题的理解，最终生成完整的新闻分析报告。
- **核心特色**: 
  - 6种专用新闻搜索工具（快速搜索、深度分析、时间范围搜索、图片搜索等）
  - 多轮迭代搜索（初始搜索 + 反思搜索循环）
  - 每条搜索结果包含**发布日期**，便于时间线分析
  - 支持**按日期范围搜索**历史新闻
  - 最终生成结构化的 Markdown 报告

## 目录核心文件

### `agent.py` - 主编排器

[QueryEngine/agent.py](QueryEngine/agent.py#L1-L474)

主要类：
- **`DeepSearchAgent`**: 核心agent类，整合所有模块，实现完整的深度新闻搜索流程。

**职责**:
- 初始化 LLM 客户端、新闻搜索工具、处理节点和状态
- 协调报告结构生成、段落处理、反思循环和报告最终化
- 管理进度、保存/加载状态
- 支持6种搜索工具的自动选择与参数验证（特别是日期验证）

### `nodes/` - 处理节点

| 文件 | 类 | 职责 |
|------|----|----|
| `base_node.py` | `BaseNode` / `StateMutationNode` | 定义所有节点的基础接口与状态修改能力 |
| `report_structure_node.py` | `ReportStructureNode` | 从查询生成报告的段落结构与大纲 |
| `search_node.py` | `FirstSearchNode` / `ReflectionNode` | 生成初始和反思搜索查询、选择合适的新闻搜索工具 |
| `summary_node.py` | `FirstSummaryNode` / `ReflectionSummaryNode` | 根据搜索结果生成和更新段落总结 |
| `formatting_node.py` | `ReportFormattingNode` | 将所有段落总结整合成最终markdown报告 |

### `tools/search.py` - 新闻舆情搜索工具

[QueryEngine/tools/search.py](QueryEngine/tools/search.py#L1-L251)

**核心类**:
- **`TavilyNewsAgency`**: 封装 Tavily API，提供6种新闻搜索工具

**支持的搜索工具**:

| 工具名 | 方法 | 说明 | 返回结果数 |
|--------|------|------|-----------|
| `basic_search_news` | 标准、快速新闻搜索 | 通用、快速的新闻搜索，最常用 | 最多 7 条（可配置） |
| `deep_search_news` | 深度新闻分析 | 对主题进行最全面、最深入的搜索，返回 AI 生成摘要 | 最多 20 条 |
| `search_news_last_24_hours` | 24小时内最新新闻 | 追踪突发事件或最新进展 | 最多 10 条 |
| `search_news_last_week` | 本周新闻 | 周度舆情总结或回顾 | 最多 10 条 |
| `search_images_for_news` | 新闻图片搜索 | 查找与新闻主题相关的图片 | 最多 5 张 |
| `search_news_by_date` | 按日期范围搜索 | 在指定历史时间段内搜索新闻，需要日期参数 | 最多 15 条 |

**数据结构**:
- `TavilyResponse`: 封装完整搜索结果（查询、AI摘要、网页结果、图片结果）
- `SearchResult`: 单条新闻结果（包含 `title`、`url`、`content`、`score`、`published_date`）
- `ImageResult`: 单张图片结果

### `prompts/prompts.py` - 提示词与JSON Schema

[QueryEngine/prompts/prompts.py](QueryEngine/prompts/prompts.py#L1-L447)

包含每个处理阶段的：
- **系统提示词** (SYSTEM_PROMPT_*): LLM的角色与指令
- **输入/输出 JSON Schema**: 数据验证与强制结构化输出
  - 包含 `start_date` 和 `end_date` 字段（用于 `search_news_by_date` 工具）
- **示例提示** (EXAMPLE_*): Few-shot学习样本

### `state/state.py` - 状态管理

定义 `State` 类，维护：
- 报告标题与查询
- 段落列表（每个段落包含搜索历史、总结、反思计数）
- 最终报告内容
- 进度跟踪与完成状态

### `llms/` - LLM 客户端

[QueryEngine/llms/base.py](QueryEngine/llms/base.py) 定义 `LLMClient`，提供：
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
  2. 执行新闻搜索（选择6种工具之一）
  3. 生成或更新段落总结
```

- **初始搜索**: 基于段落标题与内容生成初始查询
- **反思搜索**: 基于已有总结提出新角度，进行深化搜索
- **搜索工具选择**: 由 LLM 决策（可选 6 种工具中的任一）
- **日期参数处理**: 
  - 若选择 `search_news_by_date` 工具，LLM 需生成 `start_date` 和 `end_date`
  - 格式验证：必须为 `YYYY-MM-DD`
  - 验证失败时自动降级到 `basic_search_news`

### 3. 日期处理与时间线支持

- **每条搜索结果**包含 `published_date` 字段，支持按发布时间排序/筛选
- **日期范围搜索**: 
  - 支持在历史数据中进行精确搜索
  - 典型场景：追踪某事件的时间发展、对比不同时期的新闻
  - LLM 自动生成合理的日期范围或改用快速搜索

### 4. 状态修改节点模式

- 某些节点实现 `StateMutationNode` 接口
- 提供 `mutate_state(input_data, state) -> State` 方法
- 对状态的修改是**增量的**，保留历史（不覆盖）

### 5. 新闻搜索工具集成

Tavily API 特色：
- 6种专用工具满足不同搜索场景
- `deep_search_news` 返回 AI 生成的高级摘要
- 支持时间筛选（24小时、1周、自定义范围）
- 支持图片搜索
- 每条结果包含可信度评分与发布日期

### 6. 线程与并发

- 单线程串行处理（不使用并发）
- 所有 I/O 操作通过 LLMClient 统一管理
- 搜索调用包含 retry 装饰器以处理暂时性失败

### 7. 错误处理与降级

- 日期格式无效时自动改用 `basic_search_news`
- JSON 解析失败时调用 `fix_incomplete_json` 尝试修复
- LLM 输出格式不符时尝试正则提取或备用方案
- 搜索结果不足时继续进行反思循环

## 业务流程（步骤化）

### Step 1: 初始化

```python
agent = DeepSearchAgent(config)
# 初始化: LLM客户端、Tavily搜索工具、节点对象、状态
```

### Step 2: 生成报告结构

```
输入: query = "2025年AI芯片市场动向"
  ↓
ReportStructureNode.run(query)
  ↓
LLM 生成段落列表，例如:
  - "英伟达最新芯片发布"
  - "AMD与英特尔的竞争态势"
  - "国内芯片厂商的进展"
  - "芯片供应链风险分析"
  ↓
更新 state.paragraphs
```

### Step 3: 处理每个段落（迭代搜索）

```
FOR 每个段落 i:
  
  ===== 初始搜索 (i=0) =====
  段落信息 → FirstSearchNode → 生成 search_query_0
              + 选择搜索工具（6选1）
              + 如选中 search_news_by_date，生成 start_date / end_date
  
  验证日期格式（如适用）↓
  
  search_query_0 + 工具参数 → TavilyNewsAgency.<选中工具>()
                           → 获取新闻结果（含发布日期）
  
  segment_info + search_results_0 → FirstSummaryNode
                                  → 生成 paragraph_summary_0
                                  → 更新 state.paragraphs[i].research.latest_summary
  
  ===== 反思循环 (j=1 to MAX_REFLECTIONS) =====
  FOR j=1 to MAX_REFLECTIONS:
    
    paragraph + paragraph_summary_{j-1} → ReflectionNode
                                        → 生成 search_query_j
                                        → 选择搜索工具（6选1）
                                        → 如需要，生成日期范围
    
    验证日期格式（如适用）↓
    
    search_query_j + 工具参数 → TavilyNewsAgency.<选中工具>()
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
  ├─ [FirstSearchNode] → 生成初始搜索查询 + 选择工具
  ├─ 验证日期格式（如适用）
  ├─ [TavilyNewsAgency] → 执行新闻搜索
  ├─ [FirstSummaryNode] → 生成初始总结
  │
  └─ 反思循环 (i = 1 to MAX_REFLECTIONS)
     ├─ [ReflectionNode] → 生成反思查询 + 选择工具
     ├─ 验证日期格式（如适用）
     ├─ [TavilyNewsAgency] → 执行反思搜索
     └─ [ReflectionSummaryNode] → 更新总结
  
[ReportFormattingNode] → 整合所有段落
  ↓
最终报告 (Markdown)
  ↓
保存文件 + 返回内容
```

## 配置项

配置来源: [config.py](config.py) 或 [QueryEngine/utils/config.py](QueryEngine/utils/config.py)

关键字段:

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `QUERY_ENGINE_API_KEY` | Query Agent LLM API 密钥 | None |
| `QUERY_ENGINE_MODEL_NAME` | LLM 模型标识 | None |
| `QUERY_ENGINE_BASE_URL` | LLM Base URL | None |
| `TAVILY_API_KEY` | Tavily 新闻搜索 API 密钥 | None |
| `MAX_REFLECTIONS` | 每个段落的最大反思轮数 | 2 |
| `OUTPUT_DIR` | 报告输出目录 | "query_engine_streamlit_reports" |
| `SAVE_INTERMEDIATE_STATES` | 是否保存中间状态 JSON | True |
| `SEARCH_CONTENT_MAX_LENGTH` | 搜索结果摘要的最大长度 | 1500 |

示例环境变量：

```bash
QUERY_ENGINE_API_KEY=sk-xxxxx
QUERY_ENGINE_MODEL_NAME=gpt-4o
QUERY_ENGINE_BASE_URL=https://api.openai.com/v1
TAVILY_API_KEY=tavily_key_xxxxx
MAX_REFLECTIONS=3
OUTPUT_DIR=/path/to/reports
```

## 使用示例

### 基本使用

```python
from QueryEngine import DeepSearchAgent

# 创建agent
agent = DeepSearchAgent()

# 执行深度新闻研究
query = "2025年AI芯片市场动向"
final_report = agent.research(query, save_report=True)

# 查看进度
progress = agent.get_progress_summary()
print(progress)
```

### 状态保存与加载

```python
# 保存中间状态
agent.save_state("checkpoint.json")

# 加载并继续处理
agent.load_state("checkpoint.json")
final_report = agent._generate_final_report()
```

### 搜索工具选择逻辑

LLM 会根据查询意图自动选择合适的搜索工具。agent 支持以下工具：

| 使用场景 | 推荐工具 | 原因 |
|--------|---------|------|
| 通用新闻搜索 | `basic_search_news` | 快速、结果多样化 |
| 全面了解背景 | `deep_search_news` | 返回 AI 摘要，信息聚合 |
| 追踪突发事件 | `search_news_last_24_hours` | 获取最新进展 |
| 周度舆情总结 | `search_news_last_week` | 覆盖过去7天 |
| 配图需求 | `search_images_for_news` | 返回相关图片链接 |
| 历史事件分析 | `search_news_by_date` | 在指定时间范围内搜索 |

### 日期验证与参数处理

```python
# 当 LLM 选择 search_news_by_date 时，agent 会自动验证日期
# 验证失败示例：
#   - "2025/01/01" → 无效，改用 basic_search_news
#   - "2025-13-01" → 无效月份，改用 basic_search_news
#   - "2025-01-01" → 有效，执行搜索

# 日志示例：
# 日期格式错误（应为YYYY-MM-DD），改用基础搜索
# 提供的日期: start_date=2025/01/01, end_date=2025/02/01
```

## 节点深入理解

### FirstSearchNode vs ReflectionNode

| 特性 | FirstSearchNode | ReflectionNode |
|------|-----------------|-----------------|
| **输入** | {title, content} | {title, content, **paragraph_latest_state**} |
| **职责** | 基于段落描述生成初始搜索 | 基于已有总结提出新角度 |
| **调用时机** | 每个段落一次（最开始） | 反思循环中（最多MAX_REFLECTIONS次） |
| **搜索策略** | 广泛覆盖 | 深度探索已知信息的盲点 |
| **工具范围** | 6种工具任选 | 6种工具任选（含日期范围搜索） |

### FirstSummaryNode vs ReflectionSummaryNode

| 特性 | FirstSummaryNode | ReflectionSummaryNode |
|------|-----------------|----------------------|
| **输入** | {title, content, search_query, search_results} | {..., **paragraph_latest_state**} |
| **职责** | 从搜索结果生成初始总结 | 将新搜索结果与旧总结融合 |
| **总结内容** | 新的发现与信息 | 更新、补充、对比、深化 |
| **调用时机** | 初始搜索后 | 反思搜索后（每个反思一次） |

### 搜索结果结构

每条新闻结果包含：
- `title`: 新闻标题
- `url`: 新闻链接
- `content`: 新闻摘要或正文
- `score`: 相关性评分（0-1）
- `published_date`: 发布日期（YYYY-MM-DD 格式）
- `raw_content`: 原始内容

## 常见问题与故障排查

### 1. 搜索工具选择不当

**症状**: LLM 选择了不合适的搜索工具或日期范围

**检查**:
- 查看日志中的"选择的工具"与"反思推理"字段
- 验证 prompt 中的工具说明是否清晰
- 检查 LLM 模型是否支持结构化输出

**解决**:
- 在 system prompt 中增加工具选择的示例与场景说明
- 尝试更换 LLM 模型（例如 gpt-4o）
- 手动调整 `MAX_REFLECTIONS` 以改变搜索深度

### 2. 日期参数验证失败

**症状**: "日期格式错误（应为YYYY-MM-DD），改用基础搜索"

**原因**:
- LLM 生成了不符合格式的日期字符串
- 日期本身无效（如13月、32日）

**解决**:
- 在 prompt 中提供日期格式示例
- 增加 LLM 输出的日期验证函数
- 允许 agent 降级到快速搜索（已实现）

### 3. 搜索结果不完整

**症状**: 某些段落的搜索结果数量少或为空

**检查**:
- 查看搜索查询是否过于具体或生僻
- 增加 `MAX_REFLECTIONS` 的值以进行更多深化搜索
- 验证 Tavily API 是否可用

**解决**:
- 调整 prompt 中的搜索查询生成逻辑
- 选择更通用的搜索工具（`basic_search_news` 或 `deep_search_news`）
- 检查网络连接与 API 配额

### 4. 性能与超时

**症状**: 运行时间过长或超时

**优化**:
- 减少 `MAX_REFLECTIONS` 的值（默认2，可改为1）
- 使用 `basic_search_news` 替代 `deep_search_news`
- 减少 `SEARCH_CONTENT_MAX_LENGTH` 以加快 LLM 处理
- 验证是否有网络延迟

## 与其他引擎的关系

- **与 InsightEngine 的区别**:
  - QueryEngine 侧重于**新闻舆情**搜索与分析
  - InsightEngine 侧重于**私有数据库查询**与情感分析
  - QueryEngine 支持时间范围搜索，InsightEngine 不需要
  
- **与 MediaEngine 的区别**:
  - QueryEngine 使用 **Tavily（新闻搜索）**
  - MediaEngine 使用 **Bocha（多模态搜索）**
  - QueryEngine 强调**新闻时间线**与**历史数据追踪**
  - MediaEngine 强调**多模态内容**（图片、视频等）

- **与 ForumEngine 的关系**:
  - QueryEngine 的 `SummaryNode` 输出被 ForumEngine 监听并汇总
  - ForumEngine 可基于 QueryEngine 的输出触发主持人发言

## 扩展建议 / 下一步

1. **事件时间线生成**: 根据 `published_date` 自动生成事件发展的时间线可视化
2. **情感分析集成**: 将每条新闻进行情感评分，支持舆情倾向分析
3. **新闻去重与聚合**: 对重复报道进行去重，聚合不同媒体的观点
4. **多语言支持**: 扩展搜索到国际新闻（当前可能仅限中文/英文）
5. **缓存机制**: 对相同查询缓存搜索结果以避免重复调用
6. **实时监控**: 支持持续监控新闻源，定期更新报告
7. **可视化导出**: 生成 HTML/PDF 报告，包含图表与可视化元素

## 文件实现参考

- `QueryEngine/agent.py` — 主编排与流程控制
- `QueryEngine/nodes/*.py` — 各个处理节点
- `QueryEngine/tools/search.py` — Tavily 新闻搜索工具集（6种工具）
- `QueryEngine/prompts/prompts.py` — 提示词与 Schema 定义
- `QueryEngine/state/state.py` — 状态管理

---

如果你希望我增加时间线可视化、提取更多配置为可配置变量、或详细讲解日期参数处理逻辑，我可以继续完善本文档。
