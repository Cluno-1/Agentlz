from fastapi import FastAPI
from starlette.responses import StreamingResponse
from langserve import add_routes
from langchain_core.runnables import RunnableLambda
import asyncio
import json

# from agentlz.agents.schedule.schedule_1_agent import query as schedule_query
from agentlz.agents.schedule.schedule_2_agent import query as schedule2_query
# from agentlz.agents.schedule.schedule_think_agent import query_stream as schedule_query_stream

app = FastAPI(title="Agentlz via LangServe")


# 对返回字符串的函数用 RunnableLambda 包一层
# add_routes(app, RunnableLambda(lambda x: schedule_query(x["input"] if isinstance(x, dict) else x)), path="/agents/schedule_1")

# 新增：schedule_2_agent 路由
add_routes(app, RunnableLambda(lambda x: schedule2_query(x["input"] if isinstance(x, dict) else x)), path="/agents/schedule_2")


# @app.post("/agents/schedule_think/stream")
# async def schedule_think_stream(input_data: dict):
#     """
#     SSE 流式接口 for ScheduleAgentThink - OpenAI兼容格式
#     """
#     query_text = input_data.get("input", "") if isinstance(input_data, dict) else str(input_data)
    
#     async def event_stream():
#         try:
#             async for chunk in schedule_query_stream(query_text):
#                 print("[chunk respones :]"+chunk)
#                 # 直接发送OpenAI格式的JSON作为SSE数据
#                 yield f"data: {chunk}\n\n"
#                 await asyncio.sleep(0.01)  # 避免发送过快
            
#             # 发送完成事件，保持连接
#             yield f"data: [DONE]\n\n"
            
#         except Exception as e:
#             # 发送错误信息，保持OpenAI格式
#             error_response = json.dumps({
#                 "id": "chatcmpl-error",
#                 "object": "chat.completion.chunk",
#                 "created": 1700000000,
#                 "model": "gpt-4",
#                 "choices": [{
#                     "index": 0,
#                     "delta": {"content": f"Error: {str(e)}"},
#                     "finish_reason": "stop"
#                 }]
#             })
#             yield f"data: {error_response}\n\n"
#             yield f"data: [DONE]\n\n"
    
#     return StreamingResponse(
#         event_stream(),
#         media_type="text/event-stream",
#         headers={
#             "Cache-Control": "no-cache",
#             "Connection": "keep-alive",
#             "Access-Control-Allow-Origin": "*",
#             "Access-Control-Allow-Headers": "*",
#             "X-Accel-Buffering": "no",  # 禁用Nginx缓冲
#         }
#     )
