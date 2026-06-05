from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.bookings import Booking, BookingStatus
from app.models.clients import Client, ClientStatus
from app.models.users import User
from app.models.vehicles import Vehicle, VehicleStatus
from app.schemas.booking import BookingCreate, BookingOut, BookingUpdate


router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("/", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def create_booking(
    booking: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    client = db.query(Client).filter(
        Client.id == booking.client_id,
        Client.tenant_id == current_user.tenant_id,
    ).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found. Add client first.",
        )

    vehicle = db.query(Vehicle).filter(
        Vehicle.id == booking.vehicle_id,
        Vehicle.tenant_id == current_user.tenant_id,
    ).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found.",
        )
    if vehicle.status != VehicleStatus.available:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Vehicle is '{vehicle.status.value}'. Only available vehicles can be booked.",
        )

    db_booking = Booking(
        **booking.model_dump(),
        tenant_id=current_user.tenant_id,
    )
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking


@router.get("/", response_model=list[BookingOut])
def list_bookings(
    status: BookingStatus | None = None,
    client_id: int | None = None,
    vehicle_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Booking).filter(Booking.tenant_id == current_user.tenant_id)
    if status is not None:
        query = query.filter(Booking.status == status)
    if client_id is not None:
        query = query.filter(Booking.client_id == client_id)
    if vehicle_id is not None:
        query = query.filter(Booking.vehicle_id == vehicle_id)
    return query.order_by(Booking.created_at.desc()).all()


@router.get("/{booking_id}", response_model=BookingOut)
def get_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.tenant_id == current_user.tenant_id,
    ).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found.",
        )
    return booking


@router.patch("/{booking_id}", response_model=BookingOut)
def update_booking(
    booking_id: int,
    updates: BookingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.tenant_id == current_user.tenant_id,
    ).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found.",
        )
    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(booking, field, value)
    db.commit()
    db.refresh(booking)
    return booking


@router.delete("/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.tenant_id == current_user.tenant_id,
    ).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found.",
        )
    db.delete(booking)
    db.commit()