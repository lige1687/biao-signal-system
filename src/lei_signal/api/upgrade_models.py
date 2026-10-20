"""研究目标的数据约定，不产生交易判断或执行指令。"""
from datetime import date
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Kind = Literal["directional", "concrete"]
Priority = Literal["high", "medium", "low"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Milestone(StrictModel):
    id: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=500)
    done: bool = False


class EvidenceLink(StrictModel):
    label: str = Field(min_length=1, max_length=150)
    url: str = Field(min_length=1, max_length=2000)

    @field_validator("url")
    @classmethod
    def safe_link(cls, value):
        parsed = urlsplit(value)
        if "\\" in value or any(ord(c) < 32 for c in value):
            raise ValueError("链接格式不正确")
        if parsed.scheme in {"https", "http"} and parsed.netloc and not parsed.username:
            return value
        if value.startswith("/library?") or value.startswith("/upgrades?"):
            return value
        if value.startswith("zotero://select/library/"):
            return value
        raise ValueError("只支持网页、报告库、目标或 Zotero 文献链接")


class GoalContent(StrictModel):
    title: str = Field(min_length=1, max_length=150)
    purpose: str = Field(default="", max_length=6000)
    parent_id: str | None = Field(default=None, max_length=100)
    priority: Priority = "medium"
    owner: str = Field(default="待安排", max_length=100)
    target_date: date | None = None
    next_action: str = Field(default="", max_length=2000)
    evidence: str = Field(default="", max_length=10000)
    milestones: list[Milestone] = Field(default_factory=list, max_length=50)
    links: list[EvidenceLink] = Field(default_factory=list, max_length=30)

    @field_validator("milestones")
    @classmethod
    def unique_milestones(cls, values):
        if len({m.id for m in values}) != len(values):
            raise ValueError("完成标准编号不可重复")
        return values


class GoalCreate(GoalContent):
    kind: Kind


class GoalPatch(StrictModel):
    version: int = Field(ge=1)
    title: str | None = None
    purpose: str | None = None
    parent_id: str | None = None
    priority: Priority | None = None
    owner: str | None = None
    target_date: date | None = None
    next_action: str | None = None
    evidence: str | None = None
    milestones: list[Milestone] | None = None
    links: list[EvidenceLink] | None = None

    @model_validator(mode="after")
    def check_nulls(self):
        for key in self.model_fields_set - {"parent_id", "target_date"}:
            if getattr(self, key) is None:
                raise ValueError(f"{key} 不能设为空值")
        return self


class GoalAction(StrictModel):
    version: int = Field(ge=1)
    action: Literal["note", "request_approval", "authorize", "revoke", "start",
                    "pause", "submit_review", "accept", "drop", "reopen"]
    note: str = Field(min_length=1, max_length=6000)
    scope: str = Field(default="", max_length=4000)
