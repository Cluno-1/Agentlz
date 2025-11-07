import asyncio
import json
from agentlz.workflows.workflow_builder import build_workflow_chain
from agentlz.workflows.mcp_chain_executor import MCPChainExecutor

def main():
    user_input = "请根据原始数字进行两次平方和一次与原始数字的相加，输出一段有趣的话，初始输入：3"
    print("开始流程编排...")
    chain_json = build_workflow_chain(user_input)
    print("编排结果：", chain_json)
    try:
        plan = json.loads(chain_json)
        execution_chain = plan.get("execution_chain")
        mcp_config = plan.get("mcp_config")
        if execution_chain and mcp_config:
            print("开始执行链路...")
            executor = MCPChainExecutor(mcp_config, execution_chain)
            input_data = 3
            loop = asyncio.get_event_loop()
            final_result = loop.run_until_complete(executor.execute_chain(input_data))
            print("最终结果:", final_result)
        else:
            print("编排结果格式错误！")
    except Exception as e:
        print("解析或执行出错：", e)

if __name__ == "__main__":
    main()