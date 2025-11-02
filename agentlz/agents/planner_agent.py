from typing import Dict, Any, List

from langchain.agents import create_agent

from ..config.settings import get_settings
from ..core.model_factory import get_model
from ..prompts.templates import PLANNER_SYSTEM_PROMPT
from ..schemas.responses import PlanResponse, PlanStep


def build_planner_agent():
    """构建规划Agent"""
    settings = get_settings()
    model = get_model(settings)
    agent = create_agent(
        model=model,
        tools=[],  # 规划Agent通常不需要外部工具
        system_prompt=PLANNER_SYSTEM_PROMPT,
    )
    return agent


def create_execution_plan(query: str) -> PlanResponse:
    """创建执行计划
    
    Args:
        query: 用户的查询请求
        
    Returns:
        PlanResponse: 执行计划响应
    """
    agent = build_planner_agent()
    result: Dict[str, Any] = agent.invoke({"messages": [{"role": "user", "content": query}]})
    
    # 解析返回结果为PlanResponse对象
    if isinstance(result, dict):
        steps_data = result.get("steps", [])
        steps = [
            PlanStep(
                step_number=step.get("step_number"),
                description=step.get("description"),
                agent_type=step.get("agent_type"),
                status=step.get("status", "pending"),
                result=step.get("result")
            )
            for step in steps_data
        ]
        
        return PlanResponse(
            query=query,
            steps=steps,
            status="pending"
        )
    
    raise ValueError(f"Unexpected response format from planner agent: {result}")


def update_step_status(plan: PlanResponse, step_number: int, status: str, result: Dict[str, Any] = None) -> PlanResponse:
    """更新步骤状态
    
    Args:
        plan: 当前执行计划
        step_number: 要更新的步骤编号
        status: 新状态
        result: 执行结果（可选）
        
    Returns:
        PlanResponse: 更新后的执行计划
    """
    for step in plan.steps:
        if step.step_number == step_number:
            step.status = status
            if result:
                step.result = result
            break
    
    # 更新整体计划状态
    if all(step.status == "completed" for step in plan.steps):
        plan.status = "completed"
    elif any(step.status == "in_progress" for step in plan.steps):
        plan.status = "in_progress"
    
    return plan