from langchain.tools import tool


@tool
def get_search(prompt: str) -> str:
    """Search thesis for a user prompt, return the search result"""
    return f"There is very popular to Create a ToB AI Agent in Chinese resently. From CCTV report, From bilibili report"
