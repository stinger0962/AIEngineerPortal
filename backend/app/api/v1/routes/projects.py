from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import ProjectIn, ProjectOut
from app.services.project_service import create_project, get_project_by_slug, list_projects, update_project

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=List[ProjectOut])
def get_projects(db: Session = Depends(get_db)) -> List[ProjectOut]:
    return [ProjectOut.model_validate(project) for project in list_projects(db)]


@router.get("/{slug}", response_model=ProjectOut)
def get_project(slug: str, db: Session = Depends(get_db)) -> ProjectOut:
    project = get_project_by_slug(db, slug)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectOut.model_validate(project)


@router.post("", response_model=ProjectOut)
def add_project(payload: ProjectIn, db: Session = Depends(get_db)) -> ProjectOut:
    return ProjectOut.model_validate(create_project(db, payload.model_dump()))


@router.patch("/{project_id}", response_model=ProjectOut)
def edit_project(project_id: int, payload: ProjectIn, db: Session = Depends(get_db)) -> ProjectOut:
    project = update_project(db, project_id, payload.model_dump())
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectOut.model_validate(project)
