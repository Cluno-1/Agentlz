from typing import Any, Dict, List, Optional

from agentlz.config.settings import get_settings
from agentlz.core.logger import setup_logging
from agentlz.core.model_factory import get_model
from agentlz.schemas.responses import ScheduleResponse, PlanStep
from langchain.agents import create_agent

# 可信度表（MCP）导入：若为空则表示无可用 Agent
try:
    from agentlz.agent_tables.plan import PLAN_AGENTS  # type: ignore
except Exception:
    PLAN_AGENTS: List[Dict[str, Any]] = []

try:
    from agentlz.agent_tables.tools import TOOLS_AGENTS  # type: ignore
except Exception:
    TOOLS_AGENTS: List[Dict[str, Any]] = []

try:
    from agentlz.agent_tables.check import CHECK_AGENTS  # type: ignore
except Exception:
    CHECK_AGENTS: List[Dict[str, Any]] = []


class Schedule1Agent:
    """最小化可执行的总调度 Agent（schedule_1_agent）。

    基本职责：
    - 读取 plan/check/tools 的可信度表（MCP）。
    - 若表为空（无可用 Agent），则自己做判断,根据用户查询内容返回思考结果.
    - 若存在可用的 plan agent，则给出最小化的调度计划骨架与候选工具/检查列表（不实际远程调用）。
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.logger = setup_logging(settings.log_level)
        self.model = get_model(settings)  # 用于 LLM 汇总

    @staticmethod
    def _select_top(agents: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not agents:
            return None
        return sorted(agents, key=lambda x: x.get("trust", 0), reverse=True)[0]

    @staticmethod
    def _sort_by_trust(agents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return sorted(agents, key=lambda x: x.get("trust", 0), reverse=True)

    def _llm_summarize(
        self,
        query: str,
        status: str,
        plan_id: Optional[str],
        tools_ids: List[str],
        check_ids: List[str],
        steps: List[PlanStep],
        extra_notes: Optional[str] = None,
    ) -> str:
        
        # Fallback 简述
        fallback = (
            f"状态: {status}；Plan: {plan_id or '无'}；Tools: {tools_ids or []}；"
            f"Checks: {check_ids or []}；步骤数: {len(steps or [])}。"
        )
        if self.model is None:
            return fallback + (f"备注: {extra_notes}" if extra_notes else "")
        agent = create_agent(
            model=self.model,
            tools=[],
            system_prompt=self.settings.system_prompt,
        )
        # 构造汇总输入
        context = {
            "query": query,
            "status": status,
            "selected_plan_agent_id": plan_id,
            "selected_tools_agent_ids": tools_ids,
            "selected_check_agent_ids": check_ids,
            "steps": [s.model_dump() for s in (steps or [])],
            "notes": extra_notes or "",
        }
        result: Any = agent.invoke({"messages": [{"role": "user", "content": str(context)}]})
        if isinstance(result, dict):
            return (
                result.get("output")
                or result.get("final_output")
                or result.get("structured_response")
                or fallback
            )
        return str(result) if result else fallback

    def _llm_direct_answer(self, query: str) -> str:
        """When no plan is needed, directly use LLM to answer the query."""
        if self.model is None:
            return "模型未加载，无法回答。"

        agent = create_agent(
            model=self.model,
            tools=[],
            system_prompt="你是一个乐于助人的助手，请直接回答用户的问题。",
        )
        try:
            result: Any = agent.invoke({"messages": [{"role": "user", "content": query}]})
            
            if isinstance(result, dict):
                output = (
                    result.get("output")
                    or result.get("final_output")
                    or result.get("structured_response")
                )
                if output:
                    return output

            if result:
                return str(result)
            
            return "抱歉，我无法生成回答。"
        except Exception as e:
            self.logger.error(f"Error during direct LLM answer: {e}")
            return "在直接回答时发生错误。"
    # 计划代理, 当没有plan agent时使用
    def _llm_generate_plan(
        self,
        query: str,
        tools_candidates: List[Dict[str, Any]],
        check_candidates: List[Dict[str, Any]],
    ) -> tuple[List[str], List[str], List[PlanStep]]:
        """使用 LLM 生成计划、工具和检查列表，当没有 plan agent 时。"""

        if self.model is None:
            return [], [], []

        agent = create_agent(
            model=self.model,
            tools=[],
            system_prompt="你是一个调度代理，当没有可用的计划代理时，基于用户查询生成一个简单的执行计划，包括工具调用和检查步骤。请输出工具 ID 列表、检查 ID 列表和计划步骤列表。",
        )

        context = {
            "query": query,
            "available_tools": [a.get("id") for a in tools_candidates],
            "available_checks": [a.get("id") for a in check_candidates],
        }

        result: Any = agent.invoke({"messages": [{"role": "user", "content": str(context)}]})

        # 假设 result 是结构化的输出，解析它
        # 这里需要根据实际 LLM 输出解析，假设它返回 dict
        if isinstance(result, dict):
            tools_ids = result.get("tools_ids", [])
            check_ids = result.get("check_ids", [])
            steps = [PlanStep(**step) for step in result.get("steps", [])]
        else:
            # Fallback 解析
            tools_ids = []
            check_ids = []
            steps = []

        return tools_ids, check_ids, steps

    def execute(self, query: str) -> ScheduleResponse:
        """执行调度流程（最小化版本）。

        规则：
        - 优先选取最高可信度的 plan agent。
        - 输出占位的步骤（不真正调用 MCP），并列出 tools/check 候选。
        """

        # 1) 选择 plan agent（最高可信度）
        top_plan = self._select_top(PLAN_AGENTS)
        if not top_plan:
            self.logger.info("没有可用的 Plan MCP Agent（plan 可信度表为空）")

            # 整理 tools/check 候选（按可信度降序）
            tools_candidates = self._sort_by_trust(TOOLS_AGENTS)
            check_candidates = self._sort_by_trust(CHECK_AGENTS)
            selected_tool_ids = [a.get("id") for a in tools_candidates]
            selected_check_ids = [a.get("id") for a in check_candidates]

            # 使用 LLM 生成计划
            generated_tools, generated_checks, generated_steps = self._llm_generate_plan(
                query, tools_candidates, check_candidates
            )

            if not generated_steps:
                # If no plan is generated, it's likely a simple chat query.
                # Answer directly using the LLM.
                final_summary = self._llm_direct_answer(query)
                return ScheduleResponse(
                    query=query,
                    status="direct_answer",
                    selected_plan_agent_id=None,
                    selected_tools_agent_ids=[],
                    steps=[],
                    check_passed=None,
                    final_summary=final_summary,
                )

            final_summary = self._llm_summarize(
                query=query,
                status="auto_planned",
                plan_id=None,
                tools_ids=generated_tools,
                check_ids=generated_checks,
                steps=generated_steps,
                extra_notes="没有计划代理，使用 LLM 自动生成计划和工具调用。",
            )
            return ScheduleResponse(
                query=query,
                status="auto_planned",
                selected_plan_agent_id=None,
                selected_tools_agent_ids=generated_tools,
                steps=generated_steps,
                check_passed=False,
                final_summary=final_summary,
            )

        # 2) 整理 tools/check 候选（按可信度降序）
        tools_candidates = self._sort_by_trust(TOOLS_AGENTS)
        check_candidates = self._sort_by_trust(CHECK_AGENTS)
        selected_tool_ids = [a.get("id") for a in tools_candidates]
        selected_check_ids = [a.get("id") for a in check_candidates]

        # 3) 最小化计划骨架（占位）
        plan_steps: List[PlanStep] = [
            PlanStep(
                step_number=1,
                description="根据 plan agent 规范选择并调用第一个 tools agent（占位）",
                agent_type="tool",
                status="pending",
            ),
            PlanStep(
                step_number=2,
                description="使用 check agent 校验工具输出是否符合预期（占位）",
                agent_type="check",
                status="pending",
            ),
        ]

        # 4) 空表直接提示，不执行任何实际调用
        if len(tools_candidates) == 0 or len(check_candidates) == 0:
            msg = []
            if len(tools_candidates) == 0:
                msg.append("tools 可信度表为空")
            if len(check_candidates) == 0:
                msg.append("check 可信度表为空")
            extra = "，".join(msg) + "。仅输出计划骨架。"
            final_summary = self._llm_summarize(
                query=query,
                status="missing_tools_or_checks",
                plan_id=top_plan.get("id"),
                tools_ids=selected_tool_ids,
                check_ids=selected_check_ids,
                steps=plan_steps,
                extra_notes=extra,
            )
            return ScheduleResponse(
                query=query,
                status="missing_tools_or_checks",
                selected_plan_agent_id=top_plan.get("id"),
                selected_tools_agent_ids=selected_tool_ids,
                steps=plan_steps,
                check_passed=None,
                final_summary=final_summary,
            )

        # 5) 最小化执行结果（不触发 MCP）：仅汇总选择
        summary = (
            f"计划代理: {top_plan.get('id')}；"
            f"工具候选（按可信度降序）: {selected_tool_ids}；"
            f"检查候选: {selected_check_ids}。"
            "未进行真实远程调用，需接入 MCP 客户端后生效。"
        )

        return ScheduleResponse(
            query=query,
            status="planned",
            selected_plan_agent_id=top_plan.get("id"),
            selected_tools_agent_ids=selected_tool_ids,
            steps=plan_steps,
            check_passed=False,
            final_summary=summary,
        )


def query(message: str) -> str:
    """调度入口（字符串输出），便于 HTTP/CLI 包装。"""
    agent = Schedule1Agent()
    res = agent.execute(message)

    # 文本化输出（简要）
    lines = [
        f"查询: {res.query}",
        f"状态: {res.status}",
        f"Plan Agent: {res.selected_plan_agent_id or '无'}",
        f"Tools 候选: {', '.join(res.selected_tools_agent_ids) or '无'}",
        f"步骤数: {len(res.steps or [])}",
        f"总结: {res.final_summary or ''}",
    ]
    return "\n".join(lines)