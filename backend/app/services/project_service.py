from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Project


def slugify(value: str) -> str:
    value = value.lower().strip()
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def list_projects(db: Session) -> list[Project]:
    return list(db.scalars(select(Project).order_by(Project.portfolio_score.desc(), Project.id.asc())).all())


def get_project_by_slug(db: Session, slug: str) -> Project | None:
    return db.scalar(select(Project).where(Project.slug == slug))


def create_project(db: Session, payload: dict) -> Project:
    project = Project(**payload, slug=slugify(payload["title"]))
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def update_project(db: Session, project_id: int, payload: dict) -> Project | None:
    project = db.scalar(select(Project).where(Project.id == project_id))
    if not project:
        return None
    for field, value in payload.items():
        setattr(project, field, value)
    if "title" in payload:
        project.slug = slugify(payload["title"])
    db.commit()
    db.refresh(project)
    return project
