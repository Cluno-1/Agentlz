import os
import sys
import time
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from agentlz.config.settings import settings

class OptimizedMCPClient:
    def __init__(self, servers_config):
        self.client = MultiServerMCPClient(servers_config)
        self._tools_cache = None
        self._last_tool_refresh = 0
        self._cache_ttl = 60
    async def get_tools_cached(self):
        current_time = time.time()
        if (self._tools_cache is None or current_time - self._last_tool_refresh > self._cache_ttl):
            print("🔄 刷新工具缓存...")
            self._tools_cache = await self.client.get_tools()
            self._last_tool_refresh = current_time
            print(f"✅ 缓存更新，获取到 {len(self._tools_cache)} 个工具")
        else:
            print(f"💾 使用缓存工具，剩余TTL: {self._cache_ttl - (current_time - self._last_tool_refresh):.1f}秒")
        return self._tools_cache

async def simple_test_optimized():
    print("=" * 50)
    print("🤖 开始优化测试 - 减少频繁MCP调用")
    print("=" * 50)
    client = OptimizedMCPClient({
        "math_agent": {
            "transport": "stdio",
            "command": "python",
            "args": [os.path.join(os.path.dirname(__file__), "..", "agents", "math_agent.py")]
        },
        "language_agent": {
            "transport": "stdio",
            "command": "python",
            "args": [os.path.join(os.path.dirname(__file__), "..", "agents", "language_agent.py")]
        }
    })
    tools = await client.get_tools_cached()
    print(f"🛠️ 总工具数: {len(tools)}")
    model = ChatOpenAI(
        model=settings.MODEL_NAME,
        base_url=settings.MODEL_BASE_URL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0.1
    )
    system_prompt = """
    你是一个流程编排大师，根据任务要求编排MCP工具链并输出流程链
    """
    agent = create_agent(model, tools, system_prompt=system_prompt)
    user_input = "请根据原始数字进行两次平方和一次与原始数字的相加，输出一段有趣的话，初始输入：3"
    print(f"\n🎯 用户输入: {user_input}")
    print("⏳ 开始处理...")
    start_time = time.time()
    response = await agent.ainvoke({
        "messages": [{"role": "user", "content": user_input}]
    })
    end_time = time.time()
    processing_time = end_time - start_time
    print(f"\n✅ 处理完成，耗时: {processing_time:.2f}秒")
    print("📝 回答:")
    print("-" * 40)
    print(response["messages"][-1].content)
    print("-" * 40)
    try:
        stats_tools = [tool for tool in tools if "stats" in tool.name.lower()]
        if stats_tools:
            for stats_tool in stats_tools:
                stats_result = await stats_tool.ainvoke({})
                print(f"\n📊 {stats_tool.name} 统计:")
                print(stats_result)
    except Exception as e:
        print(f"⚠️ 获取统计信息失败: {e}")

if __name__ == "__main__":
    asyncio.run(simple_test_optimized())