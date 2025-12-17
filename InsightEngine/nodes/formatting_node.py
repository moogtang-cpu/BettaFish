"""
报告格式化节点
负责将最终研究结果格式化为美观的Markdown报告
"""

import json
from typing import List, Dict, Any
from loguru import logger

from .base_node import BaseNode
from ..prompts import SYSTEM_PROMPT_REPORT_FORMATTING
from ..utils.text_processing import (
    remove_reasoning_from_output,
    clean_markdown_tags
)




class ReportFormattingNode(BaseNode):
    """格式化最终报告的节点"""
    
    def __init__(self, llm_client):
        """
        初始化报告格式化节点
        
        Args:
            llm_client: LLM客户端
        """
        super().__init__(llm_client, "ReportFormattingNode")
    
    def _is_valid_item(self, item: Any, index: int) -> bool:
        """
        验证单个数据项是否有效
        
        Args:
            item: 要验证的项目
            index: 项目索引
            
        Returns:
            项目是否有效
        """
        required_keys = {"title", "paragraph_latest_state"}
        
        if not isinstance(item, dict):
            logger.error(f"数据项 {index} 类型错误，期望dict，实际为{type(item).__name__}")
            return False
        
        missing_keys = required_keys - item.keys()
        if missing_keys:
            logger.error(f"数据项 {index} 缺少必需的键: {missing_keys}")
            return False
        
        return True
    
    def validate_input(self, input_data: Any) -> bool:
        """验证输入数据"""
        # 规范化输入数据
        data = input_data
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"JSON解析失败: {str(e)}")
                return False
        elif not isinstance(data, list):
            logger.error(f"输入类型错误，期望str或list，实际为{type(data).__name__}")
            return False
        
        # 验证数据格式
        if not data:
            logger.warning("输入数据为空列表")
            return False
        
        # 验证每个项目
        for i, item in enumerate(data):
            if not self._is_valid_item(item, i):
                return False
        
        return True
    
    def run(self, input_data: Any, **kwargs) -> str:
        """
        调用LLM生成Markdown格式报告
        
        Args:
            input_data: 包含所有段落信息的列表
            **kwargs: 额外参数
            
        Returns:
            格式化的Markdown报告
        """
        try:
            if not self.validate_input(input_data):
                raise ValueError("输入数据格式错误，需要包含title和paragraph_latest_state的列表")
            
            # 准备输入数据
            if isinstance(input_data, str):
                message = input_data
            else:
                message = json.dumps(input_data, ensure_ascii=False)
            
            logger.info("正在格式化最终报告")
            
            # 调用LLM（流式，安全拼接UTF-8）
            response = self.llm_client.stream_invoke_to_string(
                SYSTEM_PROMPT_REPORT_FORMATTING,
                message,
            )
            
            # 处理响应
            processed_response = self.process_output(response)
            
            logger.info("成功生成格式化报告")
            return processed_response
            
        except Exception as e:
            logger.exception(f"报告格式化失败: {str(e)}")
            raise e
    
    def process_output(self, output: str) -> str:
        """
        处理LLM输出，清理Markdown格式
        
        Args:
            output: LLM原始输出
            
        Returns:
            清理后的Markdown报告
        """
        try:
            # 清理响应文本
            cleaned_output = remove_reasoning_from_output(output)
            cleaned_output = clean_markdown_tags(cleaned_output)
            
            # 确保报告有基本结构
            if not cleaned_output.strip():
                return "# 报告生成失败\n\n无法生成有效的报告内容。"
            
            # 如果没有标题，添加一个默认标题
            if not cleaned_output.strip().startswith('#'):
                cleaned_output = "# 深度研究报告\n\n" + cleaned_output
            
            return cleaned_output.strip()
            
        except Exception as e:
            logger.exception(f"处理输出失败: {str(e)}")
            return "# 报告处理失败\n\n报告格式化过程中发生错误。"
    
    def format_report_manually(self, paragraphs_data: List[Dict[str, str]], 
                             report_title: str = "深度研究报告") -> str:
        """
        手动格式化报告（备用方法）
        
        Args:
            paragraphs_data: 段落数据列表
            report_title: 报告标题
            
        Returns:
            格式化的Markdown报告
        """
        try:
            logger.info("使用手动格式化方法")
            
            # 构建报告
            report_lines = [
                f"# {report_title}",
                "",
                "---",
                ""
            ]
            
            # 添加各个段落
            for i, paragraph in enumerate(paragraphs_data, 1):
                title = paragraph.get("title", f"段落 {i}")
                content = paragraph.get("paragraph_latest_state", "")
                
                if content:
                    report_lines.extend([
                        f"## {title}",
                        "",
                        content,
                        "",
                        "---",
                        ""
                    ])
            
            # 添加结论
            if len(paragraphs_data) > 1:
                report_lines.extend([
                    "## 结论",
                    "",
                    "本报告通过深度搜索和研究，对相关主题进行了全面分析。"
                    "以上各个方面的内容为理解该主题提供了重要参考。",
                    ""
                ])
            
            return "\n".join(report_lines)
            
        except Exception as e:
            logger.exception(f"手动格式化失败: {str(e)}")
            return "# 报告生成失败\n\n无法完成报告格式化。"
