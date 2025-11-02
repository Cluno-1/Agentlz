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