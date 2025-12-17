# ReportEngine — 目录说明与运行指南

本文件为 `ReportEngine` 目录的架构与业务流程说明，基于代码阅读（`agent.py`、`nodes/*.py`、`core/*.py`、`renderers/*.py`）整理而成，便于维护、集成与调试。

## 概要

- **目的**: 聚合 InsightEngine、MediaEngine、QueryEngine 三个子引擎的 Markdown 报告与 ForumEngine 的论坛讨论，通过**模板选择 → 布局设计 → 篇幅规划 → 章节生成 → 装订渲染**完整流程，最终生成**结构化的 HTML/PDF 专业报告**。
- **核心特色**:
  - **多阶段编排**: 模板选择、文档布局、字数预算、章节生成、IR装订、HTML渲染
  - **异步生成**: 章节流式生成与写入，前端可实时监听进度
  - **跨引擎修复**: 当单个引擎输出有问题时，自动尝试其他引擎的 LLM 进行修复
  - **文件增量检测**: 监控三个子引擎的输出目录，自动捕捉新报告
  - **IR 与装订**: 生成标准化的 Document IR，支持多渲染器（HTML、PDF）
  - **主题与样式**: 内置 CSS 主题、响应式设计、Chart.js/MathJax 支持

## 目录核心文件与模块

### `agent.py` - 主编排器

[ReportEngine/agent.py](ReportEngine/agent.py#L1-L1514)

主要类：
- **`ReportAgent`**: 核心agent类，整合所有流程，驱动从多引擎输入到最终 HTML/PDF 输出。
- **`FileCountBaseline`**: 文件增量检测器，监控三个子引擎的输出目录变化。

**主要职责**:
- 初始化 LLM 客户端、四个处理节点、章节存储、IR装订器、渲染器
- 初始化跨引擎 LLM 修复链表（Report → Forum → Insight → Media）
- 协调完整的报告生成流程
- 管理文件增量检测与新报告自动触发
- 处理日志、状态持久化、错误兜底

### `core/` - 核心装订与存储

| 文件 | 类 | 职责 |
|------|----|----|
| `chapter_storage.py` | `ChapterStorage` / `ChapterRecord` | 章节JSON落盘、manifest管理、元数据追踪 |
| `stitcher.py` | `DocumentComposer` | 多章节拼接成整本 IR、锚点去重、元数据注入 |
| `template_parser.py` | `TemplateSection` / `parse_template_sections` | 模板文件解析、段落与主题提取 |

### `nodes/` - 处理节点

| 文件 | 类 | 职责 |
|------|----|----|
| `base_node.py` | `BaseNode` | 定义所有节点的基础接口 |
| `template_selection_node.py` | `TemplateSelectionNode` | 根据输入内容与主题选择合适的报告模板 |
| `document_layout_node.py` | `DocumentLayoutNode` | 根据模板与内容生成文档布局方案 |
| `word_budget_node.py` | `WordBudgetNode` | 为每个章节分配字数预算 |
| `chapter_generation_node.py` | `ChapterGenerationNode` | 核心章节生成节点，包含流式写入、JSON校验、跨引擎修复 |

### `renderers/` - 渲染器

| 文件 | 类 | 职责 |
|------|----|----|
| `html_renderer.py` | `HTMLRenderer` | Document IR → HTML，支持响应式、主题切换、Chart.js、MathJax |
| `pdf_renderer.py` | `PDFRenderer` | HTML → PDF，支持分页、字体子集嵌入 |
| `pdf_layout_optimizer.py` | - | PDF 分页优化、断点检测、表格宽度调整 |
| `chart_to_svg.py` | - | Chart.js 配置转换为 SVG（PDF 输出所需） |
| `math_to_svg.py` | - | MathJax 公式转换为 SVG |

### `ir/` - 中间表示（Intermediate Representation）

- **`schema.py`**: 定义 Document IR 的数据结构（chapters、blocks、themeTokens 等）
- **`validator.py`**: `IRValidator` 类，对章节 JSON 进行结构与内容校验

### `prompts/` - 提示词

包含各个处理阶段的 LLM 提示词。

### `state/` - 状态管理

定义 `ReportState` 类，维护：
- 报告标题、主题、查询
- 三个子引擎的输入 Markdown
- 章节列表与生成进度
- 最终 IR 与渲染输出

### `llms/` - LLM 客户端

定义 `LLMClient`，提供统一的 LLM 推理入口。

### `utils/` - 工具函数

- **`config.py`**: 配置管理
- **`chart_validator.py`**: Chart.js 配置本地校验与修复
- **`chart_repair_api.py`**: 调用 LLM 进行 Chart.js 修复

### `flask_interface.py` - Web 接口

提供 Flask Web 服务端点，支持前端进度查询、日志流推送等。

## 主要概念与设计要点

### 1. 文件增量检测

- **`FileCountBaseline`**: 记录三个子引擎输出目录的初始文件数
- **轮询机制**: 定期检查目录中新增 `.md` 文件数
- **自动触发**: 当检测到新报告时，自动启动报告生成流程

### 2. 模板选择

- **输入**: 用户查询、三个引擎的输出 Markdown
- **处理**: LLM 分析内容，选择最合适的报告模板
- **输出**: 模板结构与主题配置

### 3. 文档布局

- **输入**: 选中的模板、内容摘要
- **处理**: LLM 设计文档的章节顺序、分页方案、目录结构
- **输出**: 布局 JSON（chapterId、order、anchor 等）

### 4. 字数预算

- **输入**: 三个引擎的总字数、目标报告长度
- **处理**: LLM 为每个章节分配合理的字数范围
- **输出**: 各章节的字数上限与下限

### 5. 章节生成（核心流程）

```
FOR 每个章节:
  1. 基于布局、字数预算、三引擎内容生成章节 JSON
  2. 流式写入 stream.raw 文件
  3. JSON 校验：
     - 本地结构校验（JSON Schema）
     - IR 语义校验（章节内块结构、anchor等）
  4. 若校验失败：
     - 尝试自动修复（移除无效块、补齐必填字段）
     - 若修复仍失败，尝试跨引擎 LLM 重新生成
  5. 通过校验后，写入 chapter.json 并更新 manifest
  6. 章节元数据保存到 ChapterRecord
```

### 6. IR 与装订

- **`DocumentComposer`**: 将多个章节 JSON 按 order 排序并拼接
- **锚点处理**: 自动去重、补齐，确保全局唯一
- **元数据合并**: 合并 themeTokens、assets、TOC 等

### 7. HTML 渲染

- **输入**: Document IR
- **处理**:
  - 生成响应式 HTML（React 式的交互）
  - 嵌入主题 CSS 变量
  - 处理 Chart.js 组件（先校验数据）
  - 处理 MathJax 公式
  - 注水 JavaScript（按钮交互、图表实例化等）
- **输出**: 单文件 HTML（所有资源内联）

### 8. 错误处理与修复链

```
主 LLM (Report Engine)
  ↓ (若失败)
论坛主持人 LLM (ForumEngine)
  ↓ (若失败)
洞察引擎 LLM (InsightEngine)
  ↓ (若失败)
媒体引擎 LLM (MediaEngine)
  ↓ (若全部失败)
报错并记录
```

## 业务流程（完整步骤化）

### Step 1: 初始化与文件检测

```
启动 ReportAgent
  ↓
初始化 LLM、节点、渲染器、文件基准管理器
  ↓
记录三个引擎的初始文件数
  ↓
进入轮询模式，每秒检查新文件
```

### Step 2: 输入准备

```
检测到新文件 ✓
  ↓
读取三个引擎最新的 Markdown 文件
  ↓
解析内容提取摘要、关键字、主题
  ↓
加载论坛 forum.log（如果可用）
  ↓
状态更新：标记输入就绪
```

### Step 3: 模板选择

```
[TemplateSelectionNode]
  输入: {query, engine_summaries, forum_context}
    ↓
  LLM 分析并选择模板（例如"三层递进式分析"）
    ↓
  输出: {template_id, theme, toc_outline}
```

### Step 4: 文档布局

```
[DocumentLayoutNode]
  输入: {template_config, engine_contents, word_limit}
    ↓
  LLM 设计章节顺序、分页方案、目录结构
    ↓
  输出: {layout_spec} = {
    chapters: [
      {chapterId, title, order, anchor, content_sources, word_budget}
    ]
  }
```

### Step 5: 字数预算

```
[WordBudgetNode]
  输入: {layout_spec, engine_word_counts}
    ↓
  LLM 为每章分配字数范围
    ↓
  输出: {chapter_budgets} = {
    "S1": {"min": 500, "max": 1000},
    "S2": {"min": 800, "max": 1200},
    ...
  }
```

### Step 6: 章节生成（流式）

```
FOR 每个章节 i:
  
  [ChapterGenerationNode]
    输入: {
      chapter_spec: {title, content_sources, word_budget},
      engine_content: {query_text, media_text, insight_text},
      forum_context: {...}
    }
    ↓
  LLM 生成章节 JSON
    ↓
  流式写入 stream.raw
    ↓
  本地 JSON Schema 校验
    ↓
  IR 语义校验（IRValidator）
    ├─ 若校验通过 → 写入 chapter.json
    │
    └─ 若校验失败 → 进入修复流程：
       ├─ 尝试自动修复（移除无效块等）
       ├─ 若修复成功 → 写入 chapter.json
       └─ 若修复失败 → 尝试跨引擎 LLM 重新生成
  
  更新 manifest 与 ChapterRecord
  报告进度
```

### Step 7: IR 装订

```
[DocumentComposer.build_document]
  输入: {
    report_id,
    metadata: {title, theme, toc, assets},
    chapters: [...all validated chapters...]
  }
    ↓
  按 order 排序章节
    ↓
  补齐 chapterId、anchor、metadata
    ↓
  去重检查（anchor、heading_id）
    ↓
  合并 themeTokens、assets
    ↓
  输出: Document IR (满足渲染器需求)
```

### Step 8: 渲染与导出

```
[HTMLRenderer.render]
  输入: Document IR
    ↓
  生成 <head>：CSS变量、库引入、CDN fallback
    ↓
  生成 <body>：页眉、目录、章节块、脚本注水
    ↓
  处理 Chart.js：
    - 校验数据配置
    - 若无效，尝试 LLM 修复
    - 生成图表脚本
    ↓
  处理 MathJax：
    - 提取公式
    - 转换为 SVG（PDF 需要）
    ↓
  输出: report.html (单文件，所有资源内联)

[PDFRenderer.render] (可选)
  输入: report.html 或 Document IR
    ↓
  html2canvas + jspdf 转换
    ↓
  分页优化
    ↓
  字体子集嵌入
    ↓
  输出: report.pdf
```

### ASCII 流程图

```
三引擎输入 (Insight/Media/Query Markdown)
  ↓
[文件增量检测] ✓
  ↓
[模板选择] → template_id + theme
  ↓
[文档布局] → layout_spec (章节顺序)
  ↓
[字数预算] → chapter_budgets
  ↓
FOR 每个章节 ━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ├─ [章节生成] → JSON (流式写入)
  ├─ [本地校验] ✓/✗
  ├─ 若失败 → [自动修复] ✓/✗
  ├─ 若失败 → [跨引擎 LLM 修复] ✓/✗
  └─ 若全部失败 → 报错并记录
  
[IR 装订] → Document IR
  ├─ 按order排序
  ├─ 去重anchor
  └─ 合并metadata
  
[HTML 渲染] → report.html
  ├─ 生成响应式HTML
  ├─ 校验+修复 Chart.js
  └─ 处理 MathJax
  
[PDF 渲染] (可选) → report.pdf
  ├─ HTML2Canvas
  ├─ 分页优化
  └─ 字体嵌入

报告完成 ✓
```

## 配置项

配置来源: [config.py](config.py) 或 [ReportEngine/utils/config.py](ReportEngine/utils/config.py)

关键字段:

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `REPORT_ENGINE_API_KEY` | Report Agent LLM API 密钥 | None |
| `REPORT_ENGINE_MODEL_NAME` | LLM 模型标识 | None |
| `REPORT_ENGINE_BASE_URL` | LLM Base URL | None |
| `FORUM_HOST_API_KEY` | Forum 主持人 LLM API 密钥（修复链） | None |
| `INSIGHT_ENGINE_API_KEY` | Insight 引擎 LLM API 密钥（修复链） | None |
| `MEDIA_ENGINE_API_KEY` | Media 引擎 LLM API 密钥（修复链） | None |
| `TEMPLATE_DIR` | 模板文件所在目录 | "templates" |
| `CHAPTER_OUTPUT_DIR` | 章节 JSON 输出目录 | "final_reports" |
| `OUTPUT_DIR` | 最终 HTML/PDF 输出目录 | "output" |
| `DOCUMENT_IR_OUTPUT_DIR` | Document IR JSON 输出目录 | "document_ir" |
| `LOG_FILE` | Report Engine 专属日志文件 | "logs/report_engine.log" |
| `FLASK_PORT` | Web 服务端口 | 5000 |

示例环境变量：

```bash
REPORT_ENGINE_API_KEY=sk-xxxxx
REPORT_ENGINE_MODEL_NAME=gpt-4o
REPORT_ENGINE_BASE_URL=https://api.openai.com/v1
FORUM_HOST_API_KEY=sk-xxxxx  # 修复链备选
INSIGHT_ENGINE_API_KEY=sk-xxxxx  # 修复链备选
MEDIA_ENGINE_API_KEY=sk-xxxxx  # 修复链备选
TEMPLATE_DIR=/path/to/templates
CHAPTER_OUTPUT_DIR=final_reports
OUTPUT_DIR=output
FLASK_PORT=5000
```

## 使用示例

### 基本使用

```python
from ReportEngine import ReportAgent

# 创建agent
agent = ReportAgent()

# 自动监控三个子引擎的输出
# 当检测到新文件时自动触发报告生成
# 生成过程会流式输出到 HTML 与 PDF

# 查看生成进度
progress = agent.state.get_progress()
print(f"已生成章节: {progress['chapters_done']}/{progress['total_chapters']}")
```

### 手动触发报告生成

```python
# 不依赖文件监控，直接输入三引擎 Markdown
engine_inputs = {
    'query': 'QueryEngine markdown content...',
    'media': 'MediaEngine markdown content...',
    'insight': 'InsightEngine markdown content...',
    'forum': 'forum.log content...'  # 可选
}

report_id = agent.generate_report(
    query='研究主题',
    engine_inputs=engine_inputs,
    save_report=True
)

# 查看生成的报告
print(f"报告已生成: output/{report_id}.html")
```

### 访问 Web 服务

```bash
# 启动 Flask 服务
python app.py

# 前端访问
curl http://localhost:5000/api/status
curl http://localhost:5000/api/progress
curl http://localhost:5000/logs/stream
```

## 节点深入理解

### TemplateSelectionNode

| 特性 | 说明 |
|------|------|
| **输入** | query, engine_summaries, forum_context |
| **职责** | 分析内容特征，选择最合适的报告模板 |
| **输出** | template_id, theme_config, toc_outline |
| **LLM 任务** | 理解内容类型（深度分析/对比/趋势等），推荐模板 |

### DocumentLayoutNode

| 特性 | 说明 |
|------|------|
| **输入** | template_config, engine_contents, word_limit |
| **职责** | 设计文档结构：章节顺序、主次、分页方案 |
| **输出** | layout_spec with chapter definitions |
| **LLM 任务** | 基于模板与内容逻辑，规划最优章节布局 |

### WordBudgetNode

| 特性 | 说明 |
|------|------|
| **输入** | layout_spec, engine_word_counts |
| **职责** | 为每章分配合理的字数范围 |
| **输出** | {chapter_id: {min, max}} 字数预算 |
| **LLM 任务** | 根据章节重要性与内容复杂度分配预算 |

### ChapterGenerationNode

| 特性 | 说明 |
|------|------|
| **输入** | chapter_spec, engine_content, forum_context, budget |
| **职责** | 生成章节 JSON，包含校验、修复、跨引擎修复 |
| **输出** | validated_chapter.json 或 error_placeholder |
| **LLM 任务** | 生成符合 IR Schema 的结构化章节内容 |
| **修复链** | 本地校验 → 自动修复 → Report LLM → Forum LLM → Insight LLM → Media LLM |

## Chapter JSON 结构示例

```json
{
  "chapterId": "S1",
  "slug": "executive-summary",
  "title": "执行摘要",
  "order": 10,
  "anchor": "section-1",
  "blocks": [
    {
      "type": "paragraph",
      "content": "本报告深入分析了..."
    },
    {
      "type": "table",
      "props": {"title": "关键数据"},
      "data": [["指标", "数值"], ["增长率", "25%"]]
    },
    {
      "type": "chart",
      "widgetType": "bar",
      "data": {"labels": [...], "datasets": [...]}
    }
  ]
}
```

## Document IR 顶层结构

```json
{
  "version": "1.0",
  "reportId": "report-20251217-xxxxx",
  "metadata": {
    "title": "2025年AI市场深度分析报告",
    "theme": "blue",
    "generatedAt": "2025-12-17T10:30:00Z",
    "toc": {
      "title": "目录",
      "customEntries": [...]
    }
  },
  "themeTokens": {
    "primaryColor": "#0066cc",
    "fontFamily": "仓耳等宽宋"
  },
  "chapters": [
    {章节1}, {章节2}, ...
  ],
  "assets": {
    "fonts": {...},
    "icons": {...}
  }
}
```

## 常见问题与故障排查

### 1. 章节生成失败

**症状**: 某个章节报错或内容为空

**检查**:
- 查看日志中的 JSON 校验错误详情
- 验证 LLM 是否返回了有效 JSON
- 检查字数预算是否过小

**解决**:
- 启用自动修复（已默认启用）
- 增加修复链中的 LLM 备选项
- 手动调整字数预算

### 2. HTML 渲染问题

**症状**: Chart.js 图表不显示或样式错乱

**检查**:
- 查看浏览器开发者工具的控制台错误
- 验证 Chart.js 数据配置是否有效
- 检查 CSS 变量是否正确加载

**解决**:
- 启用 Chart 校验与修复（已内置）
- 更新图表配置
- 清理浏览器缓存重新加载

### 3. PDF 转换失败

**症状**: PDF 生成时出错或页面空白

**检查**:
- 验证 html2canvas 与 jspdf 库是否加载
- 检查 HTML 是否包含不兼容的元素
- 查看分页优化日志

**解决**:
- 简化 HTML（移除复杂的交互）
- 增加超时时间
- 使用服务端 PDF 转换（如 Puppeteer）

### 4. 文件监控未触发

**症状**: 新文件生成后没有自动启动报告生成

**检查**:
- 验证三个引擎的输出目录是否正确
- 查看文件基准是否初始化
- 检查轮询是否正常运行

**解决**:
- 手动调用 `agent.generate_report()`
- 检查日志目录权限
- 重启 ReportAgent

## 与其他引擎的关系

- **输入来源**: InsightEngine、MediaEngine、QueryEngine 的 Markdown 报告
- **论坛整合**: 可选地集成 ForumEngine 的 forum.log（主持人发言）
- **修复链**: 跨引擎 LLM 修复（优先级：Report → Forum → Insight → Media）

## 扩展建议 / 下一步

1. **实时协作编辑**: 支持多用户同时编辑生成的报告
2. **版本管理**: 保存报告的多个版本，支持对比与恢复
3. **自定义模板**: 提供模板编辑器，用户可自定义报告样式
4. **多语言输出**: 支持报告翻译与多语言渲染
5. **数据源更新**: 支持定期更新报告（重新抓取三引擎输出）
6. **分布式生成**: 将章节生成分散到多个 Worker 进程加快速度
7. **可视化编辑**: Web 拖拽界面调整章节顺序与内容
8. **知识图谱**: 提取并可视化文档中的实体与关系

## 文件实现参考

- `ReportEngine/agent.py` — 主编排与流程控制
- `ReportEngine/nodes/*.py` — 四个处理节点
- `ReportEngine/core/*.py` — 章节存储、IR装订、模板解析
- `ReportEngine/renderers/*.py` — HTML/PDF 渲染
- `ReportEngine/ir/*.py` — IR Schema 与校验
- `ReportEngine/flask_interface.py` — Web 服务接口

---

如果你希望我增加可视化流程图、详细讲解修复链逻辑、或提供模板编写指南，我可以继续完善本文档。
