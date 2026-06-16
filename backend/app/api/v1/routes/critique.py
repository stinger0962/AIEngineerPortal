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
    output_lang: str = "auto"  # auto | zh | en


class ReviseRequest(BaseModel):
    text: str
    paper_type: str = "research"
    output_lang: str = "auto"


class DocReviewRequest(BaseModel):
    text: str
    paper_type: str = "research"
    output_lang: str = "auto"


class PolishRequest(BaseModel):
    text: str
    paper_type: str = "research"
    output_lang: str = "auto"
    depth: str = "medium"  # light | medium | deep


class PatchRequest(BaseModel):
    text: str
    paper_type: str = "research"
    output_lang: str = "auto"
    depth: str = "medium"


class ProbeRequest(BaseModel):
    text: str
    paper_type: str = "research"
    output_lang: str = "auto"


class ProbeAnswer(BaseModel):
    question: str
    answer: str = ""
    stance: str = "evidence"  # evidence | speculation | skip


class IntegrateRequest(BaseModel):
    text: str
    paper_type: str = "research"
    output_lang: str = "auto"
    answers: list[ProbeAnswer] = []


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
            payload.text, payload.paper_type, payload.output_lang, settings.anthropic_api_key, settings.critique_model
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        logger.exception("Critique evaluate failed")
        raise HTTPException(status_code=500, detail="评估失败，请稍后重试。")


@router.post("/revise")
def revise(payload: ReviseRequest):
    """Assisted single-round revision: produce a writing-layer revision + a pairwise
    verdict on whether it's genuinely better. The user reviews the diff and decides."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="改进服务未配置。")
    try:
        rev = critic.revise(
            payload.text, payload.paper_type, payload.output_lang, settings.anthropic_api_key, settings.critique_model
        )
        verdict = critic.judge_pair(
            payload.text, rev["revised"], payload.paper_type, payload.output_lang,
            settings.anthropic_api_key, settings.critique_model,
        )
        return {"revised": rev["revised"], "changes": rev.get("changes", []), "verdict": verdict}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        logger.exception("Critique revise failed")
        raise HTTPException(status_code=500, detail="改进失败，请稍后重试。")


@router.post("/docreview")
def docreview(payload: DocReviewRequest):
    """Document-level review of the whole paper (footnotes/consistency/dedup) →
    an actionable edit list the author applies in their own editor. No rewrite."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="审阅服务未配置。")
    try:
        return critic.doc_review(
            payload.text, payload.paper_type, payload.output_lang, settings.anthropic_api_key, settings.critique_model
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        logger.exception("Critique docreview failed")
        raise HTTPException(status_code=500, detail="审阅失败，请稍后重试。")


@router.post("/polish")
def polish(payload: PolishRequest):
    """[PROTOTYPE] Deep-improve pipeline: plan → chunk → revise each chunk with the
    global plan injected → stitch. Synchronous (the SSE + plan-gate UI come later)."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="改进服务未配置。")
    try:
        return critic.polish(
            payload.text, payload.paper_type, payload.output_lang, payload.depth,
            settings.anthropic_api_key, settings.critique_model,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        logger.exception("Critique polish failed")
        raise HTTPException(status_code=500, detail="深度改进失败，请稍后重试。")


@router.post("/patch")
def patch(payload: PatchRequest):
    """Patch-style improve: model returns precise find/replace edits over the whole
    doc (no length cap, ~5–10x fewer output tokens than a rewrite), applied
    programmatically. Returns {patched, summary, applied, unapplied, notes}."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="改进服务未配置。")
    try:
        return critic.patch(
            payload.text, payload.paper_type, payload.output_lang, payload.depth,
            settings.anthropic_api_key, settings.critique_model,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        logger.exception("Critique patch failed")
        raise HTTPException(status_code=500, detail="改进失败，请稍后重试。")


@router.post("/probe")
def probe(payload: ProbeRequest):
    """深挖实质 step 1: generate targeted probe questions on the paper's substance-layer
    weaknesses (rigor / originality) — the things AI can't fix without the author's real
    material. Returns {questions:[{location, weakness, question}]}."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="深挖服务未配置。")
    try:
        return critic.probe(
            payload.text, payload.paper_type, payload.output_lang, settings.anthropic_api_key, settings.critique_model
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        logger.exception("Critique probe failed")
        raise HTTPException(status_code=500, detail="提问失败，请稍后重试。")


@router.post("/integrate")
def integrate(payload: IntegrateRequest):
    """深挖实质 step 2: weave the author's answers into the paper as patch-style
    find/replace edits, honoring each answer's stance (evidence/speculation/skip).
    Never fabricates. Returns the same shape as /patch."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="深挖服务未配置。")
    try:
        return critic.integrate(
            payload.text,
            [a.model_dump() for a in payload.answers],
            payload.paper_type,
            payload.output_lang,
            settings.anthropic_api_key,
            settings.critique_model,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        logger.exception("Critique integrate failed")
        raise HTTPException(status_code=500, detail="融入失败，请稍后重试。")
