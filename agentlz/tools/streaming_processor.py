"""
流式处理工具 - 用于处理OpenAI模型的思考过程和最终结果分离

该模块提供功能：
1. 流式获取模型响应
2. 分离思考过程和最终答案
3. 支持不同的输出格式
"""

import re
from typing import AsyncIterator, Dict, List, Optional, Tuple
from enum import Enum


class ContentType(Enum):
    """内容类型枚举"""
    THINKING = "thinking"
    FINAL_ANSWER = "final_answer"
    UNKNOWN = "unknown"


class StreamingProcessor:
    """
    流式处理器 - 处理模型响应的思考过程和最终结果
    
    参数:
        None
        
    属性:
        thinking_pattern: 思考过程的正则表达式模式
        answer_pattern: 最终答案的正则表达式模式
    """
    
    def __init__(self):
        # 定义思考过程和最终答案的模式
        self.thinking_pattern = re.compile(r'\[思考开始\](.*?)\[思考结束\]', re.DOTALL)
        self.answer_pattern = re.compile(r'\[最终回答\](.*?)\[回答结束\]', re.DOTALL)
    
    async def process_streaming_response(
        self, 
        response_stream: AsyncIterator,
        chunk_callback: Optional[callable] = None
    ) -> Tuple[str, str]:
        """
        处理流式响应，分离思考过程和最终答案
        
        参数:
            response_stream: 异步迭代器，模型流式响应
            chunk_callback: 可选的回调函数，处理每个chunk
            
        返回值:
            Tuple[str, str]: (思考过程, 最终答案)
            
        异常:
            可能抛出异步迭代相关的异常
        """
        full_response = ""
        thinking_content = ""
        final_answer = ""
        
        try:
            async for chunk in response_stream:
                if hasattr(chunk, 'content'):
                    content = chunk.content
                else:
                    content = str(chunk)
                
                full_response += content
                
                # 调用回调函数处理每个chunk
                if chunk_callback:
                    await chunk_callback(content)
                
                # 实时尝试提取思考过程和最终答案
                thinking_match = self.thinking_pattern.search(full_response)
                answer_match = self.answer_pattern.search(full_response)
                
                if thinking_match:
                    thinking_content = thinking_match.group(1).strip()
                if answer_match:
                    final_answer = answer_match.group(1).strip()
        
        except Exception as e:
            # 如果流式处理出错，尝试从完整响应中提取
            thinking_match = self.thinking_pattern.search(full_response)
            answer_match = self.thinking_pattern.search(full_response)
            
            if thinking_match:
                thinking_content = thinking_match.group(1).strip()
            if answer_match:
                final_answer = answer_match.group(1).strip()
        
        # 如果没有匹配到模式，返回完整响应作为最终答案
        if not thinking_content and not final_answer:
            final_answer = full_response.strip()
        elif not final_answer and thinking_content:
            # 只有思考过程，没有最终答案
            final_answer = "思考完成，请查看思考过程获取详细分析"
        
        return thinking_content, final_answer
    
    def classify_content_type(self, content: str) -> ContentType:
        """
        分类内容类型
        
        参数:
            content: 需要分类的内容字符串
            
        返回值:
            ContentType: 内容类型枚举值
        """
        if self.thinking_pattern.search(content):
            return ContentType.THINKING
        elif self.answer_pattern.search(content):
            return ContentType.FINAL_ANSWER
        else:
            return ContentType.UNKNOWN
    
    def extract_structured_response(self, full_response: str) -> Dict[str, str]:
        """
        从完整响应中提取结构化的思考过程和最终答案
        
        参数:
            full_response: 完整的模型响应字符串
            
        返回值:
            Dict[str, str]: 包含思考过程和最终答案的字典
        """
        thinking_match = self.thinking_pattern.search(full_response)
        answer_match = self.answer_pattern.search(full_response)
        
        result = {
            "thinking_process": thinking_match.group(1).strip() if thinking_match else "",
            "final_answer": answer_match.group(1).strip() if answer_match else "",
            "raw_response": full_response
        }
        
        return result


def create_thinking_prompt(user_query: str) -> str:
    """
    创建包含思考过程要求的提示词
    
    参数:
        user_query: 用户查询字符串
        
    返回值:
        str: 包含思考过程要求的完整提示词
    """
    from ..prompts.thinking_process import THINKING_PROCESS_PROMPT
    
    return f"{THINKING_PROCESS_PROMPT}\n\n用户查询: {user_query}"