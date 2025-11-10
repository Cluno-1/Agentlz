from pathlib import Path

CHECK_PROMPT = Path(__file__).parent.joinpath("check/system.prompt").read_text(encoding="utf-8")