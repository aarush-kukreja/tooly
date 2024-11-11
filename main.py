from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from llm_helper import process_query_with_tools, save_api_key
import uvicorn
from typing import Optional, List
import os

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Only mount static files if the directory exists
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

class ChatHistory:
    def __init__(self):
        self.messages: List[dict] = []
        self.pending_api_keys: List[str] = []

    def add_message(self, content: dict):
        self.messages.append(content)

    def set_pending_api_keys(self, keys: List[str]):
        self.pending_api_keys = keys

    def clear_pending_api_keys(self):
        self.pending_api_keys = []

chat_history = ChatHistory()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request, 
            "chat_history": chat_history.messages,
            "pending_api_keys": chat_history.pending_api_keys
        }
    )

@app.post("/process")
async def process_query(
    request: Request,
    query: str = Form(...),
    llm_provider: str = Form(default="groq")
):
    try:
        result = await process_query_with_tools(query, llm_provider)
        chat_history.add_message({
            "query": query,
            "result": result
        })
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "chat_history": chat_history.messages,
                "pending_api_keys": chat_history.pending_api_keys
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "chat_history": chat_history.messages,
                "pending_api_keys": chat_history.pending_api_keys,
                "error": str(e)
            }
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
