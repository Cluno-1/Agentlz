from dataclasses import dataclass
from typing import List


@dataclass
class MCPConfigItem:
    """单个 MCP Agent 的装配配置项。"""
    name: str
    transport: str
    command: str
    args: List[str]


@dataclass
class WorkflowPlan:
    """MCP 工作流编排的结构化输出模型。"""
    execution_chain: List[str]
    mcp_config: List[MCPConfigItem]