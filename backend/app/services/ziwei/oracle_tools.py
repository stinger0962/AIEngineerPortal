"""Oracle 镜头/UI 工具：Claude 调用以驱动 3D（消费在 Phase 3b；本期仅收集指令）。"""
from __future__ import annotations

VALID_PALACES = {"命宫", "兄弟", "夫妻", "子女", "财帛", "疾厄", "迁移", "交友", "官禄", "田宅", "福德", "父母"}

TOOL_SCHEMAS: list[dict] = [
    {
        "name": "focus_palace",
        "description": "把 3D 镜头飞入并聚焦到命主某一宫位。当你的解读聚焦到某宫时调用，让画面跟随你的话语。",
        "input_schema": {
            "type": "object",
            "properties": {"palace": {"type": "string", "description": "宫位名，如 命宫、官禄、夫妻"}},
            "required": ["palace"],
        },
    },
    {
        "name": "overview",
        "description": "把镜头拉回整盘总览。在开场总评、或从单宫话题回到全局时调用。",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "explain_term",
        "description": "为一个紫微术语弹出白话解释卡片，帮助不懂命理的用户。",
        "input_schema": {
            "type": "object",
            "properties": {"term": {"type": "string"}, "explanation": {"type": "string", "description": "一句话白话解释"}},
            "required": ["term", "explanation"],
        },
    },
]


def execute_tool(name: str, tool_input: dict) -> dict:
    """执行（=校验并回 ack）。真正的动画消费在前端。返回结构化指令供路由收集。"""
    if name == "focus_palace":
        palace = tool_input.get("palace", "")
        if palace not in VALID_PALACES:
            return {"ok": False, "error": f"未知宫位：{palace}"}
        return {"ok": True, "command": {"type": "focus_palace", "palace": palace}}
    if name == "overview":
        return {"ok": True, "command": {"type": "overview"}}
    if name == "explain_term":
        return {"ok": True, "command": {"type": "explain_term", "term": tool_input.get("term", ""), "explanation": tool_input.get("explanation", "")}}
    return {"ok": False, "error": f"未知工具：{name}"}
