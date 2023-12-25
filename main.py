from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from llm_helper import process_query_with_tools, save_api_key
import uvicorn
from typing import Optional, List

app = FastAPI()
templates = Jinja2Templates(directory="templates")
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

@app.post("/", response_class=HTMLResponse)
async def process_query(
    request: Request, 
    query: str = Form(...),
    api_key: Optional[str] = Form(None)
):
    if api_key and chat_history.pending_api_keys:
        # Save the provided API key
        service = chat_history.pending_api_keys[0]
        save_api_key(service, api_key)
        chat_history.clear_pending_api_keys()
        # Reprocess the last query
        if chat_history.messages:
            last_query = chat_history.messages[-1]["query"]
            result = process_query_with_tools(last_query)
        else:
            result = {"error": "No previous query found"}
    else:
        result = process_query_with_tools(query)
        
    # Check if we need API keys
    if result.get("needs_api_key"):
        chat_history.set_pending_api_keys([result["needs_api_key"]["service"]])
    
    # Add to chat history
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
