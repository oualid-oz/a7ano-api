from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    sort: str | None = None
    search: str | None = None


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int
    pages: int


class PaginatedResponse[T](BaseModel):
    data: list[T]
    pagination: PaginationMeta


class BaseFilter(BaseModel):
    model_config = {"extra": "allow"}
