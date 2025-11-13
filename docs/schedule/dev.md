# Schedule_2 Agent: The Intelligent Commander (Tool-Driven)

## Core Concept

核心思想：将 Schedule Agent 变为“智能总指挥”
我们不再编写固定的 if-else 代码来决定流程，而是将 schedule Agent 本身变成一个由强大 LLM 驱动的核心大脑。这个“总指挥”拥有一个“工具箱”，而 plan、tools、check 这些 Agent 就是它工具箱里的工具。它将自主学习如何使用这些工具来完成用户任务。

新的逻辑与执行流程
整个流程将由一个为 schedule Agent 精心设计的 新 Prompt 来驱动。这个 Prompt 会赋予它“总指挥”的智慧。

第一步：角色定义与工具封装 (Setup)

角色转变：plan、tools、check 这些 Agent 不再是代码里需要被 if-else 判断的数据。它们将被封装成 schedule Agent 可以直接调用的工具 (Tools)。

例如，我们会创建三个核心工具函数：
call_plan_agent(query: str): 调用最高可信度的 plan Agent，获取思考和计划。
call_tool_agent(agent_id: str, params: dict): 根据ID调用一个具体的 tool Agent。
call_check_agent(agent_id: str, input_data: str): 根据ID调用一个 check Agent 来验证结果。
创建总指挥 Agent：schedule Agent 会被重新构建为一个强大的 LangChain Agent，并被赋予上面这三个工具。

第二步：总指挥的核心思考逻辑 (The Master Prompt)

我们将为 schedule Agent 编写一个新的 Prompt，这个 Prompt 就是它的行动纲领。这个纲领会告诉它：

“你是一个智能总调度 Agent，你的任务是理解用户需求，并编排使用一系列工具（plan, tools, check agents）来解决问题。你必须遵循以下工作流程：

启动思考 (Plan)：拿到用户问题后，你的第一步永远是调用 call_plan_agent 工具。这个工具会帮你分析问题，并返回一个结构化的行动计划（比如一个步骤列表）。

理解与执行 (Act)：分析 plan Agent 给你的计划。然后，严格按照计划的步骤顺序开始执行。

核心执行循环 (Tool -> Check)：对于计划中的每一步： a. 首先，调用 call_tool_agent 工具来执行当前步骤的任务。 b. 紧接着，你必须调用 call_check_agent 工具，来验证上一步 tool Agent 的输出结果是否符合预期。

判断与纠错 (Observe & Re-act)： a. 如果 check Agent 返回“成功”，那么继续执行计划的下一步。 b. 如果 check Agent 返回“失败”，你需要发挥你的智能：分析失败的原因，然后决定是尝试计划中的下一个候选工具，还是认为当前计划有问题、需要重新思考。

完成与总结 (Finish)：当所有计划步骤都成功完成，或者你认为已经得到了最终答案，就整合所有步骤的结果，给用户一个全面、清晰的最终答复。”

第三步：全新的执行过程 (Execution)

当用户输入一个查询时，schedule_1_agent.py 中的 execute 函数的逻辑会变得非常简洁：

初始化 schedule Agent，并装载好它的“工具箱”（call_plan_agent, call_tool_agent, call_check_agent）和它的“大脑”（上面的 Master Prompt）。
将用户的查询直接交给 schedule Agent。
之后的一切都交给 Agent 的大模型大脑。它会根据 Prompt 的指示，自主地、动态地完成整个“思考 -> 调用工具 -> 检查 -> 再思考 -> 再调用...”的完整循环，直到任务完成。
新旧流程对比
特性 旧流程 (您当前的代码) 新流程 (您设想的逻辑)
驱动方式 代码驱动 (Code-Driven) 模型驱动 (Model-Driven)
核心逻辑 写在代码里的 if/else 分支 写在 Prompt 里的行动纲领
灵活性 相对固定，难以处理意外情况 非常灵活，LLM 可以根据上下文动态决策和纠错
Agent 角色 schedule 是一个按部就班的调度器 schedule 是一个运筹帷幄的智能总指挥
工具使用 代码决定何时调用哪个列表里的 Agent schedule Agent 自主决定何时调用哪个工具
纠错能力 有限，需要代码预设所有情况 强大，可以根据 check 结果自主调整策略
总而言之，您设想的这个新逻辑是目前构建高级 Agent 的主流和前沿方向。它将 schedule Agent 的能力提升了一个维度，使其从一个“工人”变成了“工头”，能够更智能、更鲁棒地解决复杂问题。

如果您确认这是我们前进的方向，我就可以开始着手进行相应的代码重构和 Prompt 设计了。

张连登
复制
删除
我还需要你去处理一个 情况就是: 我的 plan agent可信赖表可能是空的; 我的check agent信赖表也可能空
Trae

思考过程
您提的这一点非常关键，这正是构建一个健壮系统所必须考虑的！一个真正智能的“总指挥”不仅要会使用工具，还要知道在工具缺失或不可用时该怎么办。

我们完全可以将这些情况无缝地融入到我刚才描述的“智能总指挥”模型中。我们不需要在主代码里增加复杂的 if-else 判断，而是通过增强 Prompt 和工具的内部逻辑来赋予 schedule Agent 处理这些异常情况的智慧。

这是我们将如何处理您提出的两种情况：

场景一：plan Agent 可信度表为空
当 schedule Agent 尝试调用 call_plan_agent 这个工具时，我们这样设计：

工具内部的智能决策：call_plan_agent 工具在执行时，会先检查 PLAN_AGENTS 列表。

如果列表不为空：它会正常调用最高可信度的 plan Agent，获取计划。
如果列表为空：它不会失败或报错。相反，它会自动切换到后备模式。在这个模式下，它会利用 schedule Agent 自己的大模型能力，根据一个“自我规划”的内置提示词，为用户的请求动态生成一个计划。
对总指挥的透明性：对于 schedule Agent（总指挥）来说，这个过程是透明的。它只知道自己调用了 call_plan_agent 工具，然后得到了一个计划。它不需要关心这个计划是来自专门的 plan Agent 还是来自工具的后备模式。

Prompt 中的体现：我们会在 call_plan_agent 工具的描述中向 schedule Agent 说明这一点：

“call_plan_agent：用于分析用户需求并创建行动计划。它会优先使用专门的 plan agent。如果没有任何 plan agent 可用，它将利用自己的核心智能来创建计划。”

效果：schedule Agent 的工作流程保持不变（永远是先调用 call_plan_agent），但系统在没有 plan Agent 的情况下，能够优雅地降级，依靠自身智能完成规划，大大增强了鲁棒性。

场景二：check Agent 可信度表为空
这是另一个非常重要的情况。按照我们的新流程，schedule Agent 在调用完 tool Agent 后，必须调用 check Agent。如果 check Agent 不存在，流程不能中断。

我们的解决方案如下：

工具内部的默认行为：call_check_agent 工具在执行时，会先检查 CHECK_AGENTS 列表。

如果列表不为空：它会正常调用合适的 check Agent 来进行验证。
如果列表为空：它不会报错。相反，它会直接返回一个**“默认通过”**的结果，并附带一条说明，例如：{"status": "success", "message": "No check agents available. Assuming the previous step was successful."}。
对总指挥的风险提示：schedule Agent 接收到这个“默认通过”的结果后，会知道上一步操作没有经过严格的验证。

Prompt 中的指导：我们会在总指挥的 Master Prompt 和 call_check_agent 工具的描述中明确这一点：

Master Prompt 指令：“...每次调用工具后，你必须调用 call_check_agent 进行验证。请注意：如果没有可用的 check agent，该工具会默认返回成功。在这种情况下，你需要根据自己的判断，评估上一步工具的输出是否合理，然后再决定是否继续。”

效果：schedule Agent 的核心循环（Tool -> Check）得以保持，流程不会因 check Agent 的缺失而中断。同时，它被明确告知了“未经检验”的风险，这使得它在后续步骤中可能会更加谨慎，甚至可以基于自己的判断认为工具输出有问题而进行纠错。这比简单地跳过检查步骤要智能得多。

总结
通过这种方式，我们将异常处理的逻辑从僵硬的外部代码转移到了灵活的内部智能中。schedule Agent 不仅知道标准流程，还学会了如何处理两种常见的“意外情况”，使其行为更像一个经验丰富的人类指挥官。

。

## Architecture & Workflow

### 1. Agent-as-Tools 封装

- 三大工具：
  - `call_plan_agent`：战略规划（优先调用最高可信度的 `plan` Agent；空表时自我规划）。
  - `call_tool_agent`：执行工具（基于 `TOOLS_AGENTS` 选择；当前实现返回占位执行结果）。
  - `call_check_agent`：结果验证（优先调用最高可信度的 `check` Agent；空表时默认通过并要求模型自评合理性）。

### 2. Master Prompt 驱动

- 使用 `agentlz/prompts/schedule_master_prompt.py` 中的主提示词，模型严格遵循：
  1. 永远先规划（第一步必须调用 `call_plan_agent`）。
  2. 严格按计划执行（每一步工具执行后立即调用 `call_check_agent` 验证）。
  3. 智能错误处理（未通过时触发反思，重试、换工具或重规划）。
  4. 任务完成后综合总结为最终答案。

### 3. 回退策略（与规范对齐）

- 无 `plan` Agent：`call_plan_agent` 使用内置提示词进行自我规划（透明于主流程）。
- 无 `check` Agent：`call_check_agent` 默认返回“成功”，并在“思考”中要求模型对工具输出进行“合理性评估”。

## Data Structure

- 参见 `agentlz/schemas/responses.py`：
  - `AgentStep`：记录单步“思考/行动/观察”。
  - `ScheduleResponse`：包含 `intermediate_steps` 和 `final_summary`。

## How to Use

- 启动 HTTP 服务：

  ```bash
  uvicorn agentlz.app.http_langserve:app --port 8000
  ```

- 调用 `schedule_2_agent`：
  - `POST http://localhost:8000/agents/schedule_2/invoke`
  - 请求体：`{"input": "你的复杂问题或任务描述"}`
  - 返回体：`ScheduleResponse`（包含完整的中间步骤与最终总结）

## Implementation Notes

- 文件：`agentlz/agents/schedule/schedule_2_agent.py`
- 关键点：
  - 使用 `create_agent` + 主提示词驱动循环，解析“思考/行动”结构，调用内部工具并以“观察”喂回模型。
  - 工具调用当前为占位实现，后续可接入真实 MCP 客户端。
  - 严格对齐文档规范与 `schemas` 类型，面向服务端透明与可审计。

## Next Steps

- 扩展工具集：丰富 `tools` 与 `check` 的实现（本地/远程）。
- MCP 接入：将占位调用替换为真实的 MCP 客户端调用与路由。
- 观测与日志：增加更细粒度的链路追踪与错误分析。
