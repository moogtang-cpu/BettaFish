# SentimentAnalysisModel — 目录说明与运行指南

本文件为 `SentimentAnalysisModel` 目录的架构与业务流程说明，基于代码阅读（predict.py、train.py、README.md）整理而成，便于维护、集成与调试。

## 概要

- **目的**: 提供多种**中文情感分析与话题分类**的预训练模型与微调脚本。包括BERT微调、多语言情感分析、传统机器学习方法等多个实现方案。
- **核心特色**:
  - **多模型并存**: 支持5种不同架构的模型（BERT微调、LoRA、Adapter、多语言、传统ML）
  - **话题分类**: 基于BERT的中文话题分类（约2.8万个话题，410万+训练样本）
  - **情感分析**: 二分类（正面/负面）或五分类（非常负面→非常正面）
  - **灵活的微调**: 支持LoRA、AdapterTuning等参数高效微调
  - **本地缓存**: 自动管理模型本地缓存，支持离线推理
  - **单卡锁定**: 统一的GPU管理机制，避免多卡冲突

## 目录结构

```
SentimentAnalysisModel/
├── BertTopicDetection_Finetuned/        # 话题分类（BERT中文基座）
│   ├── dataset/                         # 训练数据（410万+样本）
│   ├── model/                           # 生成的微调模型与缓存
│   ├── train.py                         # 训练脚本
│   ├── predict.py                       # 预测脚本
│   └── README.md
│
├── WeiboMultilingualSentiment/          # 多语言情感分析
│   ├── predict.py                       # 支持22种语言
│   └── README.md
│
├── WeiboSentiment_Finetuned/            # 微博情感分析（多种微调方式）
│   ├── BertChinese-Lora/                # LoRA微调
│   ├── GPT2-Lora/                       # GPT2 + LoRA
│   ├── GPT2-AdapterTuning/              # GPT2 + Adapter
│   └── README.md
│
├── WeiboSentiment_MachineLearning/      # 传统机器学习方法
│   ├── data/                            # 数据文件
│   ├── bayes_train.py                   # 朴素贝叶斯
│   ├── svm_train.py                     # SVM
│   ├── xgboost_train.py                 # XGBoost
│   ├── lstm_train.py                    # LSTM
│   ├── bert_train.py                    # BERT+分类头
│   └── README.md
│
└── WeiboSentiment_SmallQwen/            # 小规模Qwen模型
    ├── predict.py
    └── README.md
```

## 核心模块详解

### 1. BertTopicDetection_Finetuned — 话题分类

**目的**: 对中文文本进行话题分类（约2.8万个话题）

**关键特性**:
- **基座模型**: google-bert/bert-base-chinese（可选其他8种中文基座）
- **数据集**: 
  - 原始数据：1400万+ 问答对
  - 过滤数据：410万+ 高质量样本（点赞≥3）
  - 类别数：约2.8万个话题
- **微调方式**: 标准的 SequenceClassification 微调

**工作流程**:

```
train.py:
  1. 加载或下载基座模型（自动三段式：本地→缓存→远程）
  2. 读取 dataset/ 中的 CSV 数据
  3. 自动识别文本列与标签列
  4. 构建 DataLoader 与 Trainer
  5. 执行微调训练（支持 Early Stopping）
  6. 保存微调结果到 model/

predict.py:
  1. 加载微调后的模型
  2. 支持单条预测或交互模式
  3. 返回 Top-K 预测结果（默认Top-3）
  4. 显示置信度分数
```

**使用示例**:

```python
# 训练
python train.py --dataset_path dataset/train.csv --epochs 3 --gpu 0

# 预测
python predict.py --text "介绍一下深度学习" --gpu 0
```

### 2. WeiboMultilingualSentiment — 多语言情感分析

**目的**: 支持22种语言的情感分析（二分类或五分类）

**支持语言**: 中文、英文、西班牙文、阿拉伯文、日文、韩文等22种

**情感等级**: 
- 二分类：正面/负面
- 五分类：非常负面 → 负面 → 中性 → 正面 → 非常正面

**关键特性**:
- **模型**: tabularisai/multilingual-sentiment-analysis
- **自动下载**: 首次使用自动下载模型，后续使用本地缓存
- **快速推理**: 支持交互式输入与批量处理

**工作流程**:

```
predict.py:
  1. 检查本地缓存 (./model)
  2. 若无则下载模型到本地
  3. 进入交互模式
  4. 对每条输入进行：
     - 文本预处理
     - 分词编码（max_length=512）
     - 模型推理
     - 概率softmax + argmax
     - 返回预测标签与置信度
  5. 支持 'q' 退出、'demo' 查看示例
```

**使用示例**:

```python
# 交互模式
python predict.py

# 输入示例
请输入文本: I love this movie!
预测结果: 正面 (置信度: 0.9512)

# 多语言示例
请输入文本: 这个产品太棒了！
预测结果: 非常正面 (置信度: 0.9823)
```

### 3. WeiboSentiment_Finetuned — 微博情感分析（多种微调方式）

**目的**: 针对微博数据的情感分析（正面/负面二分类），提供多种参数高效微调方案

**子模块**:

| 目录 | 模型 | 微调方法 | 特点 |
|------|------|--------|------|
| BertChinese-Lora | BERT中文基座 | LoRA (Low-Rank Adaptation) | 参数量少，微调快速 |
| GPT2-Lora | GPT2中文 | LoRA | 支持生成式方法 |
| GPT2-AdapterTuning | GPT2中文 | Adapter | 轻量级适配器 |

**LoRA 微调原理**:
```
原始参数: W ∈ R^{d_out × d_in}
LoRA 分解: W' = W + ΔW = W + BA

其中:
  - B: d_out × r 的可训练矩阵
  - A: r × d_in 的可训练矩阵
  - r: 秩（通常 r << d_in, d_out）
  
优势: 可训练参数 ≈ 2 × d_out × r << W 的总参数
```

**工作流程**:

```
train.py (以LoRA为例):
  1. 加载预训练模型（例如 bert-base-chinese）
  2. 初始化 LoRA 配置 (rank=8, alpha=16)
  3. 为每个 attention/dense 层添加 LoRA 适配器
  4. 冻结基座权重，仅训练 LoRA 参数
  5. 构建训练循环
  6. 保存 LoRA 权重（远小于完整模型）

predict.py:
  1. 加载基座模型
  2. 注册 LoRA 权重
  3. 执行推理
```

**使用示例**:

```bash
# 训练
cd WeiboSentiment_Finetuned/BertChinese-Lora
python train.py --epochs 5 --batch_size 16 --lora_rank 8

# 预测
python predict.py --text "这个产品真的很不错" --gpu 0
```

### 4. WeiboSentiment_MachineLearning — 传统机器学习方法

**目的**: 使用传统ML与早期神经网络方法进行微博情感分析

**支持的模型**:

| 模型 | 准确率 | AUC | 特点 |
|------|--------|-----|------|
| 朴素贝叶斯 (Naive Bayes) | 85.6% | - | 快速，内存占用小 |
| SVM (支持向量机) | 85.6% | - | 泛化能力强 |
| XGBoost | 86.0% | 90.4% | 稳定，支持特征重要性分析 |
| LSTM | 87.0% | 93.1% | 理解序列与上下文 |
| BERT+分类头 | 87.0% | 92.9% | 强大的语义理解 |

**工作流程**:

```
朴素贝叶斯 (bayes_train.py):
  1. 加载数据集 (data/weibo2018/train.txt)
  2. 文本预处理 (分词、清理、停用词过滤)
  3. 构建词汇表
  4. TF-IDF 特征提取
  5. 训练高斯或多项式朴素贝叶斯
  6. 保存模型与特征转换器

SVM (svm_train.py):
  1-5. 与朴素贝叶斯相同
  6. 使用 sklearn.svm.SVC 训练
  7. 支持 --kernel 选择 (linear/rbf/poly)

XGBoost (xgboost_train.py):
  1-5. 特征提取
  6. 使用 xgboost.XGBClassifier 训练
  7. 支持特征重要性可视化

LSTM (lstm_train.py):
  1. 加载数据集
  2. 使用 Word2Vec 或 GloVe 生成词向量
  3. 序列化文本为向量序列
  4. 构建 LSTM 模型 (Embedding → LSTM → Dense)
  5. 训练与评估

BERT+分类头 (bert_train.py):
  1. 加载 BERT 预训练模型
  2. 添加分类头 (Dropout + Dense)
  3. 微调整个模型或仅微调顶层
  4. 使用 AdamW 优化器
  5. 保存微调结果
```

**使用示例**:

```bash
# 训练各模型
python bayes_train.py
python svm_train.py --kernel rbf --C 1.0
python xgboost_train.py --max_depth 6
python lstm_train.py --embedding_dim 100 --hidden_dim 64
python bert_train.py --epochs 3 --batch_size 32

# 评估
python evaluate.py --model xgboost --test_file data/weibo2018/test.txt
```

### 5. WeiboSentiment_SmallQwen — 小规模Qwen模型

**目的**: 使用精量化或蒸馏后的Qwen模型进行轻量级情感分析

**特点**: 
- 模型体积小，部署简便
- 推理速度快
- 可在CPU或低端GPU上运行

## 核心设计模式

### 1. 单卡GPU锁定

所有脚本都采用统一的GPU管理机制：

```python
# 在导入 torch/transformers 之前执行
def _extract_gpu_arg(argv, default="0"):
    for i, arg in enumerate(argv):
        if arg.startswith("--gpu="):
            return arg.split("=", 1)[1]
        if arg == "--gpu" and i + 1 < len(argv):
            return argv[i + 1]
    return default

# 锁定单卡，避免多卡冲突
os.environ["CUDA_VISIBLE_DEVICES"] = gpu_to_use
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ.pop("RANK", None)
os.environ.pop("LOCAL_RANK", None)
os.environ.pop("WORLD_SIZE", None)
```

**优势**:
- 避免意外的多卡/分布式启动
- 支持 `--gpu 0` 或 `--gpu=1` 两种参数格式
- 稳定性高

### 2. 本地模型缓存与三段式加载

```python
def ensure_base_model_local(model_name, local_root):
    # 段式1：本地缓存检查
    if os.path.isdir(local_path):
        return load_from_local(local_path)
    
    # 段式2：Hugging Face 离线缓存
    try:
        return load_from_hf_cache(model_name, local_files_only=True)
    except:
        pass
    
    # 段式3：远程下载
    model = download_from_huggingface(model_name)
    save_to_local(model, local_path)
    return model
```

**优势**:
- 支持离线推理
- 减少重复下载
- 灵活的模型管理

### 3. 交互式参数选择

训练脚本支持交互式选择基座模型或其他超参数：

```python
# 非交互环境下跳过询问
if os.environ.get("NON_INTERACTIVE") == "1":
    return default_value

# 交互环境下允许用户选择
if sys.stdin.isatty():
    choice = input("请选择模型 (1-8) 或直接输入模型ID: ")
    return map_choice_to_model_id(choice)
```

## 主要类与函数

### BertTopicDetection_Finetuned

**predict.py**:
- `preprocess_text(text: str) -> str`: 文本预处理
- `ensure_base_model_local(model_name, local_root) -> Tuple[str, AutoTokenizer]`: 模型加载与缓存管理
- `load_finetuned(model_root, subdir) -> Tuple[str, Dict]`: 加载微调模型
- `predict_topk(model, tokenizer, device, text, max_length, top_k) -> List[Tuple[str, float]]`: Top-K 预测

**train.py**:
- `prompt_backbone_interactive(current_id: str) -> str`: 交互式基座模型选择
- `CustomDataset(Dataset)`: 自定义数据集类
- `compute_metrics(eval_pred)`: 评估指标计算
- 主训练循环使用 Hugging Face Trainer

### WeiboMultilingualSentiment

**predict.py**:
- `preprocess_text(text)`: 多语言文本预处理
- `main()`: 交互式预测主循环
- `show_multilingual_demo(tokenizer, model, device, sentiment_map)`: 多语言示例展示

## 推理流程（通用）

```
预处理 (preprocess_text)
  ↓
分词编码 (tokenizer)
  - max_length: 根据模型调整 (128-512)
  - padding: max_length 或 longest
  - truncation: True
  - return_tensors: "pt"
  ↓
转移到设备 (device)
  - GPU: cuda:0
  - CPU: cpu
  ↓
前向推理 (model.forward)
  - 禁用梯度: with torch.no_grad()
  - 输出: logits (batch_size, num_classes)
  ↓
后处理
  - Softmax → 概率分布
  - Argmax → 预测标签
  - Top-K → 候选结果
  ↓
格式化输出
  - 标签名称
  - 置信度分数
```

## 配置项与环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `CUDA_VISIBLE_DEVICES` | 可见GPU列表 | 由 `--gpu` 参数决定 |
| `NON_INTERACTIVE` | 非交互模式 | 0 (交互) |
| `TOKENIZERS_PARALLELISM` | tokenizer并行化 | false |

**示例**:

```bash
# 指定 GPU 0
python predict.py --gpu 0

# 非交互模式（CI/CD）
NON_INTERACTIVE=1 python train.py

# 指定模型缓存路径
python predict.py --model_root /custom/model/path
```

## 使用示例

### 话题分类

```python
from SentimentAnalysisModel.BertTopicDetection_Finetuned.predict import predict_topk
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# 加载模型
tokenizer = AutoTokenizer.from_pretrained("bert-finetuned/")
model = AutoModelForSequenceClassification.from_pretrained("bert-finetuned/")
device = torch.device("cuda")
model.to(device)

# 预测
text = "深度学习技术在计算机视觉中的应用"
results = predict_topk(model, tokenizer, device, text, top_k=3)

for rank, (topic, confidence) in enumerate(results, 1):
    print(f"{rank}. {topic} ({confidence:.4f})")
```

### 情感分析（多语言）

```bash
python WeiboMultilingualSentiment/predict.py

# 输入
请输入文本: Excellent product! Highly recommended!
预测结果: 非常正面 (置信度: 0.9723)

# 输入
请输入文本: 产品质量真差，非常失望
预测结果: 非常负面 (置信度: 0.9654)
```

### 传统机器学习

```bash
# 训练
python WeiboSentiment_MachineLearning/xgboost_train.py --epochs 100

# 评估
python WeiboSentiment_MachineLearning/evaluate.py --model xgboost
```

## 常见问题与故障排查

### 1. 模型下载失败

**症状**: "Connection timeout" 或 "Failed to download"

**原因**: Hugging Face 服务器不可达或网络问题

**解决**:
- 检查网络连接
- 使用代理: `HF_ENDPOINT=https://hf-mirror.com python predict.py`
- 提前手动下载模型到本地

### 2. GPU 内存不足

**症状**: "CUDA out of memory"

**解决**:
- 减少 `batch_size`
- 减少 `max_length`
- 使用 LoRA/Adapter 等参数高效方法
- 使用 CPU 推理: `python predict.py --device cpu`

### 3. 模型精度下降

**症状**: 预测结果准确率低于预期

**原因**: 
- 输入文本与训练数据分布不同
- 模型需要再次微调
- 超参数设置不优

**解决**:
- 收集更多相关数据进行微调
- 调整模型超参数
- 尝试不同的基座模型

### 4. 推理速度慢

**症状**: 单条推理耗时 > 1秒

**优化**:
- 批量推理而非单条
- 使用 ONNX 模型加速
- 考虑更轻量级的模型（SmallQwen）
- 启用 GPU 推理

## 与其他模块的集成

- **InsightEngine**: 使用情感分析模型对舆情数据进行情感评分
- **MediaEngine**: 对媒体文章进行情感倾向分析
- **QueryEngine**: 对查询结果的情感分类
- **ReportEngine**: 在报告中嵌入情感分析结果

## 扩展建议 / 下一步

1. **跨语言微调**: 基于多语言模型进行语言对微调
2. **方面级情感分析**: 识别特定方面的情感（例如"产品质量"、"售后服务"）
3. **情感强度预测**: 不仅分类，还预测情感强度 (0-10)
4. **模型蒸馏**: 将大模型压缩为更小的学生模型
5. **ONNX 优化**: 导出为 ONNX 格式实现跨平台推理加速
6. **量化部署**: INT8 量化减少模型体积与推理延迟
7. **知识蒸馏**: 使用强大的 LLM 生成伪标签进行无监督微调

## 文件实现参考

- `BertTopicDetection_Finetuned/` — 话题分类（BERT微调）
- `WeiboMultilingualSentiment/` — 多语言情感分析
- `WeiboSentiment_Finetuned/` — 微博情感分析（LoRA/Adapter微调）
- `WeiboSentiment_MachineLearning/` — 传统ML方法（贝叶斯/SVM/XGBoost/LSTM/BERT）
- `WeiboSentiment_SmallQwen/` — 轻量级Qwen模型

---

如果你希望我详细讲解某个特定模型的实现、提供批量推理脚本、或展示模型集成示例，我可以继续完善本文档。
