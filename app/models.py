from sqlalchemy import Column, Integer, String
from .db import Base

class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)

    w = Column(Integer, default=0)
    d = Column(Integer, default=0)
    l = Column(Integer, default=0)

    f = Column(Integer, default=0)  # goals for
    a = Column(Integer, default=0)  # goals against 

    avatar_url = Column(String, nullable=True)