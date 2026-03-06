from sqlalchemy.orm import Session
from .models import Team
from . import schemas


def list_teams(db: Session) -> list[Team]:
    return db.query(Team).order_by(Team.id.asc()).all()


def create_team(db: Session, team_in: schemas.TeamCreate) -> Team:
    team = Team(
        name=team_in.name,
        avatar_url=team_in.avatar_url,
        w=team_in.w,
        d=team_in.d,
        l=team_in.l,
        f=team_in.f,
        a=team_in.a,
    )
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


def update_team(db: Session, team_id: int, team_in: schemas.TeamUpdate) -> Team | None:
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        return None

    team.name = team_in.name
    team.avatar_url = team_in.avatar_url
    team.w = team_in.w
    team.d = team_in.d
    team.l = team_in.l
    team.f = team_in.f
    team.a = team_in.a

    db.commit()
    db.refresh(team)
    return team


def delete_team(db: Session, team_id: int) -> bool:
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        return False

    db.delete(team)
    db.commit()
    return True