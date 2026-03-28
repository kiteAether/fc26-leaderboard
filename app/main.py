import os
import uuid
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, Request, Form, Query, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from . import models
from . import crud, schemas

Base.metadata.create_all(bind=engine)

app = FastAPI(title="FC26 Leaderboard")

templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

UPLOAD_DIR = Path("app/static/uploads/players")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def ensure_avatar_columns():
    inspector = inspect(engine)
    existing_columns = {col["name"] for col in inspector.get_columns("teams")}

    with engine.begin() as conn:
        if "avatar_blob" not in existing_columns:
            blob_type = "BYTEA" if engine.dialect.name == "postgresql" else "BLOB"
            conn.execute(text(f"ALTER TABLE teams ADD COLUMN avatar_blob {blob_type}"))

        if "avatar_mime" not in existing_columns:
            conn.execute(text("ALTER TABLE teams ADD COLUMN avatar_mime VARCHAR(100)"))


ensure_avatar_columns()


def read_uploaded_avatar(file: UploadFile | None) -> tuple[bytes, str] | None:
    if not file or not file.filename:
        return None

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only jpg, png, webp, and gif images are allowed",
        )

    content = file.file.read()
    if not content:
        return None

    return content, file.content_type


def compute_table(teams: list[models.Team]) -> list[dict]:
    rows = []
    for t in teams:
        w = t.w or 0
        d = t.d or 0
        l = t.l or 0
        f = t.f or 0
        a = t.a or 0

        p = w + d + l
        gd = f - a
        pts = (w * 3) + d

        rows.append(
            dict(
                id=t.id,
                name=t.name,
                avatar_url=t.avatar_url,
                w=w,
                d=d,
                l=l,
                f=f,
                a=a,
                p=p,
                gd=gd,
                pts=pts,
            )
        )

    # Sort order:
    # pts DESC → fewer played first → more wins → fewer losses → name
    rows.sort(
        key=lambda r: (
            -r["pts"],
            r["p"],
            -r["w"],
            r["l"],
            r["name"].lower(),
        )
    )

    # Rank rule:
    # - positive-point teams can share rank when pts and played are the same
    # - zero-point teams rank normally one by one
    prev_positive_pts = None
    prev_p = None
    current_rank = 0

    for i, r in enumerate(rows, start=1):
        if r["pts"] == 0:
            current_rank = i
        elif (
            prev_positive_pts is None
            or r["pts"] != prev_positive_pts
            or r["p"] != prev_p
        ):
            current_rank = i

        r["rank"] = current_rank

        if r["pts"] > 0:
            prev_positive_pts = r["pts"]
            prev_p = r["p"]

    return rows


def require_admin(key: str | None):
    if key != os.getenv("ADMIN_KEY"):
        raise HTTPException(status_code=403, detail="Not authorized")


def avatar_route_for(team_id: int) -> str:
    return f"/api/teams/{team_id}/avatar?v={uuid.uuid4().hex}"


# ---------- UI ----------
@app.get("/", response_class=HTMLResponse)
def leaderboard_page(request: Request, db: Session = Depends(get_db)):
    teams = crud.list_teams(db)
    table = compute_table(teams)
    return templates.TemplateResponse(
        request,
        "leaderboard.html",
        {"table": table},
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
        request,
        "admin.html",
        {"table": table, "key": key},
    )


@app.post("/admin/add")
def admin_add_team(
    key: str = Query(None),
    name: str = Form(...),
    avatar_url: str | None = Form(None),
    avatar_file: UploadFile | None = File(None),
    w: int = Form(0),
    d: int = Form(0),
    l: int = Form(0),
    f: int = Form(0),
    a: int = Form(0),
    db: Session = Depends(get_db),
):
    require_admin(key)

    cleaned_avatar_url = avatar_url.strip() if avatar_url else None
    uploaded_avatar = read_uploaded_avatar(avatar_file)

    team = crud.create_team(
        db,
        schemas.TeamCreate(
            name=name.strip(),
            avatar_url=cleaned_avatar_url,
            w=w,
            d=d,
            l=l,
            f=f,
            a=a,
        ),
    )

    if uploaded_avatar:
        avatar_bytes, avatar_mime = uploaded_avatar
        team.avatar_blob = avatar_bytes
        team.avatar_mime = avatar_mime
        team.avatar_url = avatar_route_for(team.id)
        db.commit()

    return RedirectResponse(url=f"/admin?key={key}", status_code=303)


@app.post("/admin/update/{team_id}")
def admin_update_team(
    team_id: int,
    key: str = Query(None),
    name: str = Form(...),
    avatar_url: str | None = Form(None),
    avatar_file: UploadFile | None = File(None),
    w: int = Form(0),
    d: int = Form(0),
    l: int = Form(0),
    f: int = Form(0),
    a: int = Form(0),
    db: Session = Depends(get_db),
):
    require_admin(key)

    existing_team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not existing_team:
        raise HTTPException(status_code=404, detail="Team not found")

    uploaded_avatar = read_uploaded_avatar(avatar_file)
    cleaned_avatar_url = avatar_url.strip() if avatar_url else None

    team = crud.update_team(
        db,
        team_id,
        schemas.TeamUpdate(
            name=name.strip(),
            avatar_url=cleaned_avatar_url,
            w=w,
            d=d,
            l=l,
            f=f,
            a=a,
        ),
    )

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    if uploaded_avatar:
        avatar_bytes, avatar_mime = uploaded_avatar
        team.avatar_blob = avatar_bytes
        team.avatar_mime = avatar_mime
        team.avatar_url = avatar_route_for(team.id)
        db.commit()
        db.refresh(team)
    else:
        # If user manually switches to an external URL or clears it,
        # remove DB-stored avatar so the source stays consistent.
        if cleaned_avatar_url != existing_team.avatar_url:
            if cleaned_avatar_url:
                team.avatar_blob = None
                team.avatar_mime = None
                team.avatar_url = cleaned_avatar_url
            elif existing_team.avatar_blob:
                team.avatar_blob = None
                team.avatar_mime = None
                team.avatar_url = None
            db.commit()
            db.refresh(team)

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
        previous_avatar_url = team.avatar_url

        team.w = int(form.get(f"w_{team_id}", 0) or 0)
        team.d = int(form.get(f"d_{team_id}", 0) or 0)
        team.l = int(form.get(f"l_{team_id}", 0) or 0)
        team.f = int(form.get(f"f_{team_id}", 0) or 0)
        team.a = int(form.get(f"a_{team_id}", 0) or 0)

        if avatar_value:
            team.avatar_url = avatar_value
            # external URL overrides DB avatar
            if not avatar_value.startswith(f"/api/teams/{team_id}/avatar"):
                team.avatar_blob = None
                team.avatar_mime = None
        else:
            # if user clears avatar_url field manually, clear avatar completely
            if previous_avatar_url:
                team.avatar_url = None
                team.avatar_blob = None
                team.avatar_mime = None

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


@app.post("/admin/delete-all")
def admin_delete_all(
    key: str = Query(None),
    db: Session = Depends(get_db),
):
    require_admin(key)

    db.query(models.Team).delete()
    db.commit()

    return RedirectResponse(url=f"/admin?key={key}", status_code=303)


# ---------- Avatar binary route ----------
@app.get("/api/teams/{team_id}/avatar")
def team_avatar(team_id: int, db: Session = Depends(get_db)):
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team or not team.avatar_blob or not team.avatar_mime:
        raise HTTPException(status_code=404, detail="Avatar not found")

    return Response(
        content=team.avatar_blob,
        media_type=team.avatar_mime,
        headers={"Cache-Control": "public, max-age=31536000"},
    )


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