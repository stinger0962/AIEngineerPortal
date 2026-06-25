# backend/app/services/qian/oracle.py
"""观音灵签 AI 解签：单次 Claude 调用 + 内联标记（复用紫微的标记解析器）。"""
from __future__ import annotations

import time
from typing import Any, Optional

from app.services.qian.personas import persona_prompt
from app.services.ziwei.oracle_tools import current_date_note, parse_markers


class QianOracle:
    def __init__(self, client: Any, model: str):
        self.client = client
        self.model = model

    def system_prompt(self, sign: dict, question: str) -> str:
        return (
            persona_prompt()
            + "\n\n下面是求签者摇到的这支签（签诗为公版原文，"
            "**不得改写或臆造签诗**，只可解读）：\n"
            f"第{sign['id']}签 · {sign['grade']} · {sign['palace']} · {sign['title']}\n"
            f"签诗：{sign['poetry']}\n"
            f"解曰：{sign['meaning']}\n"
            f"圣意：{sign['holy']}\n"
            + current_date_note()
            + "\n\n## 输出\n先用一句把签诗的意象点出来，再结合求签者的问题给出解读与宽心的建议，"
            "约 250-450 字，口语、温和。\n"
            "## 内联标记（会被前端解析、不显示给用户）\n"
            "- 解释签诗里的生僻词或典故时，插入 [[term:词|一句话白话解释]]。\n"
            "整段只在 1-3 个最关键的词上用 term，不要每词都标。只用 term 标记，不要使用 focus 或 overview 标记。"
            "除标记外正常说话，不要输出 JSON 或代码块。"
        )

    def run(self, sign: dict, question: str) -> Optional[dict]:
        system = self.system_prompt(sign, question)
        start = time.time()
        try:
            resp = self.client.messages.create(
                model=self.model, max_tokens=1200, system=system,
                messages=[{"role": "user", "content": question}], timeout=60.0,
            )
        except Exception:
            return None
        text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        clean, segments, cameras = parse_markers(text)
        if not clean:
            return None
        return {
            "response": clean, "camera_commands": cameras, "segments": segments,
            "_meta": {
                "model": self.model,
                "input_tokens": resp.usage.input_tokens,
                "output_tokens": resp.usage.output_tokens,
                "total_tokens": resp.usage.input_tokens + resp.usage.output_tokens,
                "latency_ms": int((time.time() - start) * 1000),
            },
        }
