import os
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient

class MCPChainExecutor:
    def __init__(self, mcp_config, execution_chain):
        self.mcp_config = mcp_config
        self.execution_chain = execution_chain
        self.client = None

    def assemble_mcp(self):
        # 装配 MCP 客户端
        self.client = MultiServerMCPClient(self.mcp_config)

    async def execute_chain(self, input_data):
        self.assemble_mcp()
        result = input_data
        for agent_name in self.execution_chain:
            print(f"调用 {agent_name}，输入: {result}")
            agent = self.client.get_agent(agent_name)
            # 假设每个 agent 都有 ainvoke 方法
            result = await agent.ainvoke({"input": result})
            print(f"{agent_name} 输出: {result}")
        return result
# 示例用法
async def main():
    # 假设从流程编排大师获取到如下信息
    from workflow_builder import get_mcp_config_by_keyword
    mcp_config = get_mcp_config_by_keyword("数学")
    execution_chain = ["math_agent", "language_agent"]
    executor = MCPChainExecutor(mcp_config, execution_chain)
    input_data = 3
    final_result = await executor.execute_chain(input_data)
    print("最终结果:", final_result)

if __name__ == "__main__":
    asyncio.run(main())
