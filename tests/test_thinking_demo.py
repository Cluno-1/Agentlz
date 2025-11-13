"""
思考过程演示测试 - 测试流式获取和区分OpenAI模型的思考过程

该测试文件：
1. 可以直接运行，无需相对导入
2. 提供完整的错误处理
3. 包含详细的测试用例
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from agentlz.config.settings import get_settings
    from agentlz.core.model_factory import get_model
    from agentlz.tools.streaming_processor import StreamingProcessor, create_thinking_prompt
    from agentlz.core.logger import setup_logging
    from langchain_core.messages import HumanMessage
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保已安装所有依赖: pip install -r requirements.txt")
    sys.exit(1)


class ThinkingDemoTest:
    """
    思考过程演示测试类
    
    参数:
        None
        
    属性:
        settings: 应用配置
        logger: 日志记录器
        processor: 流式处理器
    """
    
    def __init__(self):
        """初始化测试类"""
        try:
            self.settings = get_settings()
            self.logger = setup_logging(self.settings.log_level)
            self.processor = StreamingProcessor()
            self.logger.info("思考过程演示测试初始化成功")
        except Exception as e:
            print(f"初始化失败: {e}")
            raise
    
    async def test_stream_thinking_response(self, query: str) -> dict:
        """
        测试流式获取思考过程响应
        
        参数:
            query: 用户查询字符串
            
        返回值:
            dict: 包含测试结果的字典
            
        异常:
            可能抛出模型调用或流式处理相关的异常
        """
        try:
            # 获取流式模型
            model = get_model(self.settings, streaming=True)
            if not model:
                return {
                    "success": False,
                    "error": "模型配置无效，无法创建模型实例",
                    "query": query
                }
            
            # 创建包含思考过程要求的提示词
            prompt = create_thinking_prompt(query)
            
            # 准备消息
            messages = [HumanMessage(content=prompt)]
            
            # 收集流式响应的变量
            thinking_chunks = []
            answer_chunks = []
            all_chunks = []
            
            # 定义chunk处理回调
            async def process_chunk(chunk: str):
                all_chunks.append(chunk)
                
                # 实时分类内容类型
                content_type = self.processor.classify_content_type(chunk)
                
                if content_type == self.processor.ContentType.THINKING:
                    thinking_chunks.append(chunk)
                elif content_type == self.processor.ContentType.FINAL_ANSWER:
                    answer_chunks.append(chunk)
            
            # 调用流式模型
            response_stream = model.astream(messages)
            
            # 处理流式响应
            thinking_process, final_answer = await self.processor.process_streaming_response(
                response_stream, process_chunk
            )
            
            # 如果没有从流式处理中提取到内容，尝试从完整响应中提取
            full_response = ''.join(all_chunks)
            if not thinking_process or not final_answer:
                structured = self.processor.extract_structured_response(full_response)
                thinking_process = structured['thinking_process'] or thinking_process
                final_answer = structured['final_answer'] or final_answer
            
            return {
                "success": True,
                "query": query,
                "thinking_process": thinking_process,
                "final_answer": final_answer,
                "thinking_chunks_count": len(thinking_chunks),
                "answer_chunks_count": len(answer_chunks),
                "total_chunks": len(all_chunks),
                "has_thinking": bool(thinking_process),
                "has_answer": bool(final_answer)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "query": query
            }
    
    async def test_basic_response(self, query: str) -> dict:
        """
        测试基本响应（非流式）
        
        参数:
            query: 用户查询字符串
            
        返回值:
            dict: 包含测试结果的字典
        """
        try:
            # 获取普通模型
            model = get_model(self.settings, streaming=False)
            if not model:
                return {
                    "success": False,
                    "error": "模型配置无效",
                    "query": query
                }
            
            # 创建提示词
            prompt = create_thinking_prompt(query)
            messages = [HumanMessage(content=prompt)]
            
            # 调用模型
            response = model.invoke(messages)
            
            # 提取内容
            if hasattr(response, 'content'):
                content = response.content
            else:
                content = str(response)
            
            # 提取结构化响应
            structured = self.processor.extract_structured_response(content)
            
            return {
                "success": True,
                "query": query,
                "thinking_process": structured['thinking_process'],
                "final_answer": structured['final_answer'],
                "response_length": len(content),
                "has_thinking": bool(structured['thinking_process']),
                "has_answer": bool(structured['final_answer'])
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "query": query
            }


async def run_demo_tests():
    """运行演示测试"""
    print("=== 思考过程演示测试 ===\n")
    
    try:
        test = ThinkingDemoTest()
        print("✅ 测试初始化成功")
    except Exception as e:
        print(f"❌ 测试初始化失败: {e}")
        return
    
    # 测试查询列表
    test_queries = [
        "如何计算圆的面积？",
        "请解释人工智能的基本概念",
        "帮我制定一个学习计划",
        "什么是机器学习？"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n--- 测试 {i}: {query} ---")
        
        # 测试流式响应
        print("🔄 测试流式响应...")
        stream_result = await test.test_stream_thinking_response(query)
        
        if stream_result["success"]:
            print("✅ 流式测试成功")
            print(f"   思考过程: {'有' if stream_result['has_thinking'] else '无'}")
            print(f"   最终答案: {'有' if stream_result['has_answer'] else '无'}")
            print(f"   区块统计: 思考{stream_result['thinking_chunks_count']}, 答案{stream_result['answer_chunks_count']}")
            
            if stream_result['thinking_process']:
                print(f"   📝 思考内容: {stream_result['thinking_process'][:100]}...")
            if stream_result['final_answer']:
                print(f"   💡 最终答案: {stream_result['final_answer'][:100]}...")
        else:
            print(f"❌ 流式测试失败: {stream_result['error']}")
        
        # 测试基本响应
        print("📋 测试基本响应...")
        basic_result = await test.test_basic_response(query)
        
        if basic_result["success"]:
            print("✅ 基本测试成功")
            print(f"   响应长度: {basic_result['response_length']} 字符")
            print(f"   思考过程: {'有' if basic_result['has_thinking'] else '无'}")
            print(f"   最终答案: {'有' if basic_result['has_answer'] else '无'}")
        else:
            print(f"❌ 基本测试失败: {basic_result['error']}")
        
        print("-" * 50)
    
    print("\n=== 测试完成 ===")


def check_environment():
    """检查环境配置"""
    print("🔍 检查环境配置...")
    
    # 检查环境变量文件
    env_file = project_root / ".env"
    if env_file.exists():
        print("✅ .env 文件存在")
    else:
        print("⚠️  .env 文件不存在，请复制 .env.example 并配置API密钥")
    
    # 检查设置
    try:
        settings = get_settings()
        has_openai_key = bool(settings.openai_api_key)
        has_custom_key = bool(settings.chatopenai_api_key)
        
        print(f"🔑 OpenAI API密钥: {'已配置' if has_openai_key else '未配置'}")
        print(f"🔑 自定义API密钥: {'已配置' if has_custom_key else '未配置'}")
        print(f"🤖 模型名称: {settings.model_name}")
        
        if not has_openai_key and not has_custom_key:
            print("❌ 错误: 没有配置任何API密钥")
            return False
            
    except Exception as e:
        print(f"❌ 配置检查失败: {e}")
        return False
    
    return True


if __name__ == "__main__":
    # 检查环境
    if not check_environment():
        print("\n请先配置环境:")
        print("1. 复制 .env.example 为 .env")
        print("2. 在 .env 中配置 OPENAI_API_KEY 或 CHATOPENAI_API_KEY")
        print("3. 重新运行测试")
        sys.exit(1)
    
    # 运行测试
    try:
        asyncio.run(run_demo_tests())
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"\n测试运行错误: {e}")
        print("\n调试建议:")
        print("1. 检查API密钥是否正确")
        print("2. 检查网络连接")
        print("3. 查看详细错误信息")
        import traceback
        traceback.print_exc()