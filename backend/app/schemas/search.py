from pydantic import BaseModel


class SearchResultItem(BaseModel):
    category: str  # "asset" | "personnel" | "task" | "spare"
    id: str
    title: str
    subtitle: str
    badge: str
    url: str


class SearchResponse(BaseModel):
    query: str
    total: int
    results: list[SearchResultItem]
