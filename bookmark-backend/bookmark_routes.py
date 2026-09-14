"""Bookmark and tag API routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from auth import get_bookmark_creator, get_current_user
from bookmark_service import attach_tags, get_automatic_tags
from bookmark_service import get_user_tag_names, serialize_bookmark
from database import get_db
from metadata import fetch_bookmark_metadata
from models import BookmarkDB, TagDB, UserDB
from schemas import BookmarkRequest, BookmarkUpdateRequest
from tagging import merge_tags


router = APIRouter()


@router.get("/api/bookmarks")
async def get_bookmarks(
    skip: int = 0,
    limit: int = 50,
    tag: Optional[str] = Query(None, description="Filter by tag name"),
    search: Optional[str] = Query(None, description="Search in title, description, or URL"),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    query = db.query(BookmarkDB).filter(BookmarkDB.user_id == current_user.id)
    if tag:
        query = query.filter(BookmarkDB.tags.any(TagDB.name == tag.lower()))
    if search:
        term = f"%{search}%"
        query = query.filter(or_(BookmarkDB.title.ilike(term),
                                 BookmarkDB.description.ilike(term),
                                 BookmarkDB.url.ilike(term)))
    bookmarks = query.order_by(BookmarkDB.created_at.desc()).offset(skip).limit(limit).all()
    return [serialize_bookmark(bookmark) for bookmark in bookmarks]


@router.post("/api/bookmarks", status_code=201)
async def create_bookmark(
    request: BookmarkRequest,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_bookmark_creator),
):
    existing = db.query(BookmarkDB).filter(
        BookmarkDB.url == request.url,
        BookmarkDB.user_id == current_user.id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Bookmark already exists")
    metadata = fetch_bookmark_metadata(request.url)
    if not metadata["success"]:
        raise HTTPException(status_code=400, detail=metadata["error"])
    bookmark = BookmarkDB(
        url=metadata["url"], title=metadata["title"],
        description=metadata["description"], user_id=current_user.id,
    )
    existing_tags = get_user_tag_names(db, current_user.id)
    suggested_tags = await get_automatic_tags(metadata, existing_tags)
    attach_tags(db, bookmark, merge_tags(request.tags, suggested_tags, existing_tags))
    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)
    return serialize_bookmark(bookmark)


@router.put("/api/bookmarks/{bookmark_id}")
async def update_bookmark(
    bookmark_id: int,
    request: BookmarkUpdateRequest,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    bookmark = db.query(BookmarkDB).filter(
        BookmarkDB.id == bookmark_id,
        BookmarkDB.user_id == current_user.id,
    ).first()
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    if request.url is not None and request.url != bookmark.url:
        metadata = fetch_bookmark_metadata(request.url)
        if not metadata["success"]:
            raise HTTPException(status_code=400, detail=metadata["error"])
        bookmark.url = metadata["url"]
        bookmark.title = metadata["title"]
        bookmark.description = metadata["description"]
    if request.tags is not None:
        bookmark.tags = []
        attach_tags(db, bookmark, merge_tags(request.tags, [], []))
    db.commit()
    db.refresh(bookmark)
    return serialize_bookmark(bookmark)


@router.delete("/api/bookmarks/{bookmark_id}")
async def delete_bookmark(
    bookmark_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    bookmark = db.query(BookmarkDB).filter(
        BookmarkDB.id == bookmark_id,
        BookmarkDB.user_id == current_user.id,
    ).first()
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    db.delete(bookmark)
    db.commit()
    return {"success": True, "message": f"Bookmark {bookmark_id} deleted"}


@router.get("/api/tags")
async def get_all_tags(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    bookmarks = db.query(BookmarkDB).filter(BookmarkDB.user_id == current_user.id).all()
    seen = {}
    for bookmark in bookmarks:
        for tag in bookmark.tags:
            seen[tag.id] = tag
    tags = sorted(seen.values(), key=lambda item: item.name)
    return [{"id": tag.id, "name": tag.name} for tag in tags]


@router.get("/health")
async def health_check():
    return {"status": "ok"}
