# app/routers/notes.py
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Note
from app.schemas import NoteCreate, NoteResponse

router = APIRouter(prefix="/api/notes", tags=["notes"])


@router.get("", response_model=list[NoteResponse])
async def list_notes(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[NoteResponse]:
    """List all notes, newest first."""
    try:
        result = await db.execute(select(Note).order_by(Note.created_at.desc()))
        notes = result.scalars().all()
        return [NoteResponse.model_validate(note) for note in notes]
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "PostgreSQL unavailable", "detail": str(e)},
        )


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    note_data: NoteCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NoteResponse:
    """Create a new note."""
    try:
        note = Note(title=note_data.title, body=note_data.body)
        db.add(note)
        await db.commit()
        await db.refresh(note)
        return NoteResponse.model_validate(note)
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "PostgreSQL unavailable", "detail": str(e)},
        )


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a note by ID."""
    try:
        result = await db.execute(select(Note).where(Note.id == note_id))
        note = result.scalar_one_or_none()

        if note is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

        await db.delete(note)
        await db.commit()
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "PostgreSQL unavailable", "detail": str(e)},
        )