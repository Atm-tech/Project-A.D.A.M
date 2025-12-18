from fastapi import APIRouter

from app.api.v1 import outlet_routes, pkb_routes, purchase_routes, health

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(pkb_routes.router, prefix="/pkb", tags=["PKB"])
api_router.include_router(outlet_routes.router, prefix="/outlets", tags=["Outlets"])
api_router.include_router(purchase_routes.router, prefix="/purchase", tags=["Purchase"])
