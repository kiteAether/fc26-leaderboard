from pydantic import BaseModel
from typing import Optional


class TeamCreate(BaseModel):
    name: str
    avatar_url: Optional[str] = None

    w: int = 0
    d: int = 0
    l: int = 0
    f: int = 0
    a: int = 0


class TeamUpdate(BaseModel):
    name: str
    avatar_url: Optional[str] = None

    w: int = 0
    d: int = 0
    l: int = 0
    f: int = 0
    a: int = 0


class TeamOut(BaseModel):
    id: int
    rank: int
    name: str
    avatar_url: Optional[str] = None

    p: int
    gd: int
    pts: int

    w: int
    d: int
    l: int
    f: int
    a: int

    class Config:
        from_attributes = True