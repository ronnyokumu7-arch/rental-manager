from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.invoices import Invoice, InvoiceStatus
from app.models.users import User, UserRole
from app.schemas.invoice import InvoiceCreate, InvoiceOut, InvoiceUpdate


router = APIRouter(prefix="/invoices", tags=["invoices"])


def _require_super_admin(current_user: User) -> None:
    if current_user.role != UserRole.super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can perform this action",
        )


def _get_invoice_or_404(invoice_id: int, db: Session) -> Invoice:
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )
    return invoice


def _generate_invoice_number(tenant_id: int, db: Session) -> str:
    year = datetime.now(timezone.utc).year
    count = db.query(Invoice).filter(
        Invoice.tenant_id == tenant_id,
    ).count()
    sequence = str(count + 1).zfill(4)
    return f"{tenant_id}-{year}-{sequence}"


@router.post("/", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
def create_invoice(
    payload: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_super_admin(current_user)
    invoice_number = _generate_invoice_number(payload.tenant_id, db)
    db_invoice = Invoice(
        **payload.model_dump(),
        invoice_number=invoice_number,
        status=InvoiceStatus.draft,
        amount_paid=Decimal("0"),
    )
    db.add(db_invoice)
    db.commit()
    db.refresh(db_invoice)
    return db_invoice


@router.get("/", response_model=list[InvoiceOut])
def list_invoices(
    invoice_status: InvoiceStatus | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Invoice)
    if current_user.role != UserRole.super_admin:
        query = query.filter(Invoice.tenant_id == current_user.tenant_id)
    if invoice_status is not None:
        query = query.filter(Invoice.status == invoice_status)
    return query.order_by(Invoice.created_at.desc()).all()


@router.get("/{invoice_id}", response_model=InvoiceOut)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice = _get_invoice_or_404(invoice_id, db)
    if current_user.role != UserRole.super_admin:
        if invoice.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own invoices",
            )
    return invoice


@router.patch("/{invoice_id}", response_model=InvoiceOut)
def update_invoice(
    invoice_id: int,
    payload: InvoiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_super_admin(current_user)
    invoice = _get_invoice_or_404(invoice_id, db)
    if invoice.status in (InvoiceStatus.paid, InvoiceStatus.void):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot edit a {invoice.status.value} invoice",
        )
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(invoice, field, value)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.post("/{invoice_id}/send", response_model=InvoiceOut)
def send_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_super_admin(current_user)
    invoice = _get_invoice_or_404(invoice_id, db)
    if invoice.status != InvoiceStatus.draft:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only draft invoices can be sent. Current status: '{invoice.status.value}'",
        )
    invoice.status = InvoiceStatus.sent
    db.commit()
    db.refresh(invoice)
    return invoice


@router.post("/{invoice_id}/void", response_model=InvoiceOut)
def void_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_super_admin(current_user)
    invoice = _get_invoice_or_404(invoice_id, db)
    if invoice.status == InvoiceStatus.paid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Paid invoices cannot be voided",
        )
    if invoice.status == InvoiceStatus.void:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice is already void",
        )
    invoice.status = InvoiceStatus.void
    db.commit()
    db.refresh(invoice)
    return invoice


@router.get("/{invoice_id}/pdf")
def get_invoice_pdf(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice = _get_invoice_or_404(invoice_id, db)
    if current_user.role != UserRole.super_admin:
        if invoice.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only download your own invoices",
            )

    from app.services.pdf import generate_invoice_pdf
    pdf_bytes = generate_invoice_pdf(invoice, db)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=invoice-{invoice.invoice_number}.pdf"
        },
    )