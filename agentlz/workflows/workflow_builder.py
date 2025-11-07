import os
import sys
import time
import asyncio

from langchain.chat_models import init_chat_model
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from agentlz.config.settings import settings
from agentlz.tools.mcp_config_tool import get_mcp_config_by_keyword

class FlowBuilderClient:
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

    # 顶层暴露正式API
    
def build_workflow_chain(user_input: str):
        model = init_chat_model(
            model=settings.MODEL_NAME,
            base_url=settings.MODEL_BASE_URL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.1
        )
        system_prompt = """
        你是一个流程编排大师，根据任务要求编排MCP工具链并输出流程链。
        请以JSON格式输出，包含：
        - execution_chain: agent名称列表
        - mcp_config: 每个agent的装配信息（字典）
        示例：
        {
          "execution_chain": ["math_agent", "language_agent"],
          "mcp_config": {
            "math_agent": {...},
            "language_agent": {...}
          }
        }
        """
        tools = [get_mcp_config_by_keyword]
        agent = create_agent(model, tools, system_prompt=system_prompt)
        response = agent.invoke({
            "messages": [{"role": "user", "content": user_input}]
        })
        return response["messages"][-1].content
    
    # 清理无关测试代码和多余内容，确保只暴露正式API


