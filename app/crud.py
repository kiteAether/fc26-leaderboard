from sqlalchemy.orm import Session
from .models import Team
from .schemas import TeamCreate, TeamUpdate

def create_team(db, team_in):
    team = Team(
        name=team_in.name,
        w=team_in.w, d=team_in.d, l=team_in.l,
        f=team_in.f, a=team_in.a,
        avatar_url=team_in.avatar_url,   # ✅
    )
    db.add(team)
    db.commit()
    db.refresh(team)
    return team

def update_team(db, team_id, team_in):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        return None
    team.name = team_in.name
    team.w = team_in.w; team.d = team_in.d; team.l = team_in.l
    team.f = team_in.f; team.a = team_in.a
    team.avatar_url = team_in.avatar_url   # ✅
    db.commit()
    db.refresh(team)
    return team