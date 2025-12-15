# utils/__init__.py 文件分析

该 `__init__.py` 文件在 `InsightEngine/utils` 子目录中扮演着包初始化和接口聚合的角色。

### 业务逻辑分析

1.  **包声明**: 此文件将 `utils` 文件夹声明为一个 Python 包，使得其中定义的辅助工具函数可以被系统地组织和导入。

2.  **内容聚合与导出**:
    - 该文件的核心作用是从同级目录的 `text_processing.py` 文件中导入了各种与文本处理和格式化相关的工具函数（例如 `clean_json_tags`, `clean_markdown_tags`, `remove_reasoning_from_output` 等）。
    - 通过 `__all__` 列表，它将这些导入的函数定义为 `utils` 包的公共 API。

### 总结

这个文件的主要目的在于**简化工具函数的外部调用和封装内部结构**。

`DeepSearchAgent` 中的各个节点或其他模块在需要进行文本清理、格式化或数据提取时，可以直接通过 `from InsightEngine.utils import clean_json_tags` 等方式，方便地从 `utils` 包中获取到它们所需的工具函数，而无需关心这些函数具体定义在 `utils` 包下的哪个文件中。

这种设计模式提高了代码的模块化和可维护性。它为 `InsightEngine` 的通用辅助功能提供了一个清晰、统一的访问点。
