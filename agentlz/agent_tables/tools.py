"""Tools MCP Agents 可信度表。

每项示例结构：
{
  "id": "tool_mcp_1",
  "trust": 85,
  "type": "remote",  // "remote" 或 "local"
  "endpoint": "http://.../invoke", // type 为 remote 时必填
  "import_path": "agentlz.tools.email", // type 为 local 时必填
  "function_name": "send_email", // type 为 local 时必填
  "capabilities": ["search", "markdown", "weather"]  # 可选
}

默认空表：无可用 tools agent。
"""

from typing import Any, Dict, List


TOOLS_AGENTS: List[Dict[str, Any]] = [
    {
        "id": "send_email_local",
        "trust": 95,
        "type": "local",
        "import_path": "agentlz.tools.send_email",
        "function_name": "send_email",
        "capabilities": ["send_email"],
        "schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "收件人邮箱地址"},
                "body": {"type": "string", "description": "邮件正文内容"}
            },
            "required": ["to", "body"]
        }
    },
    {
        "id": "search_remote_mcp",
        "trust": 80,
        "type": "remote",
        "endpoint": "http://mcp.example.com/search/invoke",
        "capabilities": ["web_search"],
        "schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"}
            },
            "required": ["query"]
        }
    }
]