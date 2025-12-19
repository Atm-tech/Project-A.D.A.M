from fastapi import APIRouter

from app.api.v1 import outlet_routes, pkb_routes, purchase_routes, health, closing_routes, sales_routes, perpetual_routes

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(pkb_routes.router, prefix="/pkb", tags=["PKB"])
api_router.include_router(outlet_routes.router, prefix="/outlets", tags=["Outlets"])
api_router.include_router(purchase_routes.router, prefix="/purchase", tags=["Purchase"])
api_router.include_router(closing_routes.router, prefix="/closing", tags=["Closing Stock"])
api_router.include_router(sales_routes.router, prefix="/sales", tags=["Sales"])
api_router.include_router(perpetual_routes.router, prefix="/perpetual", tags=["Perpetual Closing"])
