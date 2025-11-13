from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import json
import re
import time

from agentlz.config.settings import get_settings
from agentlz.core.logger import setup_logging
from agentlz.core.model_factory import get_model
from agentlz.schemas.responses import ScheduleResponse, AgentStep, ToolResponse, CheckResponse
from langchain.agents import create_agent

# 提示词
from agentlz.prompts.schedule_master_prompt import SCHEDULE_MASTER_PROMPT
from agentlz.prompts.schedule.plan_generation import PLAN_GENERATION_PROMPT

# 可信度表（MCP）
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


class Schedule2Agent:
    """智能指挥官（schedule_2_agent）

    该 Agent 采用“思考-行动-观察”的循环，由主提示词驱动，
    通过封装的三大工具（call_plan_agent / call_tool_agent / call_check_agent）完成任务。

    - 工具选择基于可信度表（MCP）；
    - 当可信度表为空时，按照规范进行回退（自我规划 / 默认检查通过但需自评合理性）。
    - 输出结构严格遵循 schemas.responses 中的 ScheduleResponse / AgentStep。
    """

    def __init__(self) -> None:
        """初始化实例

        参数: 无
        返回值: None
        异常: 可能抛出配置加载或模型创建相关异常
        """
        settings = get_settings()
        self.settings = settings
        self.logger = setup_logging(settings.log_level)
        self.model = get_model(settings)
        # 记录上一工具输出，便于 check 工具在未显式提供输入时进行验证
        self._last_tool_output: Dict[str, Any] = {}

    # -----------------------------
    # 统一工具箱：由调度 Agent 决策，代码仅分发执行
    # -----------------------------
    def _get_toolbox(self) -> Dict[str, Any]:
        """构建可调用的工具箱映射（tool_name -> callable）

        说明：
        - 避免在主循环中使用 if-else；
        - 每个工具均接受一个字典形式的 `action_input`，返回 (tool_output, observation)。

        返回值：
            Dict[str, Any]: 工具名称到可调用函数的映射
        """

        def _adapter_call_plan_agent(action_input: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
            query = action_input.get("query") or action_input.get("input") or ""
            tool_output = self._tool_call_plan_agent(query)
            observation = (
                f"计划已生成（mode={tool_output.get('mode')}）：{self._safe_dumps(tool_output.get('steps', []))}"
            )
            self._last_tool_output = tool_output
            return tool_output, observation

        def _adapter_call_tool_agent(action_input: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
            tool_id = action_input.get("tool_id")
            params = action_input.get("params") or {}
            if isinstance(params, str):
                try:
                    params = json.loads(params)
                except Exception:
                    params = {"raw": params}
            tool_output = self._tool_call_tool_agent(tool_id=tool_id, params=params)
            observation = tool_output.get("output_text") or "工具执行完成"
            self._last_tool_output = tool_output
            return tool_output, observation

        def _adapter_call_check_agent(action_input: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
            explicit_output = action_input.get("tool_output")
            if isinstance(explicit_output, str):
                try:
                    explicit_output = json.loads(explicit_output)
                except Exception:
                    explicit_output = {"raw": explicit_output}
            base_output: Dict[str, Any] = (
                explicit_output if isinstance(explicit_output, dict) else (self._last_tool_output or {})
            )
            tool_output = self._tool_call_check_agent(tool_output=base_output)
            observation = tool_output.get("reason") or "校验完成"
            self._last_tool_output = tool_output
            return tool_output, observation

        return {
            "call_plan_agent": _adapter_call_plan_agent,
            "call_tool_agent": _adapter_call_tool_agent,
            "call_check_agent": _adapter_call_check_agent,
        }

    # -----------------------------
    # 安全序列化：保护 json.dumps，失败回退到 str(obj)
    # -----------------------------
    @staticmethod
    def _safe_dumps(obj: Any) -> str:
        """安全地将对象序列化为 JSON 字符串。

        优先使用 json.dumps；若失败，尝试调用对象的 model_dump/dict；
        最后回退为 str(obj)。
        """
        try:
            return json.dumps(obj, ensure_ascii=False)
        except Exception:
            try:
                if hasattr(obj, "model_dump"):
                    return json.dumps(obj.model_dump(), ensure_ascii=False)
                if hasattr(obj, "dict"):
                    return json.dumps(obj.dict(), ensure_ascii=False)
            except Exception:
                pass
            return str(obj)

    # -----------------------------
    # 通用工具：可信度排序 / 选择最高
    # -----------------------------
    @staticmethod
    def _select_top(agents: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """选择可信度最高的代理

        参数: agents: 代理配置列表
        返回: 可信度最高的代理或 None
        异常: 无
        """
        if not agents:
            return None
        return sorted(agents, key=lambda x: x.get("trust", 0), reverse=True)[0]

    @staticmethod
    def _sort_by_trust(agents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """按可信度降序排序代理列表"""
        return sorted(agents, key=lambda x: x.get("trust", 0), reverse=True)

    # -----------------------------
    # 内部工具封装：plan / tool / check
    # -----------------------------
    def _tool_call_plan_agent(self, query: str) -> Dict[str, Any]:
        """封装 `call_plan_agent` 的逻辑

        规范：
        - 若有可用 plan agent（可信度表非空），按最高可信度进行规划（当前以 LLM 生成计划代替实际 MCP 调用）。
        - 若无可用 plan agent，则自我规划（LLM + 内置提示词 PLAN_GENERATION_PROMPT）。

        参数: query: 用户查询
        返回: dict，包含 plan 步骤与来源模式说明
        异常: 可能抛出 LLM 调用相关异常
        """
        tools_candidates = self._sort_by_trust(TOOLS_AGENTS)
        check_candidates = self._sort_by_trust(CHECK_AGENTS)

        mode = "mcp_plan_agent" if PLAN_AGENTS else "self_planning"
        top_plan_id = self._select_top(PLAN_AGENTS).get("id") if PLAN_AGENTS else None

        if self.model is None:
            # 模型不可用时的兜底：返回一个简单的单步计划
            return {
                "mode": mode,
                "selected_plan_agent_id": top_plan_id,
                "steps": [
                    {
                        "step": 1,
                        "tool": tools_candidates[0].get("id") if tools_candidates else "tool_placeholder",
                        "params": {},
                        "goal": "占位：执行核心工具一步并返回结果"
                    }
                ],
            }

        # 使用 LLM 生成计划（无论是否有 plan agent，均走统一的计划生成提示词，来源通过 mode 标记）
        agent = create_agent(
            model=self.model,
            tools=[],
            system_prompt=PLAN_GENERATION_PROMPT,
        )

        context = {
            "query": query,
            "available_tools": [a.get("id") for a in tools_candidates],
            "available_checks": [a.get("id") for a in check_candidates],
        }

        try:
            result: Any = agent.invoke({"messages": [{"role": "user", "content": str(context)}]})
        except Exception as e:
            self.logger.error(f"Plan generation failed: {e}")
            result = {}

        steps_raw: List[Dict[str, Any]] = []
        if isinstance(result, dict):
            steps_raw = result.get("steps", []) or []

        # 转换为统一的计划观察结构（step/tool/params/goal）
        steps_obs: List[Dict[str, Any]] = []
        for idx, s in enumerate(steps_raw or []):
            agent_type = s.get("agent_type", "tool")
            goal = s.get("description", "执行一步")
            # 为 tool/check 步骤绑定一个候选 id（若存在）
            if agent_type == "tool":
                tool_id = tools_candidates[0].get("id") if tools_candidates else "tool_placeholder"
            else:
                tool_id = (check_candidates[0].get("id") if check_candidates else "check_placeholder")
            steps_obs.append({
                "step": idx + 1,
                "tool": tool_id,
                "params": {},
                "goal": goal,
            })

        if not steps_obs:
            # 最少提供一条占位步骤
            steps_obs = [{
                "step": 1,
                "tool": tools_candidates[0].get("id") if tools_candidates else "tool_placeholder",
                "params": {},
                "goal": "占位：执行核心工具一步并返回结果",
            }]

        return {
            "mode": mode,
            "selected_plan_agent_id": top_plan_id,
            "steps": steps_obs,
        }

    def _tool_call_tool_agent(self, tool_id: Optional[str], params: Dict[str, Any]) -> Dict[str, Any]:
        """封装 `call_tool_agent` 的逻辑

        当前实现：
        - 不实际触发远程 MCP；
        - 选择最高可信度的 tools agent（若有），返回占位执行结果；
        - 若传入的 tool_id 存在于可信度表，则优先使用该 id。

        参数: tool_id: 期望执行的工具 ID；params: 工具入参
        返回: dict（ToolResponse 的 dict 形式）
        异常: 无（内部记录错误信息）
        """
        selected = None
        if tool_id:
            selected = next((t for t in TOOLS_AGENTS if t.get("id") == tool_id), None)
        if not selected:
            selected = self._select_top(TOOLS_AGENTS)

        start = time.time()
        # 占位执行
        output_text = (
            f"占位执行工具: {selected.get('id') if selected else 'none'}; "
            f"params={self._safe_dumps(params)}"
        )
        elapsed_ms = int((time.time() - start) * 1000)

        tr = ToolResponse(
            status="executed",
            agent_id=selected.get("id") if selected else None,
            tool=tool_id or (selected.get("id") if selected else None),
            params=params,
            output_text=output_text,
            output_data=None,
            success=True,
            elapsed_ms=elapsed_ms,
        )
        return tr.model_dump()

    def _tool_call_check_agent(self, tool_output: Dict[str, Any]) -> Dict[str, Any]:
        """封装 `call_check_agent` 的逻辑

        规范：
        - 若可信度表为空：默认返回通过（passed=True），同时在 reason 中提示需自行评估合理性；
        - 若非空：返回通过（占位），后续接入真实 MCP 校验。

        参数: tool_output: 上一步工具的输出
        返回: dict（CheckResponse 的 dict 形式 + 附加字段）
        异常: 无
        """
        selected = self._select_top(CHECK_AGENTS)
        if not selected:
            cr = CheckResponse(
                status="passed",
                agent_id=None,
                passed=True,
                reason="没有可用的 check agent，默认返回成功；请在思考中自行评估工具输出的合理性。",
                expected=None,
                observed=str(tool_output)[:500],
                score=None,
            ).model_dump()
            cr["fallback_no_check_agents"] = True
            return cr

        # 占位：当有 check agent 时，默认通过
        cr = CheckResponse(
            status="passed",
            agent_id=selected.get("id"),
            passed=True,
            reason="占位校验：工具输出格式合理。",
            expected=None,
            observed=str(tool_output)[:500],
            score=0.9,
        ).model_dump()
        return cr

    # -----------------------------
    # 解析助手：从模型输出中提取 思考 与 行动 JSON
    # -----------------------------
    @staticmethod
    def _parse_thought_and_action(text: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """解析模型输出，提取“思考”与“行动”JSON

        参数: text: 模型输出字符串
        返回: (thought, action_dict)；任意不可解析则返回 None
        异常: 无
        """
        thought = None
        action_json: Optional[Dict[str, Any]] = None

        # 提取“思考:”后的段落（直到“行动:”或文本末尾）
        m_thought = re.search(r"思考\s*:\s*(.*?)(?:\n\s*行动\s*:|$)", text, flags=re.S)
        if m_thought:
            thought = m_thought.group(1).strip()

        # 提取行动 JSON 代码块
        m_action_block = re.search(r"行动\s*:\s*```json\s*(.*?)\s*```", text, flags=re.S)
        if m_action_block:
            try:
                action_json = json.loads(m_action_block.group(1))
            except Exception:
                action_json = None

        return thought, action_json

    # -----------------------------
    # 解析助手：从 agent.invoke 的结果中提取最后 AI 文本与原始消息快照
    # -----------------------------
    def _extract_ai_content_and_raw(self, result: Any) -> Tuple[str, Optional[str]]:
        """从 LLM 返回结构中提取用于解析的文本与原始消息快照。

        兼容情况：
        - dict: 优先取 output/final_output/structured_response；其次 messages 列表中的最后 AI/assistant 内容；
        - 其他：回退为 str(result)。

        返回：
            (content, raw_messages_json)
        """
        raw_dump: Optional[str] = None

        if isinstance(result, dict):
            content = (
                result.get("output")
                or result.get("final_output")
                or result.get("structured_response")
            )
            # 若无直接输出，尝试从 messages 中抽取
            msgs = result.get("messages")
            if not content and isinstance(msgs, list):
                # 原始消息快照（仅保留 role/content 以控制大小）
                simplified = []
                for m in msgs:
                    role = None
                    cnt = None
                    if isinstance(m, dict):
                        role = m.get("role")
                        cnt = m.get("content")
                    else:
                        role = getattr(m, "role", None)
                        cnt = getattr(m, "content", None)
                    simplified.append({"role": role, "content": cnt})
                raw_dump = self._safe_dumps(simplified)

                # 取最后一条 AI/assistant 内容
                last_content = None
                for m in reversed(msgs):
                    role = None
                    cnt = None
                    cls = m.__class__.__name__ if not isinstance(m, dict) else None
                    if isinstance(m, dict):
                        role = m.get("role")
                        cnt = m.get("content")
                    else:
                        role = getattr(m, "role", None)
                        cnt = getattr(m, "content", None)
                    if role == "assistant" or (cls and "AIMessage" in cls):
                        last_content = cnt
                        break
                if last_content is None and msgs:
                    last = msgs[-1]
                    last_content = (
                        last.get("content") if isinstance(last, dict) else getattr(last, "content", None)
                    )
                content = last_content or ""

            if content:
                return str(content), raw_dump
            # 最后回退为序列化字典
            return self._safe_dumps(result), raw_dump

        # 非字典情况
        return str(result) if result else "", None

    # -----------------------------
    # 主执行：思考-行动-观察循环
    # -----------------------------
    def execute(self, query: str, max_loops: int = 8) -> ScheduleResponse:
        """执行调度流程

        参数: query: 用户原始输入；max_loops: 最大循环次数，避免无限循环
        返回: ScheduleResponse
        异常: 可能抛出 LLM 调用相关异常（内部捕获并记录）
        """
        if self.model is None:
            # 模型不可用，直接返回占位总结
            return ScheduleResponse(
                query=query,
                status="error",
                intermediate_steps=[],
                final_summary="模型未加载，无法执行 schedule_2_agent。",
            )

        agent = create_agent(
            model=self.model,
            tools=[],
            system_prompt=SCHEDULE_MASTER_PROMPT,
        )

        steps: List[AgentStep] = []
        messages: List[Dict[str, str]] = [{"role": "user", "content": query}]
        toolbox = self._get_toolbox()

        # 循环：LLM -> 行动解析 -> 工具执行 -> 观察反馈
        for _ in range(max_loops):
            try:
                result: Any = agent.invoke({"messages": messages})
            except Exception as e:
                self.logger.error(f"Agent invoke failed: {e}")
                return ScheduleResponse(
                    query=query,
                    status="error",
                    intermediate_steps=steps,
                    final_summary=f"执行过程中发生错误：{e}",
                    error=str(e),
                )

            # 标准化输出为字符串，同时携带原始消息快照
            content, raw_msgs = self._extract_ai_content_and_raw(result)

            thought, action = self._parse_thought_and_action(content)
            if not action or "action" not in action:
                # 认为任务已完成或输出不可解析，作为最终总结
                final_summary = content.strip() or "任务已完成。"
                # 附加原始模型消息（便于审计与完整信息返回）
                if raw_msgs:
                    final_summary = (
                        final_summary + "\n原始消息快照:" + raw_msgs
                    )
                return ScheduleResponse(
                    query=query,
                    status="final_answer",
                    intermediate_steps=steps,
                    final_summary=final_summary,
                )

            action_name = action.get("action")
            action_input = action.get("action_input", {}) if isinstance(action.get("action_input"), dict) else {}

            # 由调度 Agent 决策工具名称，这里通过工具箱映射进行统一分发
            tool_callable = toolbox.get(action_name)
            if not tool_callable:
                tool_output = {"error": f"未知的工具: {action_name}"}
                observation = f"未知工具：{action_name}"
            else:
                try:
                    tool_output, observation = tool_callable(action_input)
                except Exception as e:
                    tool_output = {"error": f"工具执行失败: {action_name}", "detail": str(e)}
                    observation = f"工具执行失败：{action_name}（{e}）"

            # 记录中间步骤（附加原始消息快照以便“返回全部信息”）
            obs_text = observation
            if raw_msgs:
                obs_text = f"{observation}\n原始消息快照:{raw_msgs}"
            steps.append(AgentStep(
                thought=thought or "",
                tool=action_name or "",
                tool_input=action_input,
                tool_output=tool_output,
                observation=obs_text,
            ))

            # 将观察反馈给 LLM，继续下一轮
            messages.append({"role": "user", "content": f"观察: {self._safe_dumps(tool_output)}"})

        # 超过最大循环仍未结束，返回已收集的步骤与提示
        return ScheduleResponse(
            query=query,
            status="final_answer",
            intermediate_steps=steps,
            final_summary="达到最大循环次数，已返回当前总结与步骤。",
        )


def query(message: str) -> ScheduleResponse:
    """调度入口函数（便于 HTTP 暴露）

    参数: message: 用户输入消息
    返回: ScheduleResponse
    异常: 可能抛出 Schedule2Agent 初始化或执行相关异常
    """
    agent = Schedule2Agent()
    return agent.execute(message)