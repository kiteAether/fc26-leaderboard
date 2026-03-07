import os

from fastapi import FastAPI, Depends, HTTPException, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from . import models
from . import crud, schemas

Base.metadata.create_all(bind=engine)

app = FastAPI(title="FC26 Leaderboard")

templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


def compute_table(teams: list[models.Team]) -> list[dict]:
    rows = []
    for t in teams:
        p = t.w + t.d + t.l
        gd = t.f - t.a
        pts = (t.w * 3) + t.d

        rows.append(
            dict(
                id=t.id,
                name=t.name,
                avatar_url=t.avatar_url,
                w=t.w,
                d=t.d,
                l=t.l,
                f=t.f,
                a=t.a,
                p=p,
                gd=gd,
                pts=pts,
            )
        )

    # Tie-break: pts → gd → f → name
    rows.sort(
        key=lambda r: (r["pts"], r["gd"], r["f"], r["name"].lower()),
        reverse=True
    )

    for i, r in enumerate(rows, start=1):
        r["rank"] = i

    return rows


def require_admin(key: str | None):
    if key != os.getenv("ADMIN_KEY"):
        raise HTTPException(status_code=403, detail="Not authorized")


# ---------- UI ----------
@app.get("/", response_class=HTMLResponse)
def leaderboard_page(request: Request, db: Session = Depends(get_db)):
    teams = crud.list_teams(db)
    table = compute_table(teams)
    return templates.TemplateResponse(
        "leaderboard.html",
        {"request": request, "table": table}
    )


@app.get("/admin", response_class=HTMLResponse)
def admin_page(
    request: Request,
    key: str = Query(None),
    db: Session = Depends(get_db)
):
    require_admin(key)

    teams = crud.list_teams(db)
    table = compute_table(teams)
    return templates.TemplateResponse(
        "admin.html",
        {"request": request, "table": table, "key": key}
    )


@app.post("/admin/add")
def admin_add_team(
    key: str = Query(None),
    name: str = Form(...),
    avatar_url: str | None = Form(None),
    w: int = Form(0),
    d: int = Form(0),
    l: int = Form(0),
    f: int = Form(0),
    a: int = Form(0),
    db: Session = Depends(get_db),
):
    require_admin(key)

    crud.create_team(
        db,
        schemas.TeamCreate(
            name=name,
            avatar_url=avatar_url,
            w=w,
            d=d,
            l=l,
            f=f,
            a=a,
        ),
    )
    return RedirectResponse(url=f"/admin?key={key}", status_code=303)


@app.post("/admin/update/{team_id}")
def admin_update_team(
    team_id: int,
    key: str = Query(None),
    name: str = Form(...),
    avatar_url: str | None = Form(None),
    w: int = Form(0),
    d: int = Form(0),
    l: int = Form(0),
    f: int = Form(0),
    a: int = Form(0),
    db: Session = Depends(get_db),
):
    require_admin(key)

    team = crud.update_team(
        db,
        team_id,
        schemas.TeamUpdate(
            name=name,
            avatar_url=avatar_url,
            w=w,
            d=d,
            l=l,
            f=f,
            a=a,
        ),
    )

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    return RedirectResponse(url=f"/admin?key={key}", status_code=303)


@app.post("/admin/save-all")
async def admin_save_all(
    request: Request,
    key: str = Query(None),
    db: Session = Depends(get_db),
):
    require_admin(key)

    form = await request.form()
    ids = form.getlist("id")

    for raw_id in ids:
        team_id = int(raw_id)
        team = db.query(models.Team).filter(models.Team.id == team_id).first()

        if not team:
            continue

        team.name = str(form.get(f"name_{team_id}", team.name)).strip()
        avatar_value = str(form.get(f"avatar_url_{team_id}", "")).strip()
        team.avatar_url = avatar_value or None
        team.w = int(form.get(f"w_{team_id}", 0) or 0)
        team.d = int(form.get(f"d_{team_id}", 0) or 0)
        team.l = int(form.get(f"l_{team_id}", 0) or 0)
        team.f = int(form.get(f"f_{team_id}", 0) or 0)
        team.a = int(form.get(f"a_{team_id}", 0) or 0)

    db.commit()
    return RedirectResponse(url=f"/admin?key={key}", status_code=303)


@app.post("/admin/clear-all")
def admin_clear_all(
    key: str = Query(None),
    db: Session = Depends(get_db),
):
    require_admin(key)

    teams = db.query(models.Team).all()
    for team in teams:
        team.w = 0
        team.d = 0
        team.l = 0
        team.f = 0
        team.a = 0

    db.commit()
    return RedirectResponse(url=f"/admin?key={key}", status_code=303)


@app.post("/admin/delete/{team_id}")
def admin_delete_team(
    team_id: int,
    key: str = Query(None),
    db: Session = Depends(get_db)
):
    require_admin(key)

    ok = crud.delete_team(db, team_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Team not found")

    return RedirectResponse(url=f"/admin?key={key}", status_code=303)


# ---------- API ----------
@app.get("/api/teams", response_model=list[schemas.TeamOut])
def api_get_teams(db: Session = Depends(get_db)):
    teams = crud.list_teams(db)
    table = compute_table(teams)

    return [
        schemas.TeamOut(
            id=r["id"],
            rank=r["rank"],
            name=r["name"],
            avatar_url=r.get("avatar_url"),
            p=r["p"],
            gd=r["gd"],
            pts=r["pts"],
            w=r["w"],
            d=r["d"],
            l=r["l"],
            f=r["f"],
            a=r["a"],
        )
        for r in table
    ]


@app.get("/api/leaderboard", response_model=list[schemas.TeamOut])
def api_leaderboard(db: Session = Depends(get_db)):
    return api_get_teams(db)