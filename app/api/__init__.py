from fastapi import APIRouter
from app.api.endpoints import wecom, transactions, auth

api_router = APIRouter()

api_router.include_router(wecom.router)
api_router.include_router(transactions.router)
api_router.include_router(auth.router)