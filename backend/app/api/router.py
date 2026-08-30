"""Aggregates every v1 router. Mounted once in main.py."""

from fastapi import APIRouter

from app.api.v1 import (
    admin,
    approvals,
    auth,
    chat,
    company,
    employees,
    me,
    onboarding,
    tasks,
    transcripts,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(tasks.router)
api_router.include_router(employees.router)
api_router.include_router(approvals.router)
api_router.include_router(company.router)
api_router.include_router(onboarding.router)
api_router.include_router(me.router)
api_router.include_router(chat.router)
api_router.include_router(transcripts.router)
api_router.include_router(admin.router)
