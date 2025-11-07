from langchain.tools import tool

@tool
def get_mcp_config_by_keyword(keyword: str) -> dict:
    """
    根据关键词返回 MCP agent 的装配信息。
    :param keyword: str, 关键词（如“数学”、“语言”）
    :return: dict, MCP agent 配置信息
    """
    import os
    if keyword in ["数学", "math"]:
        return {
            "math_agent": {
                "transport": "stdio",
                "command": "python",
                "args": [os.path.join(os.path.dirname(__file__), "..", "agents", "math_agent.py")]
            }
        }
    elif keyword in ["语言", "language"]:
        return {
            "language_agent": {
                "transport": "stdio",
                "command": "python",
                "args": [os.path.join(os.path.dirname(__file__), "..", "agents", "language_agent.py")]
            }
        }
    else:
        # 默认返回两个agent
        return {
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
        }