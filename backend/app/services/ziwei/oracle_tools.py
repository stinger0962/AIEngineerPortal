"""镜头/UI 内联标记解析：把 AI 文本里的 [[focus:宫]] [[overview]] [[term:词|释]] 解析为
干净文本 + 段落（供前端「说到哪飞到哪」回放）+ 扁平指令。替代旧的 tool_use 多轮往返。"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone


def current_date_note() -> str:
    """当前日期注入——模型有知识截止，不注入就会把『今年』当成训练时的年份。
    用东八区（命主多在中国），年/月粒度对运势判断足够。"""
    now = datetime.now(timezone(timedelta(hours=8)))
    return (
        f"\n\n【当前时间】今天是公历 {now.year} 年 {now.month} 月 {now.day} 日（农历需自行换算）。"
        "凡涉及『今年 / 今天 / 现在 / 下半年 / 明年 / 近期 / 流年 / 大限应期』等时间判断，一律以此为准；"
        "切勿凭训练记忆臆断年份（绝不可把当前年份说成往年）。"
    )


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


class StreamMarkerParser:
    """增量解析流式文本里的 [[...]] 标记：feed(delta) 吐出 ('text', 干净文本) / ('camera', 指令) 事件，
    并累积干净全文 + segments + camera_commands 供结束时持久化。处理跨 delta 切断的半个标记。"""

    def __init__(self) -> None:
        self.pending = ""
        self._clean_parts: list[str] = []
        self._seg_text = ""
        self.segments: list[dict] = []
        self.camera_commands: list[dict] = []

    def _emit_text(self, s: str) -> None:
        self._clean_parts.append(s)
        self._seg_text += s

    def feed(self, delta: str) -> list[tuple[str, object]]:
        out: list[tuple[str, object]] = []
        self.pending += delta
        while True:
            i = self.pending.find("[[")
            if i == -1:
                # 没有标记起始；末尾若是半个 "[" 则保留（可能是 "[[" 的前半）
                if self.pending.endswith("["):
                    emit, self.pending = self.pending[:-1], "["
                else:
                    emit, self.pending = self.pending, ""
                if emit:
                    self._emit_text(emit)
                    out.append(("text", emit))
                break
            if i > 0:
                emit = self.pending[:i]
                self._emit_text(emit)
                out.append(("text", emit))
                self.pending = self.pending[i:]
            # pending 现以 "[[" 开头
            j = self.pending.find("]]")
            if j == -1:
                break  # 标记未闭合，等更多 delta
            marker = self.pending[2:j]
            cmd = _to_command(marker)
            self.pending = self.pending[j + 2:]
            if cmd is None:
                continue  # 非法标记丢弃
            if self.camera_commands and self.camera_commands[-1] == cmd:
                continue  # 连续同指令去重
            self.camera_commands.append(cmd)
            self.segments.append({"text": self._seg_text.strip(), "commands": [cmd]})
            self._seg_text = ""
            out.append(("camera", cmd))
        return out

    def finish(self) -> tuple[str, str, list[dict], list[dict]]:
        """结束：把剩余 pending（非半截标记）作为文字补吐。返回 (trailing_text, clean_response, segments, camera_commands)。"""
        trailing = ""
        if self.pending and not self.pending.lstrip().startswith("[["):
            trailing = self.pending
            self._emit_text(self.pending)
        self.pending = ""
        if self._seg_text.strip():
            self.segments.append({"text": self._seg_text.strip(), "commands": []})
            self._seg_text = ""
        clean = "".join(self._clean_parts).strip()
        return trailing, clean, self.segments, self.camera_commands
