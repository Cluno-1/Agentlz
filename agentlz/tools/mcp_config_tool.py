from langchain.tools import tool
from typing import List, Dict


@tool
def get_mcp_config_by_keyword(keyword: str) -> List[Dict[str, str | List[str]]]:
    """
    根据关键词返回 MCP agent 的装配信息（列表结构，与 WorkflowPlan.mcp_config 对齐）。
    :param keyword: 关键词（如“数学”、“语言”）
    :return: list[dict], 每项包含 name/transport/command/args
    """
    import os
    base_dir = os.path.dirname(__file__)

    def item(name: str, script: str) -> Dict[str, str | List[str]]:
        script_path = os.path.abspath(os.path.normpath(os.path.join(base_dir, "..", "agents", script)))
        return {
            "name": name,
            "transport": "stdio",
            "command": "python",
            "args": [script_path],
        }

    if keyword in ["数学", "math"]:
        return [item("math_agent", "math_agent.py")]
    elif keyword in ["语言", "language"]:
        return [item("language_agent", "language_agent.py")]
    else:
        # 默认返回两个 agent
        return [
            item("math_agent", "math_agent.py"),
            item("language_agent", "language_agent.py"),
        ]