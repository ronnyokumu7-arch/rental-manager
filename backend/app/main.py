from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import admin
from app.routers import reports

from app.core.config import get_settings
from app.jobs.scheduler import start_scheduler, stop_scheduler
from app.routers import (
    auth, bookings, clients, contracts,
    invoices, payments, subscriptions,
    tenant_policies, tenant_profile,
    tenants, users, vehicles,
)


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    debug=settings.debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    start_scheduler()


@app.on_event("shutdown")
def shutdown_event():
    stop_scheduler()


@app.get("/health", tags=["system"])
def health_check():
    return {
        "status": "ok",
        "environment": settings.environment,
    }


app.include_router(auth.router, prefix="/api/v1")
app.include_router(tenants.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(clients.router, prefix="/api/v1")
app.include_router(vehicles.router, prefix="/api/v1")
app.include_router(bookings.router, prefix="/api/v1")
app.include_router(subscriptions.router, prefix="/api/v1")
app.include_router(invoices.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1")
app.include_router(tenant_profile.router, prefix="/api/v1")
app.include_router(tenant_policies.router, prefix="/api/v1")
app.include_router(contracts.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")