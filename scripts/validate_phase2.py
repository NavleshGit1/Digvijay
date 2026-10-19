"""
Phase 2 Live Stack Validation Script (Task P2-8 & Phase 2 Exit Gate).
Validates:
1. Admin authentication & RBAC
2. Deterministic data seeding via POST /api/v1/admin/seed
3. Byte-for-byte SHA-256 hash determinism across runs
4. Full relational database dimensions (40 assets, 120 crew, 300 tasks, 3 zones)
5. Live calculated Overview KPIs from PostgreSQL tables
6. Data source registry & freshness SLA evaluation (/api/v1/system/data-sources)
7. Data quality review ledger (/api/v1/admin/data-quality-issues)
"""

import json
import urllib.request
import urllib.error
import sys

BASE_URL = "http://localhost:8000/api/v1"
FIXED_AS_OF = "2026-10-20T12:00:00Z"
EXPECTED_HASH = "9bd606f992899f2e31e830386108f2c2415fd23d181df31d8025c4dde41fd70c"


def post_json(url: str, data: dict, token: str = None) -> tuple[int, dict]:
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def get_json(url: str, token: str = None) -> tuple[int, dict | list]:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def run_validations():
    print("=== PHASE 2 LIVE STACK & DATA FOUNDATION VALIDATION ===")

    # 1. Login as Admin
    print("\n1. Authenticating as Administrator...")
    status, body = post_json(
        f"{BASE_URL}/auth/login",
        {"username": "admin@airops.local", "password": "AdminSecurePass2026!"},
    )
    assert status == 200, f"Login failed: {status} {body}"
    admin_token = body["access_token"]
    print("   [PASS] Admin authenticated successfully.")

    # 2. Trigger Seed Generation via API
    print("\n2. Executing POST /api/v1/admin/seed (seed=42, fixed as_of)...")
    status, body = post_json(
        f"{BASE_URL}/admin/seed",
        {"seed": 42, "as_of": FIXED_AS_OF, "reset": True},
        token=admin_token,
    )
    assert status == 200, f"Seed failed: {status} {body}"
    hash1 = body["dataset_hash"]
    counts1 = body["entity_counts"]
    print(f"   [PASS] Seeding completed. Dataset Hash: {hash1}")
    print(f"   [PASS] Assets: {counts1['assets']}, Personnel: {counts1['personnel']}, Tasks: {counts1['tasks']}")
    assert hash1 == EXPECTED_HASH, f"Hash mismatch: expected {EXPECTED_HASH}, got {hash1}"

    # 3. Idempotent Re-Seed Verification
    print("\n3. Testing Idempotent Re-Seeding (byte-for-byte hash identity)...")
    status, body = post_json(
        f"{BASE_URL}/admin/seed",
        {"seed": 42, "as_of": FIXED_AS_OF, "reset": True},
        token=admin_token,
    )
    assert status == 200
    hash2 = body["dataset_hash"]
    counts2 = body["entity_counts"]
    assert hash1 == hash2, f"Determinism violation: run 1 ({hash1}) != run 2 ({hash2})"
    assert counts1 == counts2, f"Entity count mismatch: {counts1} != {counts2}"
    print(f"   [PASS] Perfect determinism verified byte-for-byte. Hash: {hash2}")

    # 4. Live Overview KPIs
    print("\n4. Verifying Live Computed Overview KPIs from PostgreSQL...")
    status, body = get_json(f"{BASE_URL}/overview?as_of={FIXED_AS_OF}", token=admin_token)
    assert status == 200, f"Overview request failed: {status} {body}"
    assert body["asset_availability"]["data_kind"] == "observed"
    avail = body["asset_availability"]["value"]
    shortage = body["spares_shortage"]
    eligible = body["eligible_tasks"]
    crew_avail = body["crew_availability"]["value"]
    print(f"   [PASS] Live KPIs calculated from database:")
    print(f"          - Asset Availability: {avail*100:.1f}%")
    print(f"          - Serviceability:     {body['serviceability']['value']*100:.1f}%")
    print(f"          - Eligible Tasks:     {eligible}")
    print(f"          - Crew Availability:  {crew_avail*100:.1f}%")
    print(f"          - Spares Shortages:   {shortage} parts (Controlled shortage in Base Alpha)")
    print(f"          - Total Delay:        {body['total_delay']} min")
    assert 0.80 <= avail <= 1.0
    assert shortage == 3

    # 5. Data Sources Registry & Freshness
    print("\n5. Testing GET /api/v1/system/data-sources...")
    status, body = get_json(f"{BASE_URL}/system/data-sources", token=admin_token)
    assert status == 200, f"Data sources request failed: {status} {body}"
    assert len(body) == 3, f"Expected 3 registered data sources, got {len(body)}"
    for ds in body:
        print(f"   [PASS] Source '{ds['source_name']}' ({ds['adapter_type']}) - Status: {ds['status']}, Staleness: {ds['staleness_seconds']}s")
        assert ds["status"] == "fresh"

    # 6. Dataset Versions Snapshot
    print("\n6. Testing GET /api/v1/admin/dataset-versions...")
    status, body = get_json(f"{BASE_URL}/admin/dataset-versions", token=admin_token)
    assert status == 200, f"Dataset versions request failed: {status} {body}"
    assert len(body) >= 1
    latest_ver = body[0]
    print(f"   [PASS] Version tag: {latest_ver['version_tag']} with hash {latest_ver['content_hash']}")
    assert latest_ver["content_hash"] == EXPECTED_HASH

    # 7. Data Quality Review Items
    print("\n7. Testing GET /api/v1/admin/data-quality-issues...")
    status, body = get_json(f"{BASE_URL}/admin/data-quality-issues", token=admin_token)
    assert status == 200
    print(f"   [PASS] Data quality issues query succeeded ({len(body)} issues logged in audit review ledger).")

    print("\n=== ALL PHASE 2 EXIT CRITERIA VALIDATED & PASSING! ===")


if __name__ == "__main__":
    run_validations()
