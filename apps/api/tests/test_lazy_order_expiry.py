"""TDD: lazy expiry — a PENDING order past the SePay window becomes EXPIRED on read."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.funnel_order import FunnelOrder
from app.services.funnel_order_service import FunnelOrderService
from app.services.sepay_qr import ORDER_EXPIRY_MINUTES

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_lazy_order_expiry.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
TABLES = [FunnelOrder.__table__]


@pytest.fixture()
def db():
    for t in reversed(TABLES):
        t.drop(bind=engine, checkfirst=True)
    for t in TABLES:
        t.create(bind=engine, checkfirst=True)
    s = TestingSessionLocal()
    try:
        yield s
    finally:
        s.close()


def _mk(db, code, minutes_old):
    o = FunnelOrder(
        funnel_id="f1", order_code=code, status="PENDING",
        funnel_title="t", funnel_slug="s", product_name="p",
        buyer_email="a@b.com", subtotal_amount=1000, final_amount=1000,
    )
    db.add(o)
    db.commit()
    o.created_at = datetime.now(timezone.utc) - timedelta(minutes=minutes_old)
    db.commit()
    return o


def test_pending_past_window_expires_on_read(db):
    o = _mk(db, "SEP0000000001", ORDER_EXPIRY_MINUTES + 5)
    resp = FunnelOrderService.order_status(db, o)
    assert resp.status == "EXPIRED"
    assert db.query(FunnelOrder).filter_by(id=o.id).one().status == "EXPIRED"


def test_fresh_pending_stays_pending(db):
    o = _mk(db, "SEP0000000002", 1)
    resp = FunnelOrderService.order_status(db, o)
    assert resp.status == "PENDING"
