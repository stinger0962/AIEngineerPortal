"""服务端抽签：加密级随机，可审计；3D 摇签只是装饰。"""
from __future__ import annotations

import secrets

from app.services.qian.signs import all_signs, get_sign  # noqa: F401


def draw_sign() -> dict:
    return secrets.choice(all_signs())
