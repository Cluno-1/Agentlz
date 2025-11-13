from __future__ import annotations
from typing import List, Optional, Dict, Any
from pydantic import BaseModel



class ToolResponse(BaseModel):
    """Tools Agent 的执行结果摘要"""
    status: str  # executed / retry_required / failed / skipped 等
    agent_id: Optional[str] = None  # 实际选用的 tools agent
    tool: Optional[str] = None  # 工具名或函数标识
    params: Dict[str, Any] = {}  # 入参
    output_text: Optional[str] = None  # 文本化输出（如日志、摘要）
    output_data: Optional[Dict[str, Any]] = None  # 结构化输出
    success: bool = False
    elapsed_ms: Optional[int] = None
    error: Optional[str] = None


class CheckResponse(BaseModel):
    """Check Agent 的校验结果"""
    status: str  # passed / failed / error 等
    agent_id: Optional[str] = None
    passed: bool = False
    reason: Optional[str] = None  # 通过/不通过的原因
    expected: Optional[str] = None  # 期望（目标/规则）
    observed: Optional[str] = None  # 实际（观察到的输出）
    score: Optional[float] = None  # 可选评分（0.0-1.0 或 0-100）
    error: Optional[str] = None


class AgentStep(BaseModel):
    """智能 Agent 的单步思考与行动"""
    thought: str  # Agent 在该步骤的思考过程
    tool: str  # Agent 决定使用的工具 (e.g., 'call_plan_agent', 'call_tool_agent')
    tool_input: Dict[str, Any]  # 调用工具时的输入参数
    tool_output: Optional[Dict[str, Any]] = None # 工具的原始输出
    observation: str  # Agent 对工具输出的观察和总结


class ScheduleResponse(BaseModel):
    """总调度 Agent（schedule_1_agent）响应结构"""
    query: str  # 用户的原始查询
    status: str  # final_answer / error
    intermediate_steps: List[AgentStep] = []  # Agent 的完整思考和行动路径
    final_summary: str  # 最终的、面向用户的回答
    error: Optional[str] = None