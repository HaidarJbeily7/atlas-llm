"""FastAPI app: serves experiment data + annotation/review API for investigation.

Run locally::

    uvicorn atlas_backend.app:app --reload --port 8000

Or via the installed script::

    atlas-backend
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import auth, db, seed as seed_module, summary as summary_module
from .database import get_db

# ---- Config --------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DATA_DIR = REPO_ROOT / "website" / "public" / "data"
DEFAULT_WEB_DIST = REPO_ROOT / "website" / "dist"

DATA_DIR = Path(os.environ.get("ATLAS_DATA_DIR", DEFAULT_DATA_DIR))
WEB_DIST = Path(os.environ.get("ATLAS_WEB_DIST", DEFAULT_WEB_DIST))


# ---- Schemas -------------------------------------------------------------

class AnnotationIn(BaseModel):
    label: str = Field("", description="Short tag, e.g. 'false_positive', 'confirmed', 'needs_context'")
    note: str = Field("", description="Free-form investigation note")


class AnnotationPatch(BaseModel):
    label: str | None = None
    note: str | None = None


class AnnotationOut(BaseModel):
    id: int
    finding_id: str
    label: str
    note: str
    author: str
    created_at: str
    updated_at: str


class VoteIn(BaseModel):
    status: str = Field(..., description=f"One of {sorted(db.VALID_STATUSES)}")
    rationale: str = ""


class VoteOut(BaseModel):
    id: int
    finding_id: str
    user_id: int
    username: str
    status: str
    rationale: str
    created_at: str
    updated_at: str


class ReviewSummaryOut(BaseModel):
    finding_id: str
    settlement: str
    status: str | None
    vote_count: int
    distinct_voter_count: int
    votes: list[VoteOut]
    my_vote: VoteOut | None = None


class UserOut(BaseModel):
    id: int
    username: str
    created_at: str


class LoginIn(BaseModel):
    username: str
    password: str


class LoginOut(BaseModel):
    token: str
    expires_at: str
    user: UserOut


# ---- App -----------------------------------------------------------------

app = FastAPI(
    title="ATLAS Investigation API",
    version="0.1.0",
    description="Investigate and annotate findings from ATLAS red-team experiments.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "data_dir": str(DATA_DIR),
        "data_available": DATA_DIR.exists(),
    }


# ---- Experiments (DB-backed) --------------------------------------------

class SeedRequest(BaseModel):
    path: str = Field(..., description="Path to a raw experiment directory (with experiment_meta.json)")
    recursive: bool = Field(False, description="Seed every child directory containing experiment_meta.json")


class SeedResultOut(BaseModel):
    experiment_id: str
    timestamp: str
    scans_seeded: int
    findings_seeded: int
    warnings: list[str]
    source_dir: str


@app.get("/api/experiments")
def list_experiments(session: Session = Depends(get_db)) -> list[dict]:
    return db.list_experiments(session)


@app.get("/api/experiments/{exp_id}")
def get_experiment_detail(exp_id: str, session: Session = Depends(get_db)) -> dict:
    result = summary_module.get_summary(session, exp_id)
    if result is None:
        raise HTTPException(404, f"Experiment {exp_id} not found")
    return result


@app.get("/api/experiments/{exp_id}/findings")
def list_experiment_findings(
    exp_id: str,
    model: str | None = Query(None),
    probe: str | None = Query(None),
    passed: bool | None = Query(None),
    session: Session = Depends(get_db),
) -> list[dict]:
    if db.get_experiment(session, exp_id) is None:
        raise HTTPException(404, f"Experiment {exp_id} not found")
    return db.list_findings_for_experiment(
        session, exp_id, model=model, probe=probe, passed=passed
    )


@app.get("/api/experiments/{exp_id}/findings/{finding_id}")
def get_experiment_finding(
    exp_id: str,
    finding_id: str,
    user: dict | None = Depends(auth.get_current_user_optional),
    session: Session = Depends(get_db),
) -> dict:
    row = db.get_finding(session, finding_id)
    if row is None or row["experiment_id"] != exp_id:
        raise HTTPException(404, f"Finding {finding_id} not found in experiment {exp_id}")
    data = json.loads(row["detail_json"])
    data["annotations"] = db.list_annotations(session, finding_id)
    data["review"] = _review_payload(session, finding_id, user)
    return data


@app.delete("/api/experiments/{exp_id}", status_code=204)
def delete_experiment(exp_id: str, session: Session = Depends(get_db)) -> None:
    if not db.delete_experiment(session, exp_id):
        raise HTTPException(404, f"Experiment {exp_id} not found")
    summary_module.invalidate(exp_id)


@app.post("/api/experiments/seed", response_model=list[SeedResultOut])
def seed_experiments(body: SeedRequest, session: Session = Depends(get_db)) -> list[dict]:
    try:
        results = seed_module.seed_from_directory(
            session, Path(body.path), recursive=body.recursive
        )
    except (FileNotFoundError, NotADirectoryError, ValueError) as e:
        raise HTTPException(400, str(e)) from e
    for r in results:
        summary_module.invalidate(r.experiment_id)
    return [r.to_dict() for r in results]


# ---- Summary & findings (computed from DB) -------------------------------

@app.get("/api/summary")
def get_summary(session: Session = Depends(get_db)) -> dict:
    exp_id = db.get_latest_experiment_id(session)
    if exp_id is None:
        raise HTTPException(
            404,
            "No experiments in DB — seed data with "
            "`atlas-backend-seed <dir>` (pointing at a raw experiment directory).",
        )
    result = summary_module.get_summary(session, exp_id)
    if result is None:
        raise HTTPException(500, "Failed to compute summary")
    return result


@app.get("/api/findings/{finding_id}")
def get_finding(
    finding_id: str,
    user: dict | None = Depends(auth.get_current_user_optional),
    session: Session = Depends(get_db),
) -> dict:
    row = db.get_finding(session, finding_id)
    if row is None:
        raise HTTPException(404, f"Finding {finding_id} not found")
    data = json.loads(row["detail_json"])
    data["annotations"] = db.list_annotations(session, finding_id)
    data["review"] = _review_payload(session, finding_id, user)
    return data


# ---- Auth ---------------------------------------------------------------

def _user_out(user: dict) -> dict:
    return {"id": user["id"], "username": user["username"], "created_at": user["created_at"]}


@app.post("/api/auth/login", response_model=LoginOut)
def login_route(body: LoginIn, session: Session = Depends(get_db)) -> dict:
    try:
        user, token, expires_at = auth.login(session, body.username, body.password)
    except ValueError as e:
        raise HTTPException(401, str(e)) from e
    return {"token": token, "expires_at": expires_at, "user": _user_out(user)}


@app.post("/api/auth/logout", status_code=204)
def logout_route(
    authorization: str | None = Header(None),
    session: Session = Depends(get_db),
) -> None:
    token = auth._extract_bearer(authorization)
    if token:
        db.delete_session(session, token)


@app.get("/api/auth/me", response_model=UserOut)
def me(user: dict = Depends(auth.require_user)) -> dict:
    return _user_out(user)


# ---- Annotations CRUD ---------------------------------------------------

@app.get("/api/findings/{finding_id}/annotations", response_model=list[AnnotationOut])
def list_annotations(finding_id: str, session: Session = Depends(get_db)) -> list[dict]:
    return db.list_annotations(session, finding_id)


@app.post(
    "/api/findings/{finding_id}/annotations",
    response_model=AnnotationOut,
    status_code=201,
)
def create_annotation(
    finding_id: str,
    body: AnnotationIn,
    user: dict = Depends(auth.require_user),
    session: Session = Depends(get_db),
) -> dict:
    return db.create_annotation(
        session, finding_id, body.label, body.note, user["username"]
    )


def _load_annotation_author(session: Session, ann_id: int) -> str | None:
    from .models import Annotation
    ann = session.get(Annotation, ann_id)
    return ann.author if ann is not None else None


@app.patch("/api/annotations/{ann_id}", response_model=AnnotationOut)
def update_annotation(
    ann_id: int,
    body: AnnotationPatch,
    user: dict = Depends(auth.require_user),
    session: Session = Depends(get_db),
) -> dict:
    author = _load_annotation_author(session, ann_id)
    if author is None:
        raise HTTPException(404, f"Annotation {ann_id} not found")
    if author and author != user["username"]:
        raise HTTPException(403, "You can only edit your own annotations")
    updated = db.update_annotation(session, ann_id, body.label, body.note, user["username"])
    if updated is None:
        raise HTTPException(404, f"Annotation {ann_id} not found")
    return updated


@app.delete("/api/annotations/{ann_id}", status_code=204)
def delete_annotation(
    ann_id: int,
    user: dict = Depends(auth.require_user),
    session: Session = Depends(get_db),
) -> None:
    author = _load_annotation_author(session, ann_id)
    if author is None:
        raise HTTPException(404, f"Annotation {ann_id} not found")
    if author and author != user["username"]:
        raise HTTPException(403, "You can only delete your own annotations")
    db.delete_annotation(session, ann_id)


@app.get("/api/annotations/counts")
def annotation_counts(session: Session = Depends(get_db)) -> dict[str, int]:
    return db.count_annotations_by_finding(session)


# ---- Reviews / per-annotator voting + settlement ------------------------

def _review_payload(session: Session, finding_id: str, user: dict | None) -> dict:
    summary = db.review_summary_for_finding(session, finding_id)
    my_vote = None
    if user is not None:
        for v in summary["votes"]:
            if v["user_id"] == user["id"]:
                my_vote = v
                break
    summary["my_vote"] = my_vote
    return summary


@app.get("/api/findings/{finding_id}/review", response_model=ReviewSummaryOut)
def get_review(
    finding_id: str,
    user: dict | None = Depends(auth.get_current_user_optional),
    session: Session = Depends(get_db),
) -> dict:
    return _review_payload(session, finding_id, user)


@app.put("/api/findings/{finding_id}/review", response_model=ReviewSummaryOut)
def put_review(
    finding_id: str,
    body: VoteIn = Body(...),
    user: dict = Depends(auth.require_user),
    session: Session = Depends(get_db),
) -> dict:
    try:
        db.cast_vote(session, finding_id, user["id"], body.status, body.rationale)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return _review_payload(session, finding_id, user)


@app.delete("/api/findings/{finding_id}/review", response_model=ReviewSummaryOut)
def delete_review(
    finding_id: str,
    user: dict = Depends(auth.require_user),
    session: Session = Depends(get_db),
) -> dict:
    db.remove_vote(session, finding_id, user["id"])
    return _review_payload(session, finding_id, user)


@app.get("/api/reviews")
def list_reviews(session: Session = Depends(get_db)) -> list[dict]:
    return db.all_review_summaries(session)


@app.get("/api/stats")
def get_stats(session: Session = Depends(get_db)) -> dict:
    return db.stats(session)


# ---- Static data + built frontend ---------------------------------------

if DATA_DIR.exists():
    app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")

if WEB_DIST.exists():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

    @app.get("/")
    def root() -> FileResponse:
        return FileResponse(WEB_DIST / "index.html")

    @app.get("/{full_path:path}")
    def spa(full_path: str) -> FileResponse:
        if full_path.startswith(("api/", "data/", "assets/")):
            raise HTTPException(404, "Not found")
        candidate = WEB_DIST / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(WEB_DIST / "index.html")
else:
    @app.get("/")
    def root_missing() -> JSONResponse:
        return JSONResponse(
            {
                "message": "ATLAS backend running. Frontend build not found — "
                "run `yarn build` in website/ or start vite dev server and proxy /api here.",
                "docs": "/docs",
            }
        )


def run() -> None:
    """Entry point for the `atlas-backend` console script."""
    import uvicorn

    uvicorn.run(
        "atlas_backend.app:app",
        host=os.environ.get("ATLAS_HOST", "127.0.0.1"),
        port=int(os.environ.get("ATLAS_PORT", "8000")),
        reload=bool(os.environ.get("ATLAS_RELOAD")),
    )


if __name__ == "__main__":
    run()
