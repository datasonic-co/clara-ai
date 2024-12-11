from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from chainlit.utils import mount_chainlit
import os

os.environ["no_proxy"] = "*"

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/app")
def read_main():
    """
    Hello world
    """
    return {"message": "Hello World from main app"}

mount_chainlit(app=app, target="app_chainlit.py", path="/chainlit")
