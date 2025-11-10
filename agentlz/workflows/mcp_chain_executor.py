import os
import asyncio
from langchain_core.runnables.config import P
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from agentlz.config.settings import settings
from agentlz.schemas.workflow import WorkflowPlan, MCPConfigItem


class MCPChainExecutor:
    def __init__(self, plan: WorkflowPlan):
        self.plan = plan
        self.client = None

    def assemble_mcp(self):
        # 将 WorkflowPlan.mcp_config 列表转换为 MultiServerMCPClient 需要的字典结构
        mcp_dict = {
            item.name: {
                "transport": item.transport,
                "command": item.command,
                "args": item.args,
            }
            for item in self.plan.mcp_config
        }
        self.client = MultiServerMCPClient(mcp_dict)

    async def execute_chain(self, input_data):
        """
        使用 MCP 工具集合创建 LangChain 代理并执行用户任务。
        说明：MultiServerMCPClient 不提供 get_agent；需通过 get_tools() 加载工具并交给代理使用。
        """
        self.assemble_mcp()
        try:
            tools = await self.client.get_tools()
            print("已加载工具:", tools)
            print("已加载client:", self.client)
        except Exception as e:
            print("❌ 加载 MCP 工具失败:", repr(e))
            print("已加载工具:", tools)
            print("已加载client:", self.client)
            raise
        # 将计划中的链路作为偏好提示传递给代理
        preferred_chain = ", ".join(self.plan.execution_chain) if self.plan.execution_chain else ""
        system_prompt = (
            "你是执行器，负责按需调用 MCP 工具完成任务。"
            + (f"优先按以下顺序使用工具/服务：{preferred_chain}。" if preferred_chain else "")
        )
        model = init_chat_model(
            model=settings.MODEL_NAME,
            base_url=settings.MODEL_BASE_URL,
            api_key=settings.DEEPSEEK_API_KEY,
            temperature=0.1,
        )
        agent = create_agent(model=model, tools=tools, system_prompt=system_prompt)
        user_content = input_data if isinstance(input_data, str) else str(input_data)
        try:
            response = await agent.ainvoke({"messages": [{"role": "user", "content": user_content}]})
        except Exception as e:
            print("❌ 代理执行失败:", repr(e))
            raise
        return response["messages"][-1].content if isinstance(response, dict) else response


# 示例用法（仅示例，实际项目可在 app 层调用）
async def main():
    from agentlz.workflows.workflow_builder import build_workflow_chain
    # 构建计划（返回 dataclass WorkflowPlan 或文本兜底）
    plan = build_workflow_chain("为数学求解和语言润色编排流程")
    if not isinstance(plan, WorkflowPlan):
        print("未获得结构化计划：", plan)
        return
    executor = MCPChainExecutor(plan)
    input_data = 3
    final_result = await executor.execute_chain(input_data)
    print("最终结果:", final_result)


if __name__ == "__main__":
    asyncio.run(main())
