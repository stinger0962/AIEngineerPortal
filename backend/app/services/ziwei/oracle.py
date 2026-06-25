"""紫微 AI 解盘：单次 Claude 调用 + 内联镜头标记解析（替代多轮 tool_use 编排）。
组装 人设 + 命盘摘要(含命中格局) + 画像 → Claude 一次成文，解析标记得镜头指令。"""
from __future__ import annotations

import json
import time
from typing import Any, Optional

from .chart_summary import format_chart_summary
from .oracle_tools import current_date_note, parse_markers
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
            current_date_note(),
            "\n\n" + format_chart_summary(chart_json),
        ]
        if portrait:
            parts.append("\n\n【命主画像】（往次解读沉淀，供延续语境）\n" + json.dumps(portrait, ensure_ascii=False))
        parts.append(
            "\n\n## 镜头联动（重要）\n"
            "在解读中用内联标记驱动 3D 画面，标记会被前端解析、不会显示给用户：\n"
            "- 讲到某一宫时，在那句话后紧跟 [[focus:宫名]]，画面飞入该宫。宫名用十二宫标准名："
            "命宫/兄弟/夫妻/子女/财帛/疾厄/迁移/仆役/官禄/田宅/福德/父母。\n"
            "- 回到整体视角时插入 [[overview]]。\n"
            "- 解释生僻术语时插入 [[term:术语|一句话白话解释]]。\n"
            "整段解读只在最关键的 2-4 处飞镜头，标记紧跟在相关句子之后，不要每宫都飞、不要重复飞同一宫。\n"
            "例如：「你命宫紫微坐守，气象不凡。[[focus:命宫]] 再看财帛，武曲化禄，财源稳健。[[focus:财帛]]」\n"
            "## 输出\n解读简洁有重点、直击要害，控制在约 350-550 字（用户明确要求详尽时才展开）。"
            "可读性优先，除上述内联标记外正常说话，不要输出 JSON 或代码块。"
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
        start = time.time()
        try:
            response = self.client.messages.create(
                model=self.model, max_tokens=1200, system=system_prompt,
                messages=claude_messages, timeout=60.0,
            )
        except Exception:
            return None
        text = "".join(b.text for b in response.content if getattr(b, "type", None) == "text")
        clean, segments, camera_commands = parse_markers(text)
        if not clean:
            return None
        return {
            "response": clean,
            "camera_commands": camera_commands,
            "segments": segments,
            "_meta": {
                "model": self.model,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                "latency_ms": int((time.time() - start) * 1000),
                "rounds": 1,
            },
        }
