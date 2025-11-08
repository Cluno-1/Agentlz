from fastapi import FastAPI
from langserve import add_routes
from langchain_core.runnables import RunnableLambda

from agentlz.agents.schedule.schedule_1_agent import query as schedule_query

app = FastAPI(title="Agentlz via LangServe")


# 对返回字符串的函数用 RunnableLambda 包一层
add_routes(app, RunnableLambda(lambda x: schedule_query(x["input"] if isinstance(x, dict) else x)), path="/agents/schedule_1")
