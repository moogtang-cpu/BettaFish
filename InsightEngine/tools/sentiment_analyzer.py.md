# tools/sentiment_analyzer.py 文件分析

`InsightEngine/tools/sentiment_analyzer.py` 文件定义了 `WeiboMultilingualSentimentAnalyzer` 类，这是一个专门为 `DeepSearchAgent` 提供**多语言情感分析**功能的工具。它的核心业务逻辑是封装了一个基于 `Hugging Face Transformers` 库的多语言序列分类模型，以对文本内容进行情感倾向预测，并将结果以结构化的方式返回给 Agent。

### 1. **核心定位：多语言情感洞察提供者**

-   `WeiboMultilingualSentimentAnalyzer` 的主要职责是对 `DeepSearchAgent` 在研究过程中获取的文本数据（例如从 `MediaCrawlerDB` 获取的搜索结果内容、用户评论等）进行情感倾向识别和分析。
-   它支持多种语言（如中文、英文、西班牙文、阿拉伯文、日文、韩文等共 22 种），并提供精细的 5 级情感分类（非常负面、负面、中性、正面、非常正面），为 `DeepSearchAgent` 提供了更深层次的舆情洞察，使其能够理解公众的真实情绪。

### 2. **依赖管理与可用性检查**

-   **前置检查**：文件开头显式检查了 `torch` (PyTorch) 和 `transformers` 库的可用性 (`TORCH_AVAILABLE`, `TRANSFORMERS_AVAILABLE`)。这是为了确保模型运行所需的核心深度学习框架和库已正确安装。
-   **手动开关**：`SENTIMENT_ANALYSIS_ENABLED` 全局布尔变量提供了一个方便的手动开关，允许在不修改代码逻辑的情况下全局禁用情感分析功能，这在调试或资源受限时非常有用。
-   **智能禁用**：在初始化 `WeiboMultilingualSentimentAnalyzer` 实例时，会根据上述依赖检查和手动开关状态，自动禁用或启用情感分析功能，并提供详细的禁用原因 (`disable_reason`)。这增强了工具的鲁棒性，并为调用者提供了清晰的反馈。

### 3. **数据结构定义 (`SentimentResult`, `BatchSentimentResult`)**

-   **`SentimentResult`**：这是一个 `dataclass`，用于统一表示单个文本的情感分析结果。它包含了原始文本 (`text`)、情感标签 (`sentiment_label`)、置信度 (`confidence`)、完整的概率分布 (`probability_distribution`)，以及操作是否成功 (`success`)、可能的错误信息 (`error_message`) 和是否实际执行了分析 (`analysis_performed`)。
-   **`BatchSentimentResult`**：这是一个 `dataclass`，用于封装批量文本的情感分析结果。它聚合了所有单个 `SentimentResult` 对象，并提供了总处理数量 (`total_processed`)、成功/失败计数 (`success_count`, `failed_count`)、平均置信度 (`average_confidence`) 等汇总统计信息，方便对批量结果进行整体评估。

### 4. **初始化 (`__init__` 和 `initialize` 方法)**

-   **懒加载 (Lazy Initialization)**：`WeiboMultilingualSentimentAnalyzer` 实例在创建时不会立即加载庞大的深度学习模型。模型只有在第一次真正需要进行分析时（通过调用 `initialize()` 方法）才会被加载。这种设计模式显著节省了应用程序的启动时间和内存资源。
-   **模型加载逻辑 (`initialize`)**：
    -   在 `initialize` 方法中，它会进行一系列前置检查，包括依赖、手动开关和是否已初始化。
    -   它会尝试从本地路径（`<项目根目录>/SentimentAnalysisModel/WeiboMultilingualSentiment/model`）加载预训练的多语言序列分类模型 (`tabularisai/multilingual-sentiment-analysis`) 和其对应的分词器 (`AutoTokenizer`)。
    -   如果本地不存在模型文件，它会自动从 Hugging Face 模型库下载模型并保存到本地，方便后续使用，避免重复下载。
    -   **智能设备选择 (`_select_device`)**：该私有方法会自动检测并选择最佳的可用计算设备进行推理（优先使用 CUDA GPU，其次是 Apple MPS，最后是 CPU）。这确保了模型在不同硬件环境下都能高效运行，无需手动配置。
    -   模型加载成功后，`is_initialized` 标志被设为 `True`，并启用分析器。
-   **情感标签映射**：内部定义了 `self.sentiment_map` 字典，将模型的原始输出标签（通常是 0 到 4 的整数）映射到更具可读性的 5 级中文情感描述（"非常负面", "负面", "中性", "正面", "非常正面"）。

### 5. **核心分析方法**

-   **`analyze_single_text` (单个文本情感分析)**：
    -   **预处理**：首先对输入文本进行基本的清理 (`_preprocess_text`)，例如去除多余空格等。
    -   **模型推理**：使用加载的分词器对文本进行编码，然后将编码后的输入送入模型进行预测。推理过程在 `torch.no_grad()` 上下文中执行，避免计算梯度，提高效率并减少内存消耗。
    -   **结果转换**：将模型的原始 `logits` 转换为概率分布，然后选择最高概率对应的标签，并根据 `sentiment_map` 映射到可读的情感标签。
    -   **输出**：返回一个 `SentimentResult` 对象，包含了详细的分析结果。
    -   **错误处理**：包含了对禁用状态、未初始化模型、空文本以及预测过程中可能发生的各种异常的健壮处理，确保始终返回一个有意义的 `SentimentResult` 对象，即使分析失败也能提供原因。

-   **`analyze_batch` (批量情感分析)**：
    -   **功能**：对一个文本列表进行批量情感分析，是处理大量文本时的主要方法。
    -   **机制**：遍历输入的文本列表，为每个文本调用 `analyze_single_text` 方法。
    -   **结果聚合**：聚合所有单个分析结果，并计算成功的数量、失败的数量、总处理数量和平均置信度，然后封装在 `BatchSentimentResult` 对象中返回。
    -   **进度显示**：支持在分析过程中显示进度信息，提升用户体验。

-   **`analyze_query_results` (对查询结果进行情感分析) - 专门用于 Agent**：
    -   **目的**：这是为 `DeepSearchAgent` 定制的核心方法，用于直接处理从 `MediaCrawlerDB` 等工具获取的原始查询结果（通常是一个字典列表），而不是简单的文本列表。
    -   **文本提取**：它能够智能地从复杂的查询结果字典中提取出需要分析的文本内容。它会尝试 `text_field`（用户指定）、`title_or_content`、`content`、`title`、`text` 等多个常见字段，增加了极大的灵活性和容错性。
    -   **批量分析**：提取所有文本后，调用 `analyze_batch` 进行高效的批量情感分析。
    -   **结果汇总与摘要**：对批量分析结果进行进一步处理，生成高层级的情感洞察：
        -   **情感分布统计**：计算不同情感标签的出现次数和比例。
        -   **高置信度结果提取**：根据 `min_confidence` 阈值，筛选并返回具有高置信度的分析结果，突出显示那些情感倾向明确的文本片段。
        -   **摘要生成**：生成一段关于整体情感趋势和主要情感倾向的总结性文字。
    -   **透传机制 (`_build_passthrough_analysis`)**：在情感分析功能被禁用或模型加载失败等情况下，它会构建一个“透传”响应，明确告知上层调用者情感分析未执行的原因，但仍返回原始数据。这确保了即使情感分析不可用，整个研究流程也能继续进行，而不会中断。
    -   **输出**：返回一个包含 `sentiment_analysis` 键的字典，其中包含了丰富的、结构化的情感分析洞察，非常适合 Agent 进行进一步的推理和报告撰写。

### 6. **辅助函数和全局实例**

-   `_preprocess_text`：用于基本的文本预处理。
-   `get_model_info`：返回模型的相关信息，如名称、支持语言、情感级别等。
-   `enable`/`disable`：公共方法，用于在运行时动态启用或禁用情感分析功能，提供了运行时的控制能力。
-   `analyze_sentiment`：一个便捷的顶层函数，允许外部直接调用情感分析功能，并支持自动初始化模型。
-   **全局实例**：文件末尾创建了一个 `multilingual_sentiment_analyzer = WeiboMultilingualSentimentAnalyzer()` 的全局单例实例。这使得 `InsightEngine` 中的其他模块可以直接使用这个已配置好的情感分析器，而无需每次都重新实例化。

### 总结

`InsightEngine/tools/sentiment_analyzer.py` 文件中的 `WeiboMultilingualSentimentAnalyzer` 是 `DeepSearchAgent` 获取**情感维度洞察**的关键工具。它：

1.  **提供了强大的多语言情感分析能力**：能够处理来自不同语种社交媒体的文本，覆盖广泛。
2.  **具备高度的健壮性和可用性**：通过依赖检查、手动开关、懒加载、设备智能选择以及全面的错误处理，确保了即使在复杂或受限的环境下也能稳定运行或优雅降级，不会导致整个系统崩溃。
3.  **支持灵活的调用模式**：提供单个文本、批量文本和针对特定查询结果的分析方法，以适应 `DeepSearchAgent` 不同场景下的需求。
4.  **产出结构化、可理解的洞察**：将模型的原始预测结果转化为易于理解的 5 级情感标签、置信度、概率分布，并提供聚合的分布统计和摘要，极大地便利了 Agent 进行进一步的推理和报告撰写。

这个工具使得 `DeepSearchAgent` 能够超越纯粹的事实检索，深入理解公众对特定话题的真实情感和态度，从而生成更具深度和“人情味”的舆情分析报告，是其核心竞争力之一。
