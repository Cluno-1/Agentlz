# 说明与使用建议

- 在总调度里， ScheduleResponse.plan_response 挂载 PlanResponse ，同时 ScheduleResponse.steps 可直接使用 PlanStep 的列表。
- selected_tools_agent_ids 表示调度时选择的工具候选（按可信度排序）；实际执行结果建议用 ToolResponse 列表（如需“返回所有内容”，可以在后续扩展 ScheduleResponse 增加 tool_responses: List[ToolResponse] 与 check_responses: List[CheckResponse] ）。
- 若需要更严格的状态类型，可将 status: str 替换为 Enum 并在各模型中使用对应枚举。当前保持灵活的 str 以便快速迭代。
- 已通过 from __future__ import annotations 解决前向引用（ ScheduleResponse 中引用 PlanResponse / PlanStep ）。如果你更偏好不使用前向引用，可把 PlanStep 、 PlanResponse 类挪到 ScheduleResponse 之前。