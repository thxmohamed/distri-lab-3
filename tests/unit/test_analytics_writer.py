import json

from civicmesh.analytics import MetricsWriter


def test_write_appends_jsonl_lines(tmp_path):

    writer = MetricsWriter(
        tmp_path / "metrics",
        "peer-1",
    )

    writer.write({"topic": "maipu", "value": 1})
    writer.write({"topic": "maipu", "value": 2})

    output = tmp_path / "metrics" / "peer-1.jsonl"

    lines = output.read_text(
        encoding="utf-8"
    ).splitlines()

    assert len(lines) == 2
    assert json.loads(lines[0]) == {
        "topic": "maipu",
        "value": 1,
    }
    assert json.loads(lines[1]) == {
        "topic": "maipu",
        "value": 2,
    }


def test_write_creates_metrics_dir_if_missing(tmp_path):

    metrics_dir = tmp_path / "runs" / "run-1" / "metrics"

    MetricsWriter(metrics_dir, "peer-1").write(
        {"topic": "maipu", "value": 1}
    )

    assert metrics_dir.is_dir()
    assert (metrics_dir / "peer-1.jsonl").exists()
