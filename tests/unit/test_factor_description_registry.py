"""Display isolation never relaxes research admission or dependency checks."""
import importlib.util
import json
from pathlib import Path

import pytest

from lei_signal.research import definitions

TASK_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = Path(definitions.__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location(
    "description_view", TASK_ROOT / "src/lei_signal/research/description_registry.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
load_view = module.load_description_registry


@pytest.fixture
def valid_registry():
    view, _ = load_view(SOURCE_ROOT / "docs/research/definitions.v1.json")
    return view


def load_json(tmp_path, data):
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(data))
    return load_view(path)


def test_current_sources_are_preserved_and_strict_research_still_rejects():
    path = SOURCE_ROOT / "docs/research/definitions.v1.json"
    original = path.read_bytes()
    view, errors = load_view(path)
    assert len(errors) == 3
    assert "research.price_volume.range_mean20@1.0.0" in definitions.validate_registry(view)
    with pytest.raises(ValueError):
        definitions.validate_registry(json.loads(original))
    assert path.read_bytes() == original


def test_invalid_dependency_cannot_become_available(tmp_path, valid_registry):
    for obj in valid_registry["objects"]:
        if obj["id"] == "mixed.momentum.raw":
            obj["definition"]["formula"] = ""
    view, errors = load_json(tmp_path, valid_registry)
    assert "mixed.momentum.raw@1.0.0" in errors
    assert "mixed.momentum.rank@1.0.0" in errors
    assert "research.price_volume.range_mean20@1.0.0" in definitions.validate_registry(view)


def test_cycles_remain_unavailable(tmp_path, valid_registry):
    for obj in valid_registry["objects"]:
        if obj["id"] == "mixed.momentum.raw":
            obj["dependencies"] = ["mixed.momentum.rank@1.0.0"]
    _, errors = load_json(tmp_path, valid_registry)
    assert "cyclic" in errors["mixed.momentum.raw@1.0.0"]
    assert "cyclic" in errors["mixed.momentum.rank@1.0.0"]


def test_duplicate_identity_stops_whole_view(tmp_path, valid_registry):
    valid_registry["objects"].append(valid_registry["objects"][0])
    with pytest.raises(ValueError, match="duplicate identity"):
        load_json(tmp_path, valid_registry)


def test_invalid_envelope_stops_whole_view(tmp_path, valid_registry):
    valid_registry["schema_version"] = "invalid"
    with pytest.raises(ValueError, match="unsupported registry"):
        load_json(tmp_path, valid_registry)
