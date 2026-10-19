from datetime import datetime, timezone
import pytest
from app.engines.data_fusion.generator import DeterministicGenerator


def test_generator_determinism():
    fixed_time = datetime(2026, 10, 20, 12, 0, 0, tzinfo=timezone.utc)
    gen1 = DeterministicGenerator(seed=42, as_of=fixed_time)
    data1 = gen1.generate_all()
    hash1 = gen1.compute_dataset_hash(data1)

    gen2 = DeterministicGenerator(seed=42, as_of=fixed_time)
    data2 = gen2.generate_all()
    hash2 = gen2.compute_dataset_hash(data2)

    assert hash1 == hash2, "Identical seed and as_of must produce identical hashes"
    assert hash1 == "9bd606f992899f2e31e830386108f2c2415fd23d181df31d8025c4dde41fd70c"


def test_generator_entity_dimensions():
    fixed_time = datetime(2026, 10, 20, 12, 0, 0, tzinfo=timezone.utc)
    gen = DeterministicGenerator(seed=42, as_of=fixed_time)
    data = gen.generate_all()

    # Core prototype dimensions
    assert len(data["zones"]) == 3
    assert len(data["assets"]) == 40
    assert len(data["personnel"]) == 120
    assert len(data["parts_catalog"]) == 25
    assert len(data["spares_inventory"]) == 75  # 25 parts * 3 zones
    assert len(data["tasks"]) == 300
    assert len(data["qualifications"]) == 8


def test_dag_acyclicity():
    fixed_time = datetime(2026, 10, 20, 12, 0, 0, tzinfo=timezone.utc)
    gen = DeterministicGenerator(seed=42, as_of=fixed_time)
    data = gen.generate_all()

    # Verify that predecessor task ID is strictly created before successor task ID
    task_order = {t["id"]: i for i, t in enumerate(data["tasks"])}
    for dep in data["task_dependencies"]:
        pred_idx = task_order[dep["predecessor_id"]]
        succ_idx = task_order[dep["successor_id"]]
        assert pred_idx < succ_idx, f"Cycle or backward edge detected: {pred_idx} >= {succ_idx}"
