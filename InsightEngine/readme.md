# InsightEngine - 深度舆情分析引擎

## 整体架构

InsightEngine 是一个**深度舆情分析引擎**，采用模块化的流程化设计：

```
输入查询 → 报告规划 → 迭代搜索 → 数据总结 → 格式化输出
```

---

## 核心模块说明

### 1. Agent (agent.py)
- 主控制类 `DeepSearchAgent`
- 协调所有子模块的执行
- 管理状态、配置、LLM 客户端

### 2. Nodes (节点层) - 处理流程的各个阶段

| 节点 | 职责 | 输入 | 输出 |
|------|------|------|------|
| `ReportStructureNode` | 规划报告结构 | 查询主题 | 5个段落 + 分析需求 |
| `FirstSearchNode` | 首次搜索 | 段落标题+内容需求 | 搜索查询+选择的工具 |
| `FirstSummaryNode` | 首次总结 | 搜索结果 | 段落初稿 |
| `ReflectionNode` | 反思优化 | 现有段落内容 | 改进的搜索查询 |
| `ReflectionSummaryNode` | 反思总结 | 新的搜索结果 | 扩充后的段落 |
| `ReportFormattingNode` | 最终格式化 | 所有段落 | Markdown 报告 |

### 3. State (state/state.py)
- 维护报告的多轮迭代状态
- 追踪每个段落的搜索-总结-反思循环

### 4. Tools (tools/)
搜索和分析工具集：

- **MediaCrawlerDB**: 6种舆情搜索工具
  - `search_hot_content`: 热点搜索
  - `search_topic_globally`: 全局话题搜索
  - `search_topic_by_date`: 时间线搜索
  - `get_comments_for_topic`: 评论获取
  - `search_topic_on_platform`: 平台定向搜索
  - `analyze_sentiment`: 情感分析

- **keyword_optimizer.py**: 关键词优化中间件
  - 将学术词汇转换为网民表达
  - 生成多个优化关键词并行查询

- **sentiment_analyzer.py**: 多语言情感分析
  - 支持22种语言
  - 输出5级情感等级（非常负面、负面、中性、正面、非常正面）

- **search.py**: 搜索工具包装
- **company_info_crawler.py**: 企业信息爬取

### 5. LLMs (llms/base.py)
- 与外部 LLM API 通信
- 遵循提示词 Schema 获取结构化输出

### 6. Prompts (prompts/prompts.py)
- 所有阶段的系统提示词定义
- JSON Schema 定义，规范 LLM 输出格式

### 7. Utils (utils/)
- 文本处理函数
- 配置管理
- 数据格式化

---

## 完整业务流程

### 流程概览

```
1️⃣ 初始化
   ├─ 加载 LLM 客户端
   ├─ 初始化搜索工具 (MediaCrawlerDB)
   ├─ 初始化情感分析器
   └─ 初始化各个节点

2️⃣ 报告规划阶段
   │ LLM 生成报告结构 
   │ ↓ 输出：[{title, content}, ...]

3️⃣ 对每个段落迭代执行：

   第一轮：【首次搜索 + 首次总结】
   ├─ 首次搜索
   │  ├─ LLM 生成初始搜索查询
   │  ├─ 关键词优化
   │  ├─ 多个搜索工具并行查询
   │  ├─ 去重 + 聚类采样
   │  ├─ 情感分析
   │  └─ 返回高质量结果
   │
   ├─ 首次总结
   │  ├─ LLM 使用搜索结果
   │  ├─ 生成段落初稿 (800-1200字)
   │  └─ 返回 paragraph_latest_state
   
   第N轮：【反思优化 + 反思总结】
   ├─ 反思（识别缺口）
   │  ├─ LLM 分析现有内容
   │  ├─ 识别缺少的视角/平台/时间段
   │  └─ 生成改进的搜索查询
   │
   ├─ 重新搜索（同上流程）
   │
   └─ 反思总结
      ├─ LLM 整合新旧数据
      ├─ 扩充段落内容 (1000-1500字)
      └─ 返回更新的 paragraph_latest_state

4️⃣ 最终格式化
   ├─ 收集所有段落
   ├─ LLM 生成专业舆情分析报告
   ├─ 整合数据表、用户引用、深度分析
   └─ 输出 Markdown 格式报告 (≥10000字)

5️⃣ 保存输出
   └─ 生成报告文件 + 状态快照
```

### 数据流向示例

```
查询: "武汉大学"
    ↓
报告规划: 5个段落
    ├─ 背景与事件概述
    ├─ 舆情热度分析
    ├─ 情感观点分析
    ├─ 群体差异分析
    └─ 深层原因分析
    ↓
每个段落迭代:
    LLM生成搜索词 → 优化 → 6个工具并行查询 
    → 去重+聚类 → 情感分析 → LLM总结生成段落
    → 评估缺口 → 反思搜索 → 扩充内容
    ↓
最终输出: 完整舆情分析报告
```

---

## 核心特性

✅ **多轮反思机制**
   - 不断补充缺失的民意视角
   - 每轮迭代扩充内容（800字 → 1000-1500字）

✅ **关键词优化**
   - 自动将学术词汇转换为网民表达
   - 避免官方化、书面语
   - 考虑不同平台的语言特色

✅ **情感分析**
   - 支持22种语言
   - 细分正面/负面/中性
   - 自动集成到搜索结果中

✅ **智能采样**
   - 使用聚类算法去除冗余结果
   - 保留最具代表性的数据

✅ **平台覆盖**
   - 微博、知乎、B站、抖音、快手、小红书、贴吧
   - 不同平台用户群体的观点差异分析

✅ **状态追踪**
   - 完整记录迭代过程
   - 支持中断恢复

✅ **数据密集化**
   - 每100字至少1-2个数据点
   - 大量用户评论引用
   - 详细的数据表格和对比

---

## 关键节点详解

### 首次搜索节点 (FirstSearchNode)
**职责**: 基于段落需求生成搜索查询

**输入**:
```json
{
  "title": "段落标题",
  "content": "段落需求描述"
}
```

**处理流程**:
1. LLM 分析段落需求
2. 生成搜索查询和工具选择
3. 关键词优化
4. 多工具并行查询
5. 去重 + 聚类采样
6. 情感分析

**输出**:
```json
{
  "search_query": "搜索词",
  "search_tool": "工具名",
  "reasoning": "查询理由",
  "results": [...],
  "sentiment_analysis": {...}
}
```

### 首次总结节点 (FirstSummaryNode)
**职责**: 根据搜索结果生成段落初稿

**输入**:
```json
{
  "title": "段落标题",
  "content": "段落需求",
  "search_query": "搜索词",
  "search_results": [...]
}
```

**处理流程**:
1. LLM 分析搜索结果
2. 提炼关键信息
3. 引用用户评论
4. 多层次分析
5. 生成800-1200字段落

**输出**:
```json
{
  "paragraph_latest_state": "详细的段落内容"
}
```

### 反思节点 (ReflectionNode)
**职责**: 识别缺口并生成改进搜索查询

**输入**:
```json
{
  "title": "段落标题",
  "content": "段落需求",
  "paragraph_latest_state": "当前段落内容"
}
```

**处理流程**:
1. LLM 评估现有内容质量
2. 识别缺失的视角/平台/时间段
3. 生成改进的搜索查询
4. 阐述补充理由

**输出**:
```json
{
  "search_query": "新的搜索词",
  "search_tool": "工具名",
  "reasoning": "为什么需要这个搜索"
}
```

### 反思总结节点 (ReflectionSummaryNode)
**职责**: 整合新旧数据扩充段落

**输入**:
```json
{
  "title": "段落标题",
  "content": "段落需求",
  "search_query": "搜索词",
  "search_results": [...],
  "paragraph_latest_state": "当前段落内容"
}
```

**处理流程**:
1. LLM 整合原有内容
2. 融合新的搜索结果
3. 扩充到1000-1500字
4. 保持信息密度 (每100字1-2个数据点)

**输出**:
```json
{
  "updated_paragraph_latest_state": "扩充后的段落内容"
}
```

### 报告格式化节点 (ReportFormattingNode)
**职责**: 整合所有段落生成最终报告

**输入**:
```json
[
  {
    "title": "段落1标题",
    "paragraph_latest_state": "段落1内容"
  },
  ...
]
```

**处理流程**:
1. LLM 整合所有段落
2. 生成执行摘要
3. 创建数据可视化
4. 添加深层洞察
5. 生成≥10000字专业报告

**输出**: Markdown 格式的完整舆情分析报告

---

## 工作流定制

### 搜索工具选择

| 工具 | 最佳场景 | 特点 |
|------|---------|------|
| search_hot_content | 挖掘当前热点 | 基于真实点赞/评论/分享数据 |
| search_topic_globally | 全面了解话题 | 覆盖所有平台，自动情感分析 |
| search_topic_by_date | 追踪时间线 | 精确时间范围，分析舆情演变 |
| get_comments_for_topic | 深度民意 | 直接获取用户评论 |
| search_topic_on_platform | 平台对比 | 分析特定平台用户观点差异 |
| analyze_sentiment | 专门分析 | 22种语言，5级情感等级 |

### 关键词优化策略

**避免的词汇**:
- 官方术语："舆情传播"、"公众反应"、"情绪倾向"
- 学术词汇："舆情"、"传播"、"倾向"

**使用的词汇**:
- 网民表达："出事了"、"怎么回事"、"翻车"、"炸了"
- 情感词：支持、反对、心疼、气死、666、绝了
- 平台特色：
  - 微博：热搜词汇、话题标签
  - 知乎：问答式表达
  - B站：弹幕文化（yyds、路过等）
  - 贴吧：直接称呼
  - 抖音/快手：短视频描述
  - 小红书：分享式表达

---

## 配置管理

主要配置参数（见 `utils/config.py`）:

```python
# LLM 配置
INSIGHT_ENGINE_API_KEY = "your_api_key"
INSIGHT_ENGINE_MODEL_NAME = "your_model"
INSIGHT_ENGINE_BASE_URL = "your_base_url"

# 搜索工具配置
DEFAULT_SEARCH_TOPIC_GLOBALLY_LIMIT_PER_TABLE = 100
DEFAULT_SEARCH_TOPIC_BY_DATE_LIMIT_PER_TABLE = 100
DEFAULT_GET_COMMENTS_FOR_TOPIC_LIMIT = 500
DEFAULT_SEARCH_TOPIC_ON_PLATFORM_LIMIT = 300

# 聚类配置
ENABLE_CLUSTERING = True
MAX_CLUSTERED_RESULTS = 50
RESULTS_PER_CLUSTER = 5

# 输出配置
OUTPUT_DIR = "output/"
```

---

## 使用示例

### 基础使用

```python
from InsightEngine import DeepSearchAgent

# 初始化
agent = DeepSearchAgent()

# 执行深度搜索
report = agent.deep_search(
    query="武汉大学",
    reflection_rounds=2  # 每个段落反思2轮
)

# 保存报告
agent.save_report(report, output_path="output/report.md")
```

### 自定义工作流

```python
# 自定义搜索参数
agent.deep_search(
    query="武汉大学",
    reflection_rounds=3,
    enable_sentiment=True,  # 启用情感分析
    enable_clustering=True,  # 启用聚类采样
    max_results=100  # 最大结果数
)
```

---

## 输出示例

### 最终报告结构

```markdown
# 【舆情洞察】武汉大学深度民意分析报告

## 执行摘要
### 核心舆情发现
- 主要情感倾向和分布
- 关键争议焦点
- 重要舆情数据指标

## 一、背景与事件概述
### 1.1 民意数据画像
| 平台 | 参与用户数 | 内容数量 | 正面情感% | 负面情感% |
|------|------------|----------|-----------|-----------|
| 微博 | 2.5万      | 856条    | 65%       | 25%       |

### 1.2 代表性民声
> "具体用户评论" —— @用户A (点赞数：1,234)

### 1.3 深度舆情解读
[详细的民意分析...]

## 二、舆情热度与传播分析
...

## 舆情态势综合分析
### 整体民意倾向
### 不同群体观点对比
### 平台差异化分析
### 舆情发展预判

## 深层洞察与建议
### 社会心理分析
### 舆情管理建议

## 数据附录
### 关键舆情指标汇总
### 重要用户评论合集
### 情感分析详细数据
```

---

## 性能优化

### 并行搜索
- 关键词优化后的多个关键词并行查询
- 多个搜索工具可并行执行

### 聚类采样
- 使用 `paraphrase-multilingual-MiniLM-L12-v2` 嵌入模型
- K-means 聚类算法
- 从每个聚类中采样代表性结果
- 大幅减少冗余数据

### 缓存机制
- 缓存 LLM 调用结果
- 缓存搜索结果
- 支持断点恢复

---

## 故障排除

### 常见问题

**Q: 情感分析失败？**
- A: 检查情感分析模型是否初始化，见 `tools/sentiment_analyzer.py`

**Q: 搜索结果为空？**
- A: 检查关键词是否过于具体，尝试使用 `search_topic_globally`

**Q: LLM 返回格式不正确？**
- A: 检查提示词中的 JSON Schema 定义是否正确

**Q: 报告生成过慢？**
- A: 减少 `reflection_rounds` 轮数，或启用聚类采样

---

## 扩展开发

### 添加新的搜索工具
1. 在 `tools/` 中实现工具类
2. 在 `MediaCrawlerDB` 中注册
3. 在提示词中添加工具说明

### 添加新的节点
1. 继承 `BaseNode` 或 `StateMutationNode`
2. 实现 `run()` 和 `validate_input()` 方法
3. 在 `agent.py` 中注册

### 定制提示词
编辑 `prompts/prompts.py` 中对应的 SYSTEM_PROMPT

---

## 相关文档

- [格式化节点](./nodes/formatting_node.py) - 报告格式化详解
- [搜索节点](./nodes/search_node.py) - 搜索查询生成详解
- [总结节点](./nodes/summary_node.py) - 内容总结详解
- [状态管理](./state/state.py) - 迭代状态管理详解
- [提示词定义](./prompts/prompts.py) - LLM 指令集详解
