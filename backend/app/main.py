from fastapi import FastAPI
from app.routers import robot
from app.routers import user
from app.routers import admin

app = FastAPI()

app.include_router(robot.router)
app.include_router(user.router)
app.include_router(admin.router)