"""镜头/UI 内联标记解析：把 AI 文本里的 [[focus:宫]] [[overview]] [[term:词|释]] 解析为
干净文本 + 段落（供前端「说到哪飞到哪」回放）+ 扁平指令。替代旧的 tool_use 多轮往返。"""
from __future__ import annotations

import re

VALID_PALACES = {"命宫", "兄弟", "夫妻", "子女", "财帛", "疾厄", "迁移", "仆役", "交友", "官禄", "田宅", "福德", "父母"}
_PALACE_ALIAS = {"交友": "仆役"}  # iztro 命盘用「仆役」；模型可能说「交友」，归一化到命盘实际宫名

_MARKER_RE = re.compile(r"\[\[(focus:[^\]\n]+?|overview|term:[^\]\n]+?)\]\]")


def _to_command(raw: str) -> dict | None:
    if raw == "overview":
        return {"type": "overview"}
    if raw.startswith("focus:"):
        palace = raw[len("focus:"):].strip()
        palace = _PALACE_ALIAS.get(palace, palace)
        if palace not in VALID_PALACES:
            return None
        return {"type": "focus_palace", "palace": palace}
    if raw.startswith("term:"):
        body = raw[len("term:"):]
        term, _, expl = body.partition("|")
        term, expl = term.strip(), expl.strip()
        if not term or not expl:
            return None  # 缺术语或解释 → 降级为纯文字，不弹空白卡
        return {"type": "explain_term", "term": term, "explanation": expl}
    return None


def parse_markers(text: str) -> tuple[str, list[dict], list[dict]]:
    """→ (clean_response, segments, camera_commands)。
    segments[i] = {text, commands}：该段文字铺完后触发其 commands（位置即叙述位置）。"""
    segments: list[dict] = []
    camera_commands: list[dict] = []
    buf = ""
    pos = 0
    for m in _MARKER_RE.finditer(text):
        cmd = _to_command(m.group(1))
        buf += text[pos:m.start()]
        pos = m.end()
        if cmd is None:
            continue  # 非法标记（如未知宫位）→ 丢弃指令，文字继续累积
        # 去重：与上一条镜头指令完全相同（如连飞同一宫）则并入文字、不重复触发
        if camera_commands and camera_commands[-1] == cmd:
            continue
        camera_commands.append(cmd)
        segments.append({"text": buf.strip(), "commands": [cmd]})
        buf = ""
    buf += text[pos:]
    if buf.strip():
        segments.append({"text": buf.strip(), "commands": []})
    response = _MARKER_RE.sub("", text).strip()
    if not segments and response:
        segments = [{"text": response, "commands": []}]
    return response, segments, camera_commands
