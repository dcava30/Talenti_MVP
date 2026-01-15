from fastapi import FastAPI

from app.api import auth, invitations, orgs, roles, storage
from app.db import Base, engine


app = FastAPI(title="Talenti API")


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(orgs.router)
app.include_router(roles.router)
app.include_router(invitations.router)
app.include_router(storage.router)
