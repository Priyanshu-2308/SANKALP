"""Unit tests for SQLite database layer and single-use approval tokens."""

import tempfile
from pathlib import Path
from apps.api.app.database import Database


def test_sqlite_token_lifecycle() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_sankalp.sqlite3"
        db = Database(db_path=db_path)

        # 1. Issue token
        itinerary_id = "itin_12345"
        token = db.create_approval_token(itinerary_id=itinerary_id, ttl_minutes=15)
        assert token.startswith("tok_")

        # 2. First redemption should succeed
        success_first = db.verify_and_redeem_token(token, itinerary_id)
        assert success_first is True

        # 3. CRITICAL: Second redemption with same token MUST strictly fail (Double spend protection)
        success_second = db.verify_and_redeem_token(token, itinerary_id)
        assert success_second is False

        # 4. Redemption with wrong itinerary ID must fail
        token2 = db.create_approval_token(itinerary_id="itin_real", ttl_minutes=15)
        success_wrong_id = db.verify_and_redeem_token(token2, "itin_fake")
        assert success_wrong_id is False


def test_sqlite_expired_token() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_sankalp_expired.sqlite3"
        db = Database(db_path=db_path)

        # Token created with negative TTL (already expired)
        token = db.create_approval_token(itinerary_id="itin_expired", ttl_minutes=-1)
        redeemed = db.verify_and_redeem_token(token, "itin_expired")
        assert redeemed is False


def test_trip_audit_logging() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_sankalp_audit.sqlite3"
        db = Database(db_path=db_path)

        token = db.create_approval_token("itin_audit_1", ttl_minutes=15)
        redeemed = db.verify_and_redeem_token(token, "itin_audit_1")
        assert redeemed is True

        trip_id = db.record_trip_approval(
            approval_token=token,
            itinerary_id="itin_audit_1",
            origin_id="STN_PUNE",
            destination_id="STN_CSMT",
            total_fare_paise=125000,
            p_ontime=0.965,
            itinerary_data={"test": "payload"},
        )
        assert trip_id.startswith("trip_")

        trip = db.get_trip(trip_id)
        assert trip is not None
        assert trip["origin_id"] == "STN_PUNE"
        assert trip["destination_id"] == "STN_CSMT"
        assert trip["total_fare_paise"] == 125000
        assert trip["p_ontime"] == 0.965
        assert trip["itinerary"] == {"test": "payload"}

        logs = db.list_audit_logs(limit=10)
        assert len(logs) == 1
        assert logs[0]["trip_id"] == trip_id
