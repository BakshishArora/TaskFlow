from contextlib import asynccontextmanager

from fastapi import FastAPI

from taskflow.db import Base, engine
from taskflow.routes import auth, health, projects


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="TaskFlow", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(health.router)
app.include_router(projects.router)
