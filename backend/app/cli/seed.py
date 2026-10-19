"""
Seed CLI Tool for AirOps Nexus.
Usage:
    python -m app.cli.seed [--seed 42] [--as-of 2026-10-20T12:00:00Z] [--reset]
"""

import argparse
import sys
from datetime import datetime
from app.db.session import SessionLocal
from app.engines.data_fusion.generator import seed_database


def main():
    parser = argparse.ArgumentParser(description="Seed AirOps Nexus with synthetic operational dataset")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic 64-bit seed sequence integer")
    parser.add_argument("--as-of", type=str, default=None, help="Reference ISO timestamp (defaults to virtual clock as_of)")
    parser.add_argument("--reset", action="store_true", default=True, help="Clear existing domain tables before seeding")
    args = parser.parse_args()

    as_of_dt = datetime.fromisoformat(args.as_of) if args.as_of else None

    print(f"=== AirOps Nexus Synthetic Data Seeder ===")
    print(f"Seed: {args.seed} | As-Of: {as_of_dt or 'Clock Default'} | Reset: {args.reset}")

    db = SessionLocal()
    try:
        dataset_hash, counts = seed_database(db=db, seed=args.seed, as_of=as_of_dt, reset=args.reset)
        print("\nSeed completed successfully!")
        print(f"Dataset SHA-256 Hash: {dataset_hash}")
        print("\nEntity Counts:")
        for entity, count in sorted(counts.items()):
            print(f"  - {entity:30s}: {count:4d} rows")
        print(f"\nTotal records seeded: {sum(counts.values())}")
    except Exception as e:
        print(f"ERROR: Seeding failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
