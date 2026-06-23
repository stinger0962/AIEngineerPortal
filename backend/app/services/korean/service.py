"""Korean course query/progress logic. State is user-scoped; content is shared."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    KoreanConversation,
    KoreanMessage,
    KoreanNode,
    KoreanProgress,
    KoreanRegion,
    MemoryCard,
)


def _ordered_nodes(db: Session, region_id: int) -> list[KoreanNode]:
    return db.scalars(
        select(KoreanNode).where(KoreanNode.region_id == region_id).order_by(KoreanNode.order_index.asc())
    ).all()


def _flat_node_order(db: Session) -> list[KoreanNode]:
    regions = db.scalars(select(KoreanRegion).order_by(KoreanRegion.order_index.asc())).all()
    out: list[KoreanNode] = []
    for r in regions:
        out.extend(_ordered_nodes(db, r.id))
    return out


def _progress_map(db: Session, user_id: int) -> dict[int, KoreanProgress]:
    rows = db.scalars(select(KoreanProgress).where(KoreanProgress.user_id == user_id)).all()
    return {p.node_id: p for p in rows}


def get_map(db: Session, user_id: int) -> list[dict[str, Any]]:
    flat = _flat_node_order(db)
    prog = _progress_map(db, user_id)
    completed_ids = {nid for nid, p in prog.items() if p.status == "completed"}

    status_by_node: dict[int, str] = {}
    for idx, node in enumerate(flat):
        if node.id in completed_ids:
            status_by_node[node.id] = "completed"
        elif idx == 0 or flat[idx - 1].id in completed_ids:
            status_by_node[node.id] = "unlocked"
        else:
            status_by_node[node.id] = "locked"

    regions = db.scalars(select(KoreanRegion).order_by(KoreanRegion.order_index.asc())).all()
    result: list[dict[str, Any]] = []
    for r in regions:
        nodes = _ordered_nodes(db, r.id)
        result.append({
            "slug": r.slug, "title": r.title, "theme": r.theme, "order_index": r.order_index,
            "nodes": [
                {
                    "slug": n.slug, "kind": n.kind, "title": n.title, "order_index": n.order_index,
                    "status": status_by_node[n.id],
                    "stars": prog[n.id].stars if n.id in prog else 0,
                }
                for n in nodes
            ],
        })
    return result


def get_node(db: Session, slug: str) -> KoreanNode | None:
    return db.scalar(select(KoreanNode).where(KoreanNode.slug == slug))


def complete_node(db: Session, user_id: int, slug: str, score: float, stars: int) -> dict[str, Any]:
    node = get_node(db, slug)
    if node is None:
        raise ValueError("unknown node")
    row = db.scalar(
        select(KoreanProgress).where(
            KoreanProgress.user_id == user_id, KoreanProgress.node_id == node.id
        )
    )
    if row is None:
        row = KoreanProgress(user_id=user_id, node_id=node.id)
        db.add(row)
    row.status = "completed"
    row.score = score
    row.stars = max(row.stars or 0, stars)
    row.completed_at = datetime.utcnow()
    _seed_cards_for_node(db, node)
    db.commit()
    return {"slug": slug, "status": "completed", "stars": row.stars}


def _seed_cards_for_node(db: Session, node: KoreanNode) -> None:
    if node.kind != "scene":
        return
    for v in node.content_json.get("new_vocab", []):
        front, back = v.get("ko", ""), v.get("en", "")
        if not front:
            continue
        exists = db.scalar(
            select(MemoryCard).where(MemoryCard.category == "korean", MemoryCard.front_md == front)
        )
        if exists:
            continue
        db.add(MemoryCard(
            front_md=front, back_md=back, category="korean", source_kind="lesson",
            source_title=node.title, difficulty="beginner", tags_json=["korean"],
        ))


def reset_progress(db: Session, user_id: int) -> dict[str, int]:
    conv_ids = db.scalars(
        select(KoreanConversation.id).where(KoreanConversation.user_id == user_id)
    ).all()
    deleted_progress = 0
    for p in db.scalars(select(KoreanProgress).where(KoreanProgress.user_id == user_id)).all():
        db.delete(p); deleted_progress += 1
    for m in db.scalars(select(MemoryCard).where(MemoryCard.category == "korean")).all():
        db.delete(m)
    if conv_ids:
        for msg in db.scalars(select(KoreanMessage).where(KoreanMessage.conversation_id.in_(conv_ids))).all():
            db.delete(msg)
    for c in db.scalars(select(KoreanConversation).where(KoreanConversation.user_id == user_id)).all():
        db.delete(c)
    db.commit()
    return {"deleted_progress": deleted_progress}
