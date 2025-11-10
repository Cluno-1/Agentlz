import asyncio
import json
from typing import Any, Dict, List
from agentlz.workflows.workflow_builder import build_workflow_chain
from agentlz.workflows.mcp_chain_executor import MCPChainExecutor
from agentlz.schemas.workflow import WorkflowPlan, MCPConfigItem

def main():
    user_input = "请根据原始数字进行两次平方和一次与原始数字的相加，运用双关语言输出一段有趣的话，初始输入：3"
    print("开始流程编排...")
    plan_or_text = build_workflow_chain(user_input)
    print("编排结果：", plan_or_text)
    try:
        # 首选使用结构化 dataclass
        if isinstance(plan_or_text, WorkflowPlan):
            plan = plan_or_text
        else:
            # 兼容旧路径：字符串或字典 -> 转换为 WorkflowPlan
            raw: Any = plan_or_text
            if isinstance(raw, str):
                raw = json.loads(raw)
            if isinstance(raw, dict):
                exec_chain = raw.get("execution_chain", [])
                mcp_items: List[Dict[str, Any]] = raw.get("mcp_config", [])
                plan = WorkflowPlan(
                    execution_chain=exec_chain,
                    mcp_config=[
                        MCPConfigItem(
                            name=item.get("name", ""),
                            transport=item.get("transport", "stdio"),
                            command=item.get("command", ""),
                            args=item.get("args", []),
                        )
                        for item in mcp_items
                    ],
                )
            else:
                raise TypeError("无法识别的编排结果类型")

        print("开始执行链路...")
        executor = MCPChainExecutor(plan)
        # 将原始用户意图作为执行输入，便于代理理解任务
        input_data = user_input
        final_result = asyncio.run(executor.execute_chain(input_data))
        print("最终结果:", final_result)
    except Exception as e:
        print("解析或执行出错：", e)

if __name__ == "__main__":
    main()