from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.tag import Tag, TagLink
from app.models.user import User
from app.schemas.tag import TagAttachRequest, TagCreateRequest, TagUpdateRequest
from app.services.audit_service import write_audit_log


async def list_tags(db: AsyncSession, owner: User) -> list[Tag]:
    result = await db.scalars(select(Tag).where(Tag.owner_id == owner.id).order_by(Tag.name.asc()))
    return list(result)


async def list_tag_links(db: AsyncSession, owner: User, target_type: str | None = None) -> list[TagLink]:
    query = select(TagLink).where(TagLink.owner_id == owner.id)
    if target_type:
        query = query.where(TagLink.target_type == target_type)
    result = await db.scalars(query)
    return list(result)


async def create_tag(db: AsyncSession, owner: User, payload: TagCreateRequest) -> Tag:
    tag = Tag(owner_id=owner.id, name=payload.name, color=payload.color)
    db.add(tag)
    await db.flush()
    await write_audit_log(db, action="tag.create", actor_user_id=owner.id, target_type="tag", target_id=str(tag.id))
    await db.commit()
    await db.refresh(tag)
    return tag


async def update_tag(db: AsyncSession, owner: User, tag_id: UUID, payload: TagUpdateRequest) -> Tag:
    tag = await db.scalar(select(Tag).where(Tag.id == tag_id, Tag.owner_id == owner.id))
    if tag is None:
        raise AppError("tag_not_found", "Tag not found", 404)
    if payload.name is not None:
        tag.name = payload.name
    if payload.color is not None:
        tag.color = payload.color
    await write_audit_log(db, action="tag.update", actor_user_id=owner.id, target_type="tag", target_id=str(tag.id))
    await db.commit()
    await db.refresh(tag)
    return tag


async def attach_tag(db: AsyncSession, owner: User, tag_id: UUID, payload: TagAttachRequest) -> TagLink:
    tag = await db.scalar(select(Tag).where(Tag.id == tag_id, Tag.owner_id == owner.id))
    if tag is None:
        raise AppError("tag_not_found", "Tag not found", 404)
    existing = await db.scalar(
        select(TagLink).where(
            TagLink.tag_id == tag_id,
            TagLink.target_type == payload.target_type,
            TagLink.target_id == payload.target_id,
            TagLink.owner_id == owner.id,
        )
    )
    if existing:
        return existing
    link = TagLink(owner_id=owner.id, tag_id=tag_id, target_type=payload.target_type, target_id=payload.target_id)
    db.add(link)
    await write_audit_log(db, action="tag.attach", actor_user_id=owner.id, target_type=payload.target_type, target_id=str(payload.target_id))
    await db.commit()
    await db.refresh(link)
    return link
