
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# находим главную папку проекта
BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI()  # создаем сервер

# подключаем папку с CSS
app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static"
)

# подключаем HTML шаблоны
templates = Jinja2Templates(
    directory=BASE_DIR / "templates"
)

# пока используем пример результатов
players = [
    {"name": "Max", "score": 150},
    {"name": "Artem", "score": 100},
    {"name": "Dimond", "score": 50}
]


# главная страница с таблицей лидеров
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"players": players}
    )


# страница с правилами игры
@app.get("/rules", response_class=HTMLResponse)
def rules(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="rules.html"
    )
