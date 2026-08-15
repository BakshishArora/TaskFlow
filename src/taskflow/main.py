from fastapi import FastAPI

from taskflow.routes import health, projects, tasks

app = FastAPI(title="TaskFlow")

app.include_router(health.router)
app.include_router(tasks.router)
app.include_router(projects.router)
