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


def _progress_map(db: Session, user_id: int) -> dict[int, KoreanProgress]:
    rows = db.scalars(select(KoreanProgress).where(KoreanProgress.user_id == user_id)).all()
    return {p.node_id: p for p in rows}


def get_map(db: Session, user_id: int) -> list[dict[str, Any]]:
    """Regions with per-node status. Nodes form a single flat sequence in region
    order, then node order within a region. The first node is unlocked; each later
    node unlocks once the node before it in that sequence is completed."""
    regions = db.scalars(select(KoreanRegion).order_by(KoreanRegion.order_index.asc())).all()
    all_nodes = db.scalars(
        select(KoreanNode).order_by(KoreanNode.region_id.asc(), KoreanNode.order_index.asc())
    ).all()
    nodes_by_region: dict[int, list[KoreanNode]] = {}
    for n in all_nodes:
        nodes_by_region.setdefault(n.region_id, []).append(n)

    flat: list[KoreanNode] = []
    for r in regions:
        flat.extend(nodes_by_region.get(r.id, []))

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

    result: list[dict[str, Any]] = []
    for r in regions:
        result.append({
            "slug": r.slug, "title": r.title, "theme": r.theme, "order_index": r.order_index,
            "nodes": [
                {
                    "slug": n.slug, "kind": n.kind, "title": n.title, "order_index": n.order_index,
                    "status": status_by_node[n.id],
                    "stars": prog[n.id].stars if n.id in prog else 0,
                }
                for n in nodes_by_region.get(r.id, [])
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
        db.delete(p)
        deleted_progress += 1
    # MemoryCard is a platform-shared table with no user_id column (used by the
    # review system across the whole platform). Korean cards are therefore cleared
    # globally by design — this is intentional for a single-user platform. In
    # contrast, KoreanProgress and KoreanConversation are user-scoped (deleted
    # only for the calling user, above).
    for m in db.scalars(select(MemoryCard).where(MemoryCard.category == "korean")).all():
        db.delete(m)
    if conv_ids:
        for msg in db.scalars(select(KoreanMessage).where(KoreanMessage.conversation_id.in_(conv_ids))).all():
            db.delete(msg)
    for c in db.scalars(select(KoreanConversation).where(KoreanConversation.user_id == user_id)).all():
        db.delete(c)
    db.commit()
    return {"deleted_progress": deleted_progress}
