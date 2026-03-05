from sqlalchemy.orm import Session
from .models import Team
from .schemas import TeamCreate, TeamUpdate

def create_team(db: Session, data: TeamCreate) -> Team:
    team = Team(**data.model_dump())
    db.add(team)
    db.commit()
    db.refresh(team)
    return team

def list_teams(db: Session) -> list[Team]:
    return db.query(Team).all()

def get_team(db: Session, team_id: int) -> Team | None:
    return db.query(Team).filter(Team.id == team_id).first()

def update_team(db: Session, team_id: int, data: TeamUpdate) -> Team | None:
    team = get_team(db, team_id)
    if not team:
        return None
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    for k, v in updates.items():
        setattr(team, k, v)
    db.commit()
    db.refresh(team)
    return team

def delete_team(db: Session, team_id: int) -> bool:
    team = get_team(db, team_id)
    if not team:
        return False
    db.delete(team)
    db.commit()
    return True