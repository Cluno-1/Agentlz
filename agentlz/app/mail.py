import typer

from ..agents.mail_agent import send as send_mail_action
from ..core.logger import setup_logging

app = typer.Typer(help="Mail agent CLI")
logger = setup_logging()


@app.command()
def send(content: str, to_email: str):
    """Send an email via the mail agent. Print 'ok' or 'error: ...'."""
    # 写一个请求他查看github代码更新，注意在coding的同时享受生活的邮件
    # 951117922@qq.com
    try:
        logger.info(f"发送邮件到: {to_email}")
        out = send_mail_action(content, to_email)
        print(out)
    except Exception as e:
        logger.error(f"发送邮件失败: {e}")
        print(f"error: {e}")


if __name__ == "__main__":
    app()