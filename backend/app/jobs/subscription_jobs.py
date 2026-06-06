import logging
from datetime import datetime, timezone

from app.db.database import SessionLocal
from app.models.subscriptions import Subscription, SubscriptionStatus, PlanType, BillingCycle
from app.models.tenants import Tenant

logger = logging.getLogger(__name__)


def run_subscription_lifecycle():
    logger.info("Running subscription lifecycle job...")
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        _handle_trial_conversions(db, now)
        _handle_expired_subscriptions(db, now)
        _handle_grace_period_expirations(db, now)
        db.commit()
        logger.info("Subscription lifecycle job completed.")
    except Exception as e:
        db.rollback()
        logger.error(f"Subscription lifecycle job failed: {e}")
    finally:
        db.close()


def _handle_trial_conversions(db, now):
    """Convert free_trial → starter_trial when trial ends."""
    from datetime import timedelta

    expired_trials = db.query(Subscription).filter(
        Subscription.plan == PlanType.free_trial,
        Subscription.status == SubscriptionStatus.trial,
        Subscription.ends_at <= now,
    ).all()

    for sub in expired_trials:
        logger.info(f"Converting tenant {sub.tenant_id} from free_trial to starter_trial")
        new_ends_at = now + timedelta(days=14)
        new_grace = new_ends_at + timedelta(days=7)

        sub.plan = PlanType.starter_trial
        sub.status = SubscriptionStatus.starter_trial
        sub.starts_at = now
        sub.ends_at = new_ends_at
        sub.grace_period_ends_at = new_grace

        tenant = db.query(Tenant).filter(Tenant.id == sub.tenant_id).first()
        if tenant:
            tenant.plan = PlanType.starter_trial.value
            tenant.subscription_status = SubscriptionStatus.starter_trial
            tenant.trial_ends_at = new_ends_at
            tenant.subscription_ends_at = new_ends_at
            tenant.grace_period_ends_at = new_grace


def _handle_expired_subscriptions(db, now):
    """Move active/starter_trial subscriptions to past_due when they expire."""
    expired = db.query(Subscription).filter(
        Subscription.status.in_([
            SubscriptionStatus.active,
            SubscriptionStatus.starter_trial,
        ]),
        Subscription.ends_at <= now,
    ).all()

    for sub in expired:
        logger.info(f"Moving tenant {sub.tenant_id} subscription to past_due")
        sub.status = SubscriptionStatus.past_due

        tenant = db.query(Tenant).filter(Tenant.id == sub.tenant_id).first()
        if tenant:
            tenant.subscription_status = SubscriptionStatus.past_due


def _handle_grace_period_expirations(db, now):
    """Suspend tenants whose grace period has ended."""
    grace_expired = db.query(Subscription).filter(
        Subscription.status == SubscriptionStatus.past_due,
        Subscription.grace_period_ends_at <= now,
    ).all()

    for sub in grace_expired:
        logger.info(f"Suspending tenant {sub.tenant_id} — grace period expired")
        sub.status = SubscriptionStatus.suspended

        tenant = db.query(Tenant).filter(Tenant.id == sub.tenant_id).first()
        if tenant:
            tenant.subscription_status = SubscriptionStatus.suspended