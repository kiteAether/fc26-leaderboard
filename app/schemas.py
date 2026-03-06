from pydantic import BaseModel
from typing import Optional

class TeamCreate(BaseModel):
    name: str
    w: int = 0
    d: int = 0
    l: int = 0
    f: int = 0
    a: int = 0
    avatar_url: Optional[str] = None   # ✅

class TeamUpdate(BaseModel):
    name: str
    w: int = 0
    d: int = 0
    l: int = 0
    f: int = 0
    a: int = 0
    avatar_url: Optional[str] = None   # ✅

class TeamOut(BaseModel):
    id: int
    rank: int
    name: str
    p: int
    gd: int
    pts: int
    w: int
    d: int
    l: int
    f: int
    a: int
    avatar_url: Optional[str] = None   # ✅

