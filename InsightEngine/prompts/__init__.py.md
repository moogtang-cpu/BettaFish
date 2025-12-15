# prompts/__init__.py 文件分析

该 `__init__.py` 文件在 `InsightEngine/prompts` 子目录中扮演着包初始化和接口聚合的角色。

### 业务逻辑分析

1.  **包声明**: 此文件将 `prompts` 文件夹声明为一个 Python 包，使得其中定义的提示词可以被系统地组织和导入。

2.  **内容聚合与导出**:
    - 该文件的核心作用是从同级目录的 `prompts.py` 文件中导入所有预定义的系统提示词（以 `SYSTEM_PROMPT_` 开头的变量）和相关的输出/输入 JSON 模式（以 `output_schema_` 或 `input_schema_` 开头的变量）。
    - 通过 `__all__` 列表，它将这些导入的常量定义为 `prompts` 包的公共 API。

### 总结

这个文件的主要目的在于**简化提示词的外部调用和封装内部结构**。

`DeepSearchAgent` 中的各个节点在与 LLM 交互时，可以直接通过 `from .prompts import SYSTEM_PROMPT_FIRST_SEARCH` 等方式，方便地从 `prompts` 包中获取到它们所需的提示词和结构定义，而无需关心这些提示词具体定义在 `prompts` 包下的哪个文件中。

这种设计模式提高了代码的模块化和可维护性。它为 `InsightEngine` 的核心智能逻辑（LLM 的行为指导）提供了一个清晰、统一的访问点。
