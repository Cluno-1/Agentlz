from typing import Dict, Any, Optional

from langchain.agents import create_agent

from ..config.settings import get_settings
from ..core.model_factory import get_model
from ..core.logger import setup_logging
from ..prompts.templates import MULTI_AGENT_SYSTEM_PROMPT
from ..schemas.responses import MultiAgentResponse, PlanResponse
from .planner_agent import create_execution_plan, update_step_status
from .thesis_agent import get_thesis_info


class MultiAgent:
    """多Agent系统的总控制器"""
    
    def __init__(self):
        settings = get_settings()
        self.model = get_model(settings)
        self.logger = setup_logging(settings.log_level)
        self.agent = create_agent(
            model=self.model,
            tools=[],  # 总控制器使用其他Agent而不是直接使用工具
            system_prompt=MULTI_AGENT_SYSTEM_PROMPT,
        )
    
    def _execute_thesis_agent(self, query: str) -> Dict[str, Any]:
        """执行论文检索Agent"""
        try:
            result = get_thesis_info(query)
            return result.model_dump()
        except Exception as e:
            self.logger.error(f"Thesis agent execution failed: {str(e)}")
            raise
    
    def _execute_step(self, step: Dict[str, Any], plan: PlanResponse) -> Optional[Dict[str, Any]]:
        """执行单个步骤
        
        Args:
            step: 步骤信息
            plan: 当前执行计划
            
        Returns:
            Dict[str, Any]: 步骤执行结果
        """
        step_number = step["step_number"]
        agent_type = step["agent_type"]
        
        # 更新步骤状态为进行中
        plan = update_step_status(plan, step_number, "in_progress")
        
        try:
            # 根据Agent类型执行相应的操作
            if agent_type == "thesis":
                result = self._execute_thesis_agent(step.get("description", ""))
            else:
                raise ValueError(f"Unknown agent type: {agent_type}")
            
            # 更新步骤状态为完成
            plan = update_step_status(plan, step_number, "completed", result)
            return result
            
        except Exception as e:
            self.logger.error(f"Step {step_number} execution failed: {str(e)}")
            plan = update_step_status(plan, step_number, "error", {"error": str(e)})
            raise
    
    def execute(self, query: str) -> MultiAgentResponse:
        """执行多Agent任务
        
        Args:
            query: 用户查询
            
        Returns:
            MultiAgentResponse: 多Agent执行结果
        """
        try:
            # 1. 创建执行计划
            plan = create_execution_plan(query)
            
            # 2. 按顺序执行每个步骤
            final_result = {}
            for step in plan.steps:
                step_result = self._execute_step(step.model_dump(), plan)
                if step_result:
                    final_result[f"step_{step.step_number}"] = step_result
            
            # 3. 返回最终结果
            return MultiAgentResponse(
                query=query,
                plan=plan,
                final_result=final_result
            )
            
        except Exception as e:
            self.logger.error(f"Multi-agent execution failed: {str(e)}")
            return MultiAgentResponse(
                query=query,
                plan=plan if 'plan' in locals() else None,
                error=str(e)
            )


def ask(query: str) -> str:
    """处理用户查询的入口函数
    
    Args:
        query: 用户查询
        
    Returns:
        str: 格式化的响应结果
    """
    agent = MultiAgent()
    result = agent.execute(query)
    
    # 如果发生错误，返回错误信息
    if result.error:
        return f"执行出错: {result.error}"
    
    # 格式化输出结果
    output = []
    output.append(f"查询: {result.query}")
    output.append("\n执行计划:")
    
    for step in result.plan.steps:
        status_map = {
            "pending": "待执行",
            "in_progress": "执行中",
            "completed": "已完成",
            "error": "出错"
        }
        output.append(f"{step.step_number}. {step.description} "
                     f"[{status_map.get(step.status, step.status)}]")
    
    if result.final_result:
        output.append("\n执行结果:")
        for step_key, step_result in result.final_result.items():
            output.append(f"\n{step_key}:")
            if isinstance(step_result, dict):
                for k, v in step_result.items():
                    output.append(f"  {k}: {v}")
            else:
                output.append(f"  {step_result}")
    
    return "\n".join(output)