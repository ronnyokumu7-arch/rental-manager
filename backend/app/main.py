from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import auth, bookings, clients, tenants, users, vehicles

from app.routers import auth, bookings, clients, invoices, payments, subscriptions, tenants, users, vehicles


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