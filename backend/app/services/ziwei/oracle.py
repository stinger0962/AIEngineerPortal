"""紫微 AI 解盘循环：仿 copilot_loop 的非流式 tool_use 编排。
组装 人设 + 命盘摘要(含命中格局) + 画像 + 近期事件 → Claude，收集镜头指令。"""
from __future__ import annotations

import json
import time
from typing import Any, Optional

from .chart_summary import format_chart_summary
from .oracle_tools import TOOL_SCHEMAS, execute_tool
from .personas import persona_prompt

SCENARIO_FRAMES = {
    "natal": "本命盘解读：以命宫与三方四正立论，兼及十二宫，给出命格总览与人生倾向。",
    "horoscope": "大限/流年解读：以大限定基调、流年看应期，结合命盘格局推演近期运势。",
    "synastry": "合盘解读：比较两人命盘，看夫妻/交友/事业宫与四化交涉，论契合与磨合。",
    "report": "结构化报告：分维度（事业/感情/财运/健康）系统梳理，条理清晰可回看。",
}


class ZiweiOracle:
    def __init__(self, client: Any, model: str):
        self.client = client
        self.model = model

    def _system_prompt(self, chart_json: dict, persona: str, scenario: str, portrait: dict) -> str:
        parts = [
            persona_prompt(persona),
            "\n\n你正在为命主解读一张紫微斗数命盘。下面是排好的盘面与确定性规则检测出的命中格局——"
            "格局部分是程序精确判定的，请务必尊重、不要漏讲或臆造未命中的格局；逐星逐宫的细致论断由你的学养发挥。\n",
            SCENARIO_FRAMES.get(scenario, SCENARIO_FRAMES["natal"]),
            "\n\n" + format_chart_summary(chart_json),
        ]
        if portrait:
            parts.append("\n\n【命主画像】（往次解读沉淀，供延续语境）\n" + json.dumps(portrait, ensure_ascii=False))
        parts.append(
            "\n\n## 镜头联动\n讲到某一宫时调用 focus_palace(该宫) 让 3D 画面飞入；回到全局时 overview()；"
            "遇到生僻术语可用 explain_term 给白话卡。镜头服务于叙述，不必频繁。\n"
            "## 输出\n用清晰中文解读，可读性优先。不要输出 JSON 或代码块，正常说话即可。"
        )
        return "".join(parts)

    def run(
        self,
        chart_json: dict,
        persona: str,
        scenario: str,
        portrait: dict,
        messages: list[dict],
        max_rounds: int = 6,
    ) -> Optional[dict]:
        system_prompt = self._system_prompt(chart_json, persona, scenario, portrait)
        claude_messages = messages[-10:] if len(messages) > 10 else list(messages)
        camera_commands: list[dict] = []
        text_parts: list[str] = []  # 累积每一轮的讲解文字（模型常「边讲边 focus」，文字与工具同 response）
        in_tok = out_tok = 0
        start = time.time()

        def _result(rounds: int) -> dict:
            return {
                "response": "\n\n".join(t for t in (p.strip() for p in text_parts) if t),
                "camera_commands": camera_commands,
                "_meta": {
                    "model": self.model, "input_tokens": in_tok, "output_tokens": out_tok,
                    "total_tokens": in_tok + out_tok, "latency_ms": int((time.time() - start) * 1000),
                    "rounds": rounds,
                },
            }

        for round_num in range(1, max_rounds + 1):
            # 最后一轮去掉工具，逼模型必出文字——否则多宫位问题（如「事业方向」会连续 focus
            # 官禄/财帛/迁移…）可能把 tool_use 轮数耗尽却始终没给最终解读。
            create_kwargs: dict = dict(
                model=self.model, max_tokens=2200, system=system_prompt,
                messages=claude_messages, timeout=40.0,
            )
            if round_num < max_rounds:
                create_kwargs["tools"] = TOOL_SCHEMAS
            try:
                response = self.client.messages.create(**create_kwargs)
            except Exception:
                return _result(round_num) if text_parts else None
            in_tok += response.usage.input_tokens
            out_tok += response.usage.output_tokens

            # 收集本轮的讲解文字（无论是否还要继续 tool_use）
            for block in response.content:
                if block.type == "text" and block.text.strip():
                    text_parts.append(block.text)

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        out = execute_tool(block.name, block.input)
                        if out.get("ok") and "command" in out:
                            camera_commands.append(out["command"])
                        tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(out, ensure_ascii=False)})
                claude_messages.append({"role": "assistant", "content": response.content})
                claude_messages.append({"role": "user", "content": tool_results})
                continue

            return _result(round_num)
        return _result(max_rounds) if text_parts else None
