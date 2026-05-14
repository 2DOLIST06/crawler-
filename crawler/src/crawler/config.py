from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

DEFAULT_SUSPECT_KEYWORDS = [
    "airplane", "helicopter", "glider", "paragliding", "skydiving", "hot-air-balloon",
    "flight-simulator", "airplane-flying-lesson", "flying-lesson", "activities", "activity",
    "gift", "near", "booking", "voucher",
]


class CrawlConfig(BaseModel):
    start_url: str
    allowed_domain: str
    max_pages: int = 1000
    max_depth: int = 5
    mode: Literal["http", "browser"] = "http"
    output_dir: Path = Path("reports")
    delay: float = 0.0
    timeout: float = 15.0
    respect_robots: bool = True
    include_query_params: bool = False
    user_agent: str = "GenericCrawler/0.1"
    same_host_only: bool = False
    verbose: bool = False
    suspect_keywords: list[str] = Field(default_factory=lambda: DEFAULT_SUSPECT_KEYWORDS.copy())
