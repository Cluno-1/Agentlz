import os
import sys
import time
import asyncio

from langchain.chat_models import init_chat_model
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from agentlz.config.settings import settings
from agentlz.tools.mcp_config_tool import get_mcp_config_by_keyword
from agentlz.schemas.workflow import WorkflowPlan

class FlowBuilderClient:
    def __init__(self, servers_config):
        self.client = MultiServerMCPClient(servers_config)
        self._tools_cache = None
        self._last_tool_refresh = 0
        self._cache_ttl = 120
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
            api_key=settings.DEEPSEEK_API_KEY,
            temperature=0.1
        )
        system_prompt = (
            "你是一个流程编排大师。根据用户输入规划 execution_chain 和 mcp_config，"
            "直接按响应格式输出，无需解释说明。"
            "必须根据任务需求选择合适的 MCP agent：涉及数学计算时包含 MathAgent；"
            "涉及写作、语言、双关、表达或润色时，需在链路末尾加入 LanguageAgent。"
        )
        tools = [get_mcp_config_by_keyword]
        agent = create_agent(
            model=model,
            tools=tools,
            system_prompt=system_prompt,
            response_format=WorkflowPlan,
        )
        response = agent.invoke({
            "messages": [{"role": "user", "content": user_input}]
        })
        # 返回结构化响应（dataclass）；严格模式：无结构化响应直接抛错，便于定位问题
        if isinstance(response, dict) and response.get("structured_response") is not None:
            return response["structured_response"]
        raise ValueError(f"WorkflowPlan structured_response missing. Raw response: {response!r}")
    
    # 清理无关测试代码和多余内容，确保只暴露正式API


