import logging
from datetime import datetime, timezone, timedelta

from app.db.database import SessionLocal
from app.models.bookings import Booking, BookingStatus

logger = logging.getLogger(__name__)

ARCHIVE_AFTER_DAYS = 30


def run_booking_auto_archive():
    logger.info("Running booking auto-archive job...")
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=ARCHIVE_AFTER_DAYS)

        archivable_statuses = [
            BookingStatus.completed,
            BookingStatus.cancelled,
            BookingStatus.no_show,
        ]

        bookings = db.query(Booking).filter(
            Booking.status.in_(archivable_statuses),
            Booking.is_archived == False,
            Booking.updated_at <= cutoff,
        ).all()

        count = 0
        for booking in bookings:
            booking.is_archived = True
            booking.archived_at = now
            count += 1

        db.commit()
        logger.info(f"Auto-archived {count} bookings.")
    except Exception as e:
        db.rollback()
        logger.error(f"Booking auto-archive job failed: {e}")
    finally:
        db.close()