from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.clients import Client, ClientStatus
from app.models.users import User
from app.schemas.client import ClientCreate, ClientOut, ClientUpdate


router = APIRouter(prefix="/clients", tags=["clients"])


@router.post("/", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
def create_client(
    client: ClientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_client = Client(**client.model_dump(), tenant_id=current_user.tenant_id)
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client


@router.get("/", response_model=list[ClientOut])
def read_clients(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Client).filter(Client.tenant_id == current_user.tenant_id).all()


@router.get("/{client_id}", response_model=ClientOut)
def read_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.tenant_id == current_user.tenant_id,
    ).first()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client


@router.patch("/{client_id}", response_model=ClientOut)
def update_client(
    client_id: int,
    updates: ClientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.tenant_id == current_user.tenant_id,
    ).first()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(client, field, value)
    db.commit()
    db.refresh(client)
    return client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.tenant_id == current_user.tenant_id,
    ).first()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    db.delete(client)
    db.commit()