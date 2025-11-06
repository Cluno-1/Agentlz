from typing import List, Optional
from pydantic import BaseModel


class ThesisResponse(BaseModel):
    """论文获取响应结构"""
    title: str
    authors: List[str]
    abstract: str
    url: Optional[str] = None
    year: Optional[int] = None
    citations: Optional[int] = None


class PlanStep(BaseModel):
    """计划步骤结构"""
    step_number: int
    description: str
    agent_type: str
    status: str = "pending"  # pending, in_progress, completed
    result: Optional[dict] = None


class PlanResponse(BaseModel):
    """规划响应结构"""
    query: str
    steps: List[PlanStep]
    status: str = "pending"  # pending, in_progress, completed


class MultiAgentResponse(BaseModel):
    """多Agent响应结构"""
    query: str
    plan: PlanResponse
    final_result: Optional[dict] = None
    error: Optional[str] = None


class ScheduleResponse(BaseModel):
    """总调度 Agent（schedule_1_agent）响应结构"""
    query: str
    status: str  # no_plan_agents / missing_tools_or_checks / planned / executed
    selected_plan_agent_id: Optional[str] = None
    selected_tools_agent_ids: List[str] = []
    steps: Optional[List[PlanStep]] = None
    check_passed: Optional[bool] = None
    final_summary: Optional[str] = None
    error: Optional[str] = None