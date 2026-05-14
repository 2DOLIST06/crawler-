from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class FetchResult(BaseModel):
    requested_url: str
    final_url: str
    status_code: int | None = None
    content_type: str | None = None
    html: str = ""
    redirect_chain: list[str] = Field(default_factory=list)
    error: str | None = None


class ResourceRecord(BaseModel):
    source_url: str
    resource_url: str
    resource_type: str
    tag_name: str
    attribute_name: str


class LinkRecord(BaseModel):
    source_url: str
    destination_url: str
    normalized_url: str | None
    anchor_text: str
    link_type: str
    is_internal: bool
    is_external: bool
    is_crawlable: bool
    rel: str
    target: str
    status_code: int | None = None
    issue: str | None = None
    found_at_depth: int


class PageRecord(BaseModel):
    requested_url: str
    final_url: str
    normalized_url: str
    status_code: int | None
    content_type: str | None
    depth: int
    fetch_mode: str
    title: str
    title_length: int
    meta_description: str
    meta_description_length: int
    canonical: str
    robots_meta: str
    h1_list: list[str]
    h1_count: int
    h2_list: list[str]
    h2_count: int
    hreflang_list: list[str]
    internal_links_count: int
    external_links_count: int
    resource_links_count: int
    word_count: int
    found_on: list[str]
    redirect_chain: list[str]
    error: str | None
    crawled_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class IssueRecord(BaseModel):
    issue_type: str
    severity: Literal["low", "medium", "high"]
    url: str
    source_url: str
    details: str
