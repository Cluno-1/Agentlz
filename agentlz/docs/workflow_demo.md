# MCP 流程链编排、装配与执行（简易版）开发说明

本文件针对 `agentlz/app/workflow_demo.py` 所示的演示流程，说明如何在“未实现 MCP 搜索逻辑”的前提下完成：
1) 流程链编排（WorkflowPlan 的结构化输出），
2) MCP 服务器装配（MultiServerMCPClient 初始化），
3) 工具加载与执行（LangChain Agent 驱动）。

## 适用范围
- 简易版：不做动态 MCP 搜索与注册，仅使用静态工具映射（`mcp_config_tool.py`）。
- 严格模式编排：`workflow_builder.py` 要求模型返回结构化 `WorkflowPlan`，不进行兜底补全；否则直接抛错。

## 关键组件
- 入口脚本：`agentlz/app/workflow_demo.py`
- 编排器：`agentlz/workflows/workflow_builder.py`
- 执行器：`agentlz/workflows/mcp_chain_executor.py`
- MCP Agents：`agentlz/agents/math_agent.py`、`agentlz/agents/language_agent.py`
- 静态工具映射：`agentlz/tools/mcp_config_tool.py`
- 数据模型：`agentlz/schemas/workflow.py`
- 配置：`agentlz/config/settings.py`

## 数据模型
- `MCPConfigItem`：描述一条 MCP 服务器装配项，字段：`name`、`transport`、`command`、`args`。
- `WorkflowPlan`：编排结构体，字段：
  - `execution_chain`：按顺序的 agent 名称列表（如 `['math_agent', 'language_agent']`）；
  - `mcp_config`：装配配置项列表（与 `MCPConfigItem` 对齐）。

## 流程编排（严格模式）
- 函数：`build_workflow_chain(user_input: str) -> WorkflowPlan`
- 机制：
  - 使用 `langchain.agents.create_agent`，绑定工具 `get_mcp_config_by_keyword`（静态返回所需 MCP 服务器装配配置）。
  - 通过 `response_format=WorkflowPlan` 要求模型输出结构化数据。
  - 若未返回 `structured_response`，直接抛出异常并携带原始响应，便于快速定位问题。


## MCP 装配
- 来源：编排返回的 `plan.mcp_config`。
- 执行器读取每条 `MCPConfigItem`，初始化 `MultiServerMCPClient`：
  - `transport` 固定为 `stdio`；
  - `command` 通常为 `python`；
  - `args` 为 MCP agent 脚本的绝对路径（例如 `agentlz/agents/math_agent.py`）。
- Windows 兼容：
  - 在 MCP agent 的 `__main__` 中设置 `sys.stdout.reconfigure(encoding='utf-8')`，避免 stdio 编码导致连接关闭；
  - 在 MCP agent 文件顶部注入项目根路径到 `sys.path`，确保子进程能导入 `agentlz` 包。

## 工具加载与执行
- 在执行器 `MCPChainExecutor` 中：
  - 调用 `await MultiServerMCPClient.get_tools()` 加载 MCP 暴露的工具列表；
  - 使用 `create_agent(model, tools, system_prompt=...)` 创建 LangChain Agent；
  - 将用户原始意图（`workflow_demo.py` 中的 `user_input` 字符串）作为上下文，调用 `agent.ainvoke(...)` 获取最终输出。
- 提示策略：系统提示中可注入“首选工具顺序”（来自 `plan.execution_chain`），引导代理按期望顺序调用工具；简易版不实现逐工具的强制链路执行。

## demo 脚本说明（workflow_demo.py）
1) 读取用户意图 `user_input`；
2) 调用 `build_workflow_chain(user_input)` 获取编排结果；
3) 首选 `WorkflowPlan` 数据类；兼容旧路径时将字符串或字典转换为 `WorkflowPlan`（仅 demo 为方便对比保留）；
4) 实例化 `MCPChainExecutor(plan)` 并调用 `execute_chain(input_data)`；
5) 输出最终结果到控制台。

## 运行与配置
- 运行：`python -m agentlz.app.workflow_demo`
- 配置：在 `settings.py` 中设置模型参数与密钥：
  - `MODEL_NAME`、`MODEL_BASE_URL`、`DEEPSEEK_API_KEY`。
- 确认本地 Python 可执行；MCP agent 脚本路径为绝对路径。

## 常见问题
- 结构化响应缺失：`ValueError: WorkflowPlan structured_response missing`。
  - 检查编排提示是否清晰、工具是否正确绑定，打印原始响应内容定位问题。
- 连接关闭：`McpError('Connection closed')`。
  - 典型原因为子进程路径或编码问题；确保脚本绝对路径、在 Windows 设置 UTF-8 编码，并注入项目根到 `sys.path`。
- 包导入失败：`ModuleNotFoundError: No module named 'agentlz'`。
  - 在 MCP agent 顶部加入项目根路径到 `sys.path` 以支持脚本模式导入。

## 扩展方向
- 动态 MCP 搜索与注册：在编排阶段根据任务自动检索与加载可用 MCP 工具。


## 文件索引
- `agentlz/app/workflow_demo.py`：演示入口，串联编排与执行。
- `agentlz/workflows/workflow_builder.py`：严格模式编排，返回 `WorkflowPlan`。
- `agentlz/workflows/mcp_chain_executor.py`：MCP 客户端与工具加载、Agent 执行。
- `agentlz/tools/mcp_config_tool.py`：静态工具映射（简易版，不含搜索逻辑）。
- `agentlz/agents/math_agent.py`、`agentlz/agents/language_agent.py`：MCP agent 服务脚本。
- `agentlz/schemas/workflow.py`：编排数据模型定义。