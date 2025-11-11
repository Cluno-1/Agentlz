# 环境配置与数据库准备（.env）

本说明指导你正确配置项目根目录的 `.env` 文件，并完成 MySQL 数据库的初始化与常见问题排查。

## 必需的环境变量
在项目根目录创建或编辑 `.env`（完整示例请参考下面的示例内容）：

### 模型与日志
- `OPENAI_API_KEY`（使用 OpenAI 官方）或使用兼容端点：
- `CHATOPENAI_API_KEY`、`CHATOPENAI_BASE_URL`（例如 DeepSeek）
- `MODEL_NAME`（例如 `deepseek-chat`）
- `LOG_LEVEL`（例如 `INFO`）

### MySQL 数据库（用于 MCP 仓储查询）
- `DB_HOST`：MySQL 服务器地址
- `DB_PORT`：端口（示例 `13306`）
- `DB_USER`：用户名（示例 `root`）
- `DB_PASSWORD`：密码（示例 `agentdb123456`）
- `DB_NAME`：数据库名（项目默认使用 `agentlz`）

### 示例 `.env` 内容
```
# 模型（任选其一）
# OPENAI_API_KEY="sk-your-openai-key"

# 兼容端点（推荐）
CHATOPENAI_API_KEY="sk-your-deepseek-key"
CHATOPENAI_BASE_URL="https://api.deepseek.com/v1"

# 模型与日志
MODEL_NAME="deepseek-chat"
LOG_LEVEL="INFO"

# MySQL
DB_HOST="<your-db-host>"
DB_PORT="13306"
DB_USER="root"
DB_PASSWORD="<your-db-password>"
DB_NAME="agentlz"
```

## 数据库初始化
1. 确认你有一台可访问的 MySQL 服务器（本地或远程），端口放通且具备访问权限。
2. 在该 MySQL 实例中创建并初始化数据库：
   - SQL 脚本位置：`test/planner/sql/`
     - `init_mysql.sql`（建库/建表）
     - `seed_mcp_agents.sql`（写入示例 MCP 代理配置）
3. 可通过 MySQL 客户端或 Workbench 执行：
   - 命令行示例：
     - `mysql -h <DB_HOST> -P <DB_PORT> -u <DB_USER> -p`
     - 登录后：
       - `SOURCE d:/PyCharm/AgentCode/Agentlz/test/planner/sql/init_mysql.sql;`
       - `SOURCE d:/PyCharm/AgentCode/Agentlz/test/planner/sql/seed_mcp_agents.sql;`

## 常见问题与排查
### 1) 连接被拒或权限错误（Access denied）
- 错误示例：`Access denied for user 'root'@'x.x.x.x' (using password: YES)`
- 排查步骤：
  - 确认 `.env` 中的账号密码与 MySQL 实际一致；用下面命令验证：
    - `mysql -h <DB_HOST> -P <DB_PORT> -u root -p`
  - 检查 MySQL 用户是否允许远程访问（按需在服务器执行）：
    - `CREATE USER 'root'@'%' IDENTIFIED BY '<your-db-password>';`
    - 或切换认证插件：
      - `ALTER USER 'root'@'%' IDENTIFIED WITH mysql_native_password BY '<your-db-password>';`
    - 授权并刷新：
      - `GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' WITH GRANT OPTION;`
      - `FLUSH PRIVILEGES;`
  - 确认 MySQL 实例允许远程连接：
    - `mysqld` 配置中 `bind-address=0.0.0.0`（或对应网卡）
    - 防火墙/安全组已放通端口（例如 `13306`）

### 2) 数据库未初始化
- 若工具查询为空或异常，请运行 `init_mysql.sql` 与 `seed_mcp_agents.sql`。

### 3) Python 版本兼容警告
- 警告示例：`Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater`
- 建议使用 Python 3.11–3.13 运行，或忽略警告继续（不影响功能）。

## 与测试的关系
- `test/planner/generate_plan.py` 在需要按关键词查询 MCP 配置时会调用数据库工具 `get_mcp_config_by_keyword`，因此 DB 要正确配置。
- `test/excutor/run_excutor.py` 会读取 `test/planner/plan_output.json` 并执行；JSON 中的 `mcp_config` 描述了 MCP 服务器启动参数，无需手动启动。
- `test/planner_excutor/planner_excutor.py` 先编排再执行，整体依赖 `.env` 与 DB 可用。