"""一次性生成观音灵签 100 签语料 → app/services/qian/signs.py。
公版语料以 GitHub snjor-kii/guanyinqiuqian 的 lottery-data.js 为基线，
字段映射 id/title/type→(grade,palace)/poetry/meaning/holy。只取公版诗文。
用法：python backend/scripts/build_qian_signs.py

源文件已预取至 scripts/lottery-data.js（via curl -k）；脚本优先读取本地缓存，
如无则尝试标准 HTTPS 拉取。
"""
from __future__ import annotations

import re
import urllib.request
from pathlib import Path

SRC = "https://raw.githubusercontent.com/snjor-kii/guanyinqiuqian/main/lottery-data.js"
LOCAL = Path(__file__).resolve().parent / "lottery-data.js"
OUT = Path(__file__).resolve().parents[1] / "app" / "services" / "qian" / "signs.py"

_PALACE_RE = re.compile(r"^(.*?)([子丑寅卯辰巳午未申酉戌亥]宫)$")
_ENTRY_RE = re.compile(
    r"id:\s*(\d+).*?title:\s*\"([^\"]*)\".*?type:\s*\"([^\"]*)\""
    r".*?poetry:\s*\"([^\"]*)\".*?meaning:\s*\"([^\"]*)\".*?explanation:\s*\"([^\"]*)\"",
    re.S,
)


def fetch_raw() -> str:
    """Read local cache if available; otherwise fetch from GitHub."""
    if LOCAL.exists():
        print(f"  (using local cache: {LOCAL})")
        return LOCAL.read_text(encoding="utf-8")
    return urllib.request.urlopen(SRC, timeout=60).read().decode("utf-8")


def main() -> None:
    raw = fetch_raw()
    entries = _ENTRY_RE.findall(raw)
    if len(entries) != 100:
        raise SystemExit(f"期望 100 签，实得 {len(entries)} —— 源结构可能变了，请检查 {SRC}")
    signs = []
    for _id, title, typ, poetry, meaning, holy in entries:
        m = _PALACE_RE.match(typ.strip())
        grade, palace = (m.group(1), m.group(2)) if m else (typ.strip(), "")
        signs.append({
            "id": int(_id), "grade": grade.strip(), "palace": palace,
            "title": title.strip(), "poetry": poetry.strip(),
            "meaning": meaning.strip(), "holy": holy.strip(),
        })
    signs.sort(key=lambda s: s["id"])
    body = ",\n".join(
        "    {"
        f"\"id\": {s['id']}, \"grade\": \"{s['grade']}\", \"palace\": \"{s['palace']}\", "
        f"\"title\": \"{s['title']}\", \"poetry\": \"{s['poetry']}\", "
        f"\"meaning\": \"{s['meaning']}\", \"holy\": \"{s['holy']}\""
        "}"
        for s in signs
    )
    OUT.write_text(
        '"""观音灵签 100 签（公版诗文，由 scripts/build_qian_signs.py 生成；勿手改）。"""\n'
        "from __future__ import annotations\n\n"
        "SIGNS: list[dict] = [\n" + body + ",\n]\n\n"
        "_BY_ID = {s[\"id\"]: s for s in SIGNS}\n\n\n"
        "def all_signs() -> list[dict]:\n    return SIGNS\n\n\n"
        "def get_sign(sign_id: int) -> dict | None:\n    return _BY_ID.get(sign_id)\n",
        encoding="utf-8",
    )
    print(f"✓ 写出 {OUT}（{len(signs)} 签）")


if __name__ == "__main__":
    main()
