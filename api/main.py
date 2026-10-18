import re
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from api import db
from game.logic import Game, MAX_SCORE


BASE_DIR = Path(__file__).resolve().parent.parent
USERNAME_PATTERN = re.compile(r"[A-Za-z0-9_-]{3,20}")
RUN_PATTERN = re.compile(r"[A-Za-z0-9_-]{16,64}")


@asynccontextmanager
async def lifespan(app):
    db.init_db()
    yield


app = FastAPI(title="Brickfall", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.exception_handler(RequestValidationError)
async def invalid_request(request, error):
    return JSONResponse(status_code=400, content={"detail": "Invalid JSON request."})


def credentials(body):
    username = body.get("username")
    password = body.get("password")
    if not isinstance(username, str) or not USERNAME_PATTERN.fullmatch(username):
        raise HTTPException(400, "Username must be 3-20 letters, digits, _ or - (ASCII).")
    if not isinstance(password, str) or not 8 <= len(password) <= 128:
        raise HTTPException(400, "Password must contain 8-128 characters.")
    try:
        password.encode("utf-8")
    except UnicodeEncodeError:
        raise HTTPException(400, "Password contains invalid characters.")
    return username, password


def current_user(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Sign in first.", headers={"WWW-Authenticate": "Bearer"})
    token = authorization[7:]
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        raise HTTPException(401, "Invalid or expired token.")
    user = db.session_user(token)
    if user is None:
        raise HTTPException(401, "Invalid or expired token.")
    return user


@app.post("/register", status_code=201)
def register(body: dict = Body(...)):
    username, password = credentials(body)
    try:
        user = db.register_user(username, password)
    except sqlite3.IntegrityError:
        raise HTTPException(409, "This username is already registered.")
    return {"username": user["username"]}


@app.post("/login")
def login(body: dict = Body(...)):
    username, password = credentials(body)
    user = db.login_user(username, password)
    if user is None:
        raise HTTPException(401, "Incorrect username or password.")
    return {"token": db.create_session(user["id"]), "username": user["username"]}


@app.post("/scores", status_code=201)
def submit_score(body: dict = Body(...), user: dict = Depends(current_user)):
    score = body.get("score")
    run_id = body.get("run_id")
    if type(score) is not int or not 0 <= score <= MAX_SCORE or score % 10 != 0:
        raise HTTPException(400, f"Score must be a multiple of 10 between 0 and {MAX_SCORE}.")
    if not isinstance(run_id, str) or not RUN_PATTERN.fullmatch(run_id):
        raise HTTPException(400, "Invalid game identifier.")
    try:
        db.add_score(user["id"], run_id, score)
    except ValueError as error:
        raise HTTPException(409, str(error))
    return {"score": score, "run_id": run_id}


@app.get("/scores/top")
def scores_top():
    return db.top_scores()


@app.get("/players/{name}/stats")
def stats(name: str):
    player = db.player_stats(name)
    if player is None:
        raise HTTPException(404, "Player not found.")
    return player


@app.put("/saves")
def save(body: dict = Body(...), user: dict = Depends(current_user)):
    try:
        state = Game.from_dict(body).to_dict()
    except (ValueError, TypeError, KeyError, OverflowError):
        raise HTTPException(400, "Invalid game save.")
    if state["state"] not in ("playing", "paused"):
        raise HTTPException(400, "Only an unfinished game can be saved.")
    try:
        db.save_game(user["id"], state)
    except ValueError as error:
        raise HTTPException(409, str(error))
    return state


@app.get("/saves")
def load(user: dict = Depends(current_user)):
    state = db.load_game(user["id"])
    if state is None:
        raise HTTPException(404, "No saved game yet.")
    try:
        return Game.from_dict(state).to_dict()
    except (ValueError, TypeError, KeyError, OverflowError):
        raise HTTPException(409, "The saved game is invalid. Start a new game.")


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request=request, name="index.html", context={"players": db.top_scores()}
    )


@app.get("/players/{name}", response_class=HTMLResponse)
def player_profile(request: Request, name: str):
    player = db.player_stats(name)
    if player is None:
        raise HTTPException(404, "Player not found.")
    return templates.TemplateResponse(
        request=request, name="player.html", context={"player": player}
    )


@app.get("/rules", response_class=HTMLResponse)
def rules(request: Request):
    return templates.TemplateResponse(request=request, name="rules.html")
