from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from . import models
from . import crud, schemas

Base.metadata.create_all(bind=engine)

app = FastAPI(title="FC26 Leaderboard")

# UI setup
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
                id=t.id, name=t.name,
                w=t.w, d=t.d, l=t.l,
                f=t.f, a=t.a,
                p=p, gd=gd, pts=pts
            )
        )

    rows.sort(key=lambda r: (r["pts"], r["gd"], r["f"]), reverse=True)
    for i, r in enumerate(rows, start=1):
        r["rank"] = i
    return rows


# ---------- UI PAGES ----------
@app.get("/", response_class=HTMLResponse)
def leaderboard_page(request: Request, db: Session = Depends(get_db)):
    teams = crud.list_teams(db)
    table = compute_table(teams)
    return templates.TemplateResponse("leaderboard.html", {"request": request, "table": table})


@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request, db: Session = Depends(get_db)):
    teams = crud.list_teams(db)
    table = compute_table(teams)
    return templates.TemplateResponse("admin.html", {"request": request, "table": table})


@app.post("/admin/add")
def admin_add_team(
    name: str = Form(...),
    w: int = Form(0),
    d: int = Form(0),
    l: int = Form(0),
    f: int = Form(0),
    a: int = Form(0),
    db: Session = Depends(get_db),
):
    crud.create_team(db, schemas.TeamCreate(name=name, w=w, d=d, l=l, f=f, a=a))
    return RedirectResponse(url="/admin", status_code=303)


@app.post("/admin/update/{team_id}")
def admin_update_team(
    team_id: int,
    name: str = Form(...),
    w: int = Form(0),
    d: int = Form(0),
    l: int = Form(0),
    f: int = Form(0),
    a: int = Form(0),
    db: Session = Depends(get_db),
):
    team = crud.update_team(db, team_id, schemas.TeamUpdate(name=name, w=w, d=d, l=l, f=f, a=a))
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return RedirectResponse(url="/admin", status_code=303)


@app.post("/admin/delete/{team_id}")
def admin_delete_team(team_id: int, db: Session = Depends(get_db)):
    ok = crud.delete_team(db, team_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Team not found")
    return RedirectResponse(url="/admin", status_code=303)


# ---------- API ----------
@app.get("/api/teams", response_model=list[schemas.TeamOut])
def api_get_teams(db: Session = Depends(get_db)):
    teams = crud.list_teams(db)
    table = compute_table(teams)

    # TeamOut requires rank included:
    return [
        schemas.TeamOut(
            id=r["id"], name=r["name"], w=r["w"], d=r["d"], l=r["l"], f=r["f"], a=r["a"],
            p=r["p"], gd=r["gd"], pts=r["pts"], rank=r["rank"]
        )
        for r in table
    ]
@app.get("/api/leaderboard", response_model=list[schemas.TeamOut])
def api_leaderboard(db: Session = Depends(get_db)):
    return api_get_teams(db)