"""评审 Critique routes: extract text from an uploaded file + run the rubric evaluation."""
from __future__ import annotations

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.core.config import get_settings
from app.services import essay_critic_service as critic

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/critique", tags=["critique"])

_MAX_UPLOAD = 10 * 1024 * 1024  # 10 MB


class EvaluateRequest(BaseModel):
    text: str
    paper_type: str = "research"


@router.post("/extract")
async def extract(file: UploadFile = File(...)):
    """Parse an uploaded .docx/.pdf/.md/.txt to plain text so the user can review
    it in the editor before evaluating."""
    raw = await file.read()
    if len(raw) > _MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="文件过大（上限 10MB）。")
    try:
        text = critic.extract_text(file.filename or "", raw)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        logger.exception("Critique extract failed")
        raise HTTPException(status_code=422, detail="无法解析该文件，请改用 .docx / .pdf / .md / .txt。")
    if not text.strip():
        raise HTTPException(status_code=422, detail="未能从文件中提取到文字（可能是扫描版 PDF）。")
    return {"text": text, "filename": file.filename}


@router.post("/evaluate")
def evaluate(payload: EvaluateRequest):
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="评估服务未配置。")
    try:
        return critic.evaluate(
            payload.text, payload.paper_type, settings.anthropic_api_key, settings.ai_model
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        logger.exception("Critique evaluate failed")
        raise HTTPException(status_code=500, detail="评估失败，请稍后重试。")
