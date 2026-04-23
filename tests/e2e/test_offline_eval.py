import json
from pathlib import Path

from scripts.offline_eval import evaluate, load_fixtures


def test_offline_evaluation_harness_generates_metrics(tmp_path: Path):
    fixtures = load_fixtures(Path("tests/fixtures/tasks"))
    report = __import__("asyncio").run(evaluate(fixtures))

    assert report["summary"]["tasks_total"] == 3
    assert 0.0 <= report["summary"]["quality_avg"] <= 1.0
    assert 0.0 <= report["summary"]["valid_output_rate"] <= 1.0

    output_file = tmp_path / "report.json"
    output_file.write_text(json.dumps(report), encoding="utf-8")
    assert output_file.exists()
