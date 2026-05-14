from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from crawler_app.database import Base

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    start_url: Mapped[str] = mapped_column(Text)
    allowed_domain: Mapped[str] = mapped_column(String(255))
    same_host_only: Mapped[bool] = mapped_column(Boolean, default=True)
    default_max_pages: Mapped[int] = mapped_column(Integer, default=100)
    default_max_depth: Mapped[int] = mapped_column(Integer, default=3)
    default_mode: Mapped[str] = mapped_column(String(20), default="http")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    runs = relationship("Run", back_populates="project")

class Run(Base):
    __tablename__ = "runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    mode: Mapped[str] = mapped_column(String(20), default="http")
    mission_type: Mapped[str] = mapped_column(String(50), default="simple_crawl")
    max_pages: Mapped[int] = mapped_column(Integer)
    max_depth: Mapped[int] = mapped_column(Integer)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    pages_crawled: Mapped[int] = mapped_column(Integer, default=0)
    links_found: Mapped[int] = mapped_column(Integer, default=0)
    issues_found: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    config_snapshot: Mapped[dict] = mapped_column(JSON, default={})
    project = relationship("Project", back_populates="runs")

class CrawledPage(Base):
    __tablename__ = "pages"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"))
    requested_url: Mapped[str] = mapped_column(Text)
    final_url: Mapped[str] = mapped_column(Text)
    normalized_url: Mapped[str] = mapped_column(Text)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    depth: Mapped[int] = mapped_column(Integer, default=0)
    fetch_mode: Mapped[str] = mapped_column(String(20))
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    title_length: Mapped[int] = mapped_column(Integer, default=0)
    meta_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_description_length: Mapped[int] = mapped_column(Integer, default=0)
    canonical: Mapped[str | None] = mapped_column(Text, nullable=True)
    robots_meta: Mapped[str | None] = mapped_column(String(255), nullable=True)
    h1: Mapped[str | None] = mapped_column(Text, nullable=True)
    h1_count: Mapped[int] = mapped_column(Integer, default=0)
    h2_count: Mapped[int] = mapped_column(Integer, default=0)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    internal_links_count: Mapped[int] = mapped_column(Integer, default=0)
    external_links_count: Mapped[int] = mapped_column(Integer, default=0)
    resource_links_count: Mapped[int] = mapped_column(Integer, default=0)
    found_on: Mapped[dict] = mapped_column(JSON, default=list)
    redirect_chain: Mapped[dict] = mapped_column(JSON, default=list)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    crawled_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Link(Base):
    __tablename__ = "links"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"))
    source_url: Mapped[str] = mapped_column(Text)
    destination_url: Mapped[str] = mapped_column(Text)
    normalized_url: Mapped[str] = mapped_column(Text)
    anchor_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    link_type: Mapped[str] = mapped_column(String(20))
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False)
    is_external: Mapped[bool] = mapped_column(Boolean, default=False)
    is_crawlable: Mapped[bool] = mapped_column(Boolean, default=True)
    rel: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    issue: Mapped[str | None] = mapped_column(Text, nullable=True)
    found_at_depth: Mapped[int] = mapped_column(Integer, default=0)

class Resource(Base):
    __tablename__ = "resources"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"))
    source_url: Mapped[str] = mapped_column(Text)
    resource_url: Mapped[str] = mapped_column(Text)
    resource_type: Mapped[str] = mapped_column(String(50))
    tag_name: Mapped[str] = mapped_column(String(50))
    attribute_name: Mapped[str] = mapped_column(String(50))

class Issue(Base):
    __tablename__ = "issues"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"))
    issue_type: Mapped[str] = mapped_column(String(100))
    severity: Mapped[str] = mapped_column(String(20))
    url: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
