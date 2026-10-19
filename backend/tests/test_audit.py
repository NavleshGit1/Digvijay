from app.services.audit import compute_audit_hash


def test_audit_hash_chain_determinism():
    prev_hash = "0" * 64
    hash1 = compute_audit_hash(
        previous_hash=prev_hash,
        actor_id="11111111-1111-1111-1111-111111111111",
        action="SEED_DATA",
        entity_type="system",
        entity_id="seed-42",
        timestamp_str="2026-10-19T12:00:00Z",
        reason="Initial seed for testing",
        before_state=None,
        after_state={"seed": 42},
    )

    # Identical payload produces identical hash
    hash2 = compute_audit_hash(
        previous_hash=prev_hash,
        actor_id="11111111-1111-1111-1111-111111111111",
        action="SEED_DATA",
        entity_type="system",
        entity_id="seed-42",
        timestamp_str="2026-10-19T12:00:00Z",
        reason="Initial seed for testing",
        before_state=None,
        after_state={"seed": 42},
    )
    assert hash1 == hash2

    # Chaining to next entry
    hash_next = compute_audit_hash(
        previous_hash=hash1,
        actor_id="22222222-2222-2222-2222-222222222222",
        action="APPROVE_PLAN",
        entity_type="plans",
        entity_id="plan-v1",
        timestamp_str="2026-10-19T12:05:00Z",
        reason="Reviewed and approved baseline",
        before_state={"status": "proposed"},
        after_state={"status": "approved"},
    )
    assert hash_next != hash1
    assert len(hash_next) == 64
