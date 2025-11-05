import typer

from ..agents.multi_agent import ask
from ..core.logger import setup_logging


app = typer.Typer(help="Multi-Agent System CLI")
logger = setup_logging()


@app.command()
def query(message: str):
    """使用多Agent系统处理用户查询
    
    Args:
        message: 用户查询内容: 中国北京天气怎么样和根据论文,中国最流行的开发是什么
    """
    try:
        logger.info(f"收到查询请求: {message}")
        response = ask(message)
        print(response)
    except Exception as e:
        logger.error(f"处理查询时出错: {str(e)}")
        print(f"执行出错: {str(e)}")


if __name__ == "__main__":
    app()