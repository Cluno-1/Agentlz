import os
import sys
import time
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from mcp.server.fastmcp import FastMCP
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient

from agentlz.config.settings import settings

# 创建MCP服务器
mcp = FastMCP("MathAgent")
call_stack = []
tool_usage_count = {}
math_client = MultiServerMCPClient({
    "math_mcp": {
        "transport": "stdio",
        "command": "python",
        "args": [os.path.join(os.path.dirname(__file__), "..", "tools", "math_tool.py")]
    }
})

@mcp.tool()
async def calculate(expression: str) -> str:
    """计算数学表达式 - 添加详细追踪"""
    call_id = f"calculate_{int(time.time() * 1000)}"
    call_stack.append({"id": call_id, "tool": "calculate", "input": expression, "timestamp": time.time()})
    print(f"🔍 [MathAgent] 开始执行 calculate('{expression}')")
    print(f"📊 当前调用栈深度: {len(call_stack)}")
    try:
        tool_usage_count["calculate"] = tool_usage_count.get("calculate", 0) + 1
        tools = await math_client.get_tools()
        print(f"🛠️  获取到 {len(tools)} 个数学工具")
        model = init_chat_model(
            model=settings.MODEL_NAME,
            base_url=settings.MODEL_BASE_URL,
            api_key=settings.OPENAI_API_KEY
        )
        system_prompt = """
        你是一个数学专家。将复杂问题分解为简单步骤，每次调用一个数学工具。
        请详细记录你的思考过程。
        """
        agent = create_agent(model, tools, system_prompt=system_prompt)
        result = await agent.ainvoke({
            "messages": [HumanMessage(content=f"计算: {expression}")]
        })
        final_result = result["messages"][-1].content
        print(f"✅ [MathAgent] 计算完成: {final_result[:100]}...")
        return final_result
    except Exception as e:
        print(f"❌ [MathAgent] 执行失败: {e}")
        return f"计算错误: {str(e)}"
    finally:
        call_stack.pop()
        print(f"🏁 [MathAgent] 调用完成，剩余调用栈: {len(call_stack)})")

@mcp.tool()
async def get_execution_stats() -> dict:
    """获取执行统计信息"""
    return {
        "total_calls": sum(tool_usage_count.values()),
        "tool_usage": tool_usage_count,
        "current_stack_depth": len(call_stack),
        "call_stack": call_stack[-5:]
    }

if __name__ == "__main__":
    print("🚀 MathAgent MCP服务器启动...")
    mcp.run(transport="stdio")