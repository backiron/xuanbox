from uuid import UUID

from pydantic import BaseModel


class SearchResult(BaseModel):
    type: str
    id: UUID
    file_id: UUID | None = None
    title: str
    subtitle: str | None = None
    snippet: str | None = None
    route: str
    source: str
    score: int = 0


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]

