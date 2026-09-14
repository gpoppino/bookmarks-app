"""Bookmark serialization and automatic-tagging operations."""

import logging
from urllib.parse import urlparse

from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from auth import as_utc
from config import load_tagging_environment
from models import BookmarkDB, TagDB, bookmark_tag_association
from tagging import MAX_EXISTING_TAGS, TaggingContext, build_tag_suggester


logger = logging.getLogger(__name__)
tag_suggester = build_tag_suggester(load_tagging_environment())


def serialize_bookmark(bookmark: BookmarkDB) -> dict:
    return {
        "id": bookmark.id,
        "url": bookmark.url,
        "title": bookmark.title,
        "description": bookmark.description,
        "created_at": as_utc(bookmark.created_at),
        "tags": [tag.name for tag in bookmark.tags],
    }


def get_user_tag_names(db: Session, user_id: int) -> list[str]:
    rows = (
        db.query(TagDB.name)
        .join(bookmark_tag_association, TagDB.id == bookmark_tag_association.c.tag_id)
        .join(BookmarkDB, BookmarkDB.id == bookmark_tag_association.c.bookmark_id)
        .filter(BookmarkDB.user_id == user_id)
        .distinct()
        .order_by(TagDB.name)
        .limit(MAX_EXISTING_TAGS)
        .all()
    )
    return [name for (name,) in rows]


async def get_automatic_tags(metadata: dict, existing_tags: list[str]) -> list[str]:
    if not tag_suggester.enabled:
        return []
    context = TaggingContext(
        domain=(urlparse(metadata["url"]).hostname or "").lower(),
        title=metadata["title"],
        description=metadata["description"],
        existing_tags=tuple(existing_tags),
    )
    try:
        return await run_in_threadpool(tag_suggester.suggest, context)
    except Exception as error:
        logger.warning(
            "Automatic tagging failed (%s); saving bookmark without suggestions",
            type(error).__name__,
        )
        return []


def attach_tags(db: Session, bookmark: BookmarkDB, tag_names: list[str]) -> None:
    for clean_tag in tag_names:
        db_tag = db.query(TagDB).filter(TagDB.name == clean_tag).first()
        if not db_tag:
            db_tag = TagDB(name=clean_tag)
        bookmark.tags.append(db_tag)
