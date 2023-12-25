from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from llm_helper import get_llm_response
import uvicorn

app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "result": None})

@app.post("/", response_class=HTMLResponse)
async def process_query(request: Request, query: str = Form(...)):
    response = get_llm_response(query)
    return templates.TemplateResponse("index.html", {"request": request, "result": response})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
