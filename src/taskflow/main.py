from fastapi import FastAPI

from taskflow.routes import health, tasks

app = FastAPI(title="TaskFlow")

app.include_router(health.router)
app.include_router(tasks.router)