import os
import sys
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from mcp.server.fastmcp import FastMCP
from langchain.agents import create_agent

# 环境变量由 settings.py 统一管理，这里仅做引用
from agentlz.config.settings import settings

# 创建MCP服务器
mcp = FastMCP("LanguageAgent")

language_stats = {
    "total_requests": 0,
    "last_input": "",
    "last_output": ""
}

@mcp.tool()
async def language(num: str) -> str:
    """将数字结果转化为有趣双关的描述 - 添加追踪"""
    language_stats["total_requests"] += 1
    language_stats["last_input"] = num
    print(f" [LanguageAgent] 开始语言处理，输入: {num}")
    try:
        model = init_chat_model(
            model=settings.MODEL_NAME,
            base_url=settings.MODEL_BASE_URL,
            api_key=settings.OPENAI_API_KEY
        )
        system_prompt = """
          你是一个双关专家。将数学结果转化为有趣、生动的故事。
          专注于创意表达和语言润色。
          """
        agent = create_agent(model, [], system_prompt=system_prompt)
        prompt = f"""
          请将这些数字结果转化为一段有趣的话: {num}
          要求:
          1. 创作一个简短有趣的故事
          2. 包含数字的变换过程
          3. 结尾要有寓意或感悟
          4. 语言生动有趣
          """
        result = await agent.ainvoke({
            "messages": [HumanMessage(content=prompt)]
        })
        output = result["messages"][-1].content
        language_stats["last_output"] = output[:200] + "..." if len(output) > 200 else output
        print(f"[LanguageAgent] 语言处理完成，输出长度: {len(output)}")
        return output
    except Exception as e:
        print(f" [LanguageAgent] 语言处理失败: {e}")
        return f"语言处理错误: {str(e)}"

@mcp.tool()
async def get_language_stats() -> dict:
    """获取语言处理统计"""
    return language_stats

if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
    mcp.run(transport="stdio")