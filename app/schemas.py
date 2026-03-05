from pydantic import BaseModel, Field

class TeamBase(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    w: int = 0
    d: int = 0
    l: int = 0
    f: int = 0
    a: int = 0

class TeamCreate(TeamBase):
    pass

class TeamUpdate(BaseModel):
    name: str | None = None
    w: int | None = None
    d: int | None = None
    l: int | None = None
    f: int | None = None
    a: int | None = None

class TeamOut(TeamBase):
    id: int
    p: int
    gd: int
    pts: int
    rank: int

    class Config:
        from_attributes = True