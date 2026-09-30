"""jobledger 台账核心单测：字段校验 / 只追加 / 红线目录拒绝。"""
from __future__ import annotations

from pathlib import Path

import pytest

from lei_signal.jobledger.ledger import (
    STATUS_FAILED,
    STATUS_SUCCESS,
    JobRecord,
    append_record,
    classify_error,
    default_ledger_path,
    read_records,
    utcnow_iso,
)


def make_record(**overrides) -> JobRecord:
    base = dict(
        operation_id="op-1",
        operation_type="launchd_job",
        started_at="2026-09-19T15:00:00.000+08:00",
        finished_at="2026-09-19T15:02:00.000+08:00",
        status=STATUS_SUCCESS,
        input_basis="close:2026-09-18",
        output_reference="table:daily_opportunity_scan",
        error_class="none",
        job_name="com.lei.daily_scan",
    )
    base.update(overrides)
    return JobRecord(**base)


class TestJobRecordValidation:
    def test_valid_record_passes(self):
        make_record().validate()

    def test_missing_required_field_rejected(self):
        with pytest.raises(ValueError, match="job_name"):
            make_record(job_name="").validate()

    def test_invalid_status_rejected(self):
        with pytest.raises(ValueError, match="status 非法"):
            make_record(status="running").validate()

    def test_timestamp_must_be_iso_with_timezone(self):
        with pytest.raises(ValueError, match="ISO-8601"):
            make_record(started_at="2026-09-19 15:00").validate()

    def test_finished_before_started_rejected(self):
        with pytest.raises(ValueError, match="早于"):
            make_record(
                started_at="2026-09-19T15:02:00.000+08:00",
                finished_at="2026-09-19T15:00:00.000+08:00",
            ).validate()

    def test_success_must_have_error_class_none(self):
        with pytest.raises(ValueError, match="error_class"):
            make_record(error_class="exit_1").validate()

    def test_failure_requires_error_class(self):
        with pytest.raises(ValueError, match="error_class"):
            make_record(status=STATUS_FAILED, error_class="none").validate()


class TestClassifyError:
    def test_signal_classification(self):
        assert classify_error(signal="SIGTERM") == "killed_by_signal:SIGTERM"

    def test_exit_code_classification(self):
        assert classify_error(returncode=1) == "exit_1"
        assert classify_error(returncode=137) == "exit_137"

    def test_unknown(self):
        assert classify_error() == "unknown"

    def test_signal_takes_precedence(self):
        assert classify_error(returncode=1, signal="SIGKILL") == (
            "killed_by_signal:SIGKILL"
        )


class TestAppendRecord:
    def test_append_only_two_lines(self, tmp_path: Path):
        path = tmp_path / "led" / "job-ledger.jsonl"
        append_record(make_record(), path)
        append_record(
            make_record(
                operation_id="op-2",
                status=STATUS_FAILED,
                error_class="exit_1",
            ),
            path,
        )
        lines = path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        records = read_records(path)
        assert [r["operation_id"] for r in records] == ["op-1", "op-2"]
        assert records[0]["status"] == STATUS_SUCCESS
        assert records[1]["error_class"] == "exit_1"

    def test_first_line_content_roundtrip(self, tmp_path: Path):
        path = tmp_path / "job-ledger.jsonl"
        rec = make_record(extra={"duration_ms": 1234, "command": ["echo", "hi"]})
        append_record(rec, path)
        data = read_records(path)[0]
        assert data["duration_ms"] == 1234
        assert data["command"] == ["echo", "hi"]
        for key in (
            "operation_id", "operation_type", "started_at", "finished_at",
            "status", "input_basis", "output_reference", "error_class", "job_name",
        ):
            assert key in data

    def test_refuses_forbidden_production_dir(self, tmp_path, monkeypatch):
        from lei_signal.jobledger import ledger
        fake_home = tmp_path / "fakehome"
        fake_home.mkdir()
        (fake_home / ".lei_signal_lab" / "paper").mkdir(parents=True)
        monkeypatch.setattr(ledger, "FORBIDDEN_DIR", fake_home / ".lei_signal_lab")
        with pytest.raises(PermissionError):
            append_record(
                make_record(), fake_home / ".lei_signal_lab" / "paper" / "x.jsonl"
            )
        # 父目录本身也拒绝
        with pytest.raises(PermissionError):
            append_record(make_record(), fake_home / ".lei_signal_lab" / "y.jsonl")

    def test_default_path_is_repo_logs_not_production(self):
        path = default_ledger_path()
        assert path.name == "job-ledger.jsonl"
        assert path.parent.name == "logs"
        assert ".lei_signal_lab" not in str(path)

    def test_utcnow_iso_parseable_with_tz(self):
        from datetime import datetime

        ts = utcnow_iso()
        parsed = datetime.fromisoformat(ts)
        assert parsed.tzinfo is not None
