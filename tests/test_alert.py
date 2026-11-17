"""Offline tests: digest building and the Slack / e-mail / Markdown renderers (no network, no Apify token).

Run: pip install -r requirements.txt pytest && pytest -q
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import alert  # noqa: E402

FIXTURE = json.loads((ROOT / "tests" / "fixtures" / "sample_items.json").read_text(encoding="utf-8"))  # real Actor output


class FakeKV:
    def __init__(self, summary):
        self.summary = summary

    def get_record(self, key):
        return {"key": key, "value": self.summary} if key == "SUMMARY" and self.summary is not None else None


@pytest.fixture
def cfg():
    return alert.load_config(ROOT / "config.yml")


def test_slack_payload_from_real_sample(cfg):
    digest, kept = alert.make_digest(FIXTURE, cfg, None)
    assert digest.total == len(kept) == len(FIXTURE)
    payload = alert.build_slack_payload(digest)
    json.dumps(payload)
    blocks = payload["blocks"]
    assert payload["text"] and blocks[0]["type"] == "header"
    assert len(blocks) <= alert.MAX_SLACK_BLOCKS
    sections = [b for b in blocks if b["type"] == "section"]
    assert len(sections) == len(digest.entries) == min(len(FIXTURE), cfg["alert"]["max_items_in_message"])
    for b, e in zip(sections, digest.entries):
        assert f"<{e.url}|" in b["text"]["text"] and len(b["text"]["text"]) <= 3000
    sites = {it["site"] for it in FIXTURE}
    assert all(s in digest.summary for s in sites)


def test_baseline_run_is_silent_and_explained(cfg):
    kv = FakeKV({"sites": [{"input": "a.com", "site": "a.com", "urlsScanned": 50, "baseline": True},
                           {"input": "b.com", "site": "b.com", "urlsScanned": 20, "baseline": True}]})
    digest, kept = alert.make_digest([], cfg, kv)
    assert digest.total == 0 and kept == []
    assert digest.summary.startswith("Baseline recorded for 2 site(s)")
    assert any("Baseline recorded for a.com, b.com" in n for n in digest.notes)


def test_problems_become_notes(cfg):
    kv = FakeKV({"stoppedReason": "max charge limit reached",
                 "sites": [{"input": "broken.example", "site": "broken.example", "urlsScanned": 0, "errors": ["HTTP 404"]},
                           {"input": "big.com", "site": "big.com", "urlsScanned": 9, "stoppedAtMaxUrlsPerSite": True}]})
    digest, _ = alert.make_digest([], cfg, kv)
    text = " ".join(digest.notes)
    assert "max charge limit" in text and "HTTP 404" in text and "maxUrlsPerSite" in text
    assert digest.summary.startswith("No new pages since the last run (9 URLs checked)")


def test_input_forces_monitoring_mode(cfg):
    run_input = alert.build_input(cfg)
    assert run_input["onlyNew"] is True and run_input["emitOnBaseline"] is False
    assert run_input["stateKey"] == cfg["input"]["stateKey"]
    with pytest.raises(SystemExit):
        alert.build_input({"input": {"sites": []}, "alert": {}})


def test_email_and_markdown_render(cfg):
    digest, _ = alert.make_digest(FIXTURE, cfg, None)
    subject, text, html_body = alert.render_email(digest)
    md = alert.render_markdown(digest)
    assert subject and digest.entries[0].url in text and digest.entries[0].url in html_body and digest.entries[0].url in md


def test_items_file_dry_run(tmp_path, monkeypatch):
    for k in ("SLACK_WEBHOOK_URL", "SMTP_HOST", "GITHUB_STEP_SUMMARY"):
        monkeypatch.delenv(k, raising=False)
    out = tmp_path / "out"
    rc = alert.main(["--config", str(ROOT / "config.yml"), "--out", str(out), "--dry-run",
                     "--items-file", str(ROOT / "tests" / "fixtures" / "sample_items.json")])
    assert rc == 0 and (out / "digest.md").exists() and (out / "items.csv").exists()


def test_missing_token_on_schedule_is_a_warning_not_a_failure(monkeypatch, tmp_path):
    monkeypatch.delenv("APIFY_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_EVENT_NAME", "schedule")
    assert alert.main(["--config", str(ROOT / "config.yml"), "--out", str(tmp_path)]) == 0
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    assert alert.main(["--config", str(ROOT / "config.yml"), "--out", str(tmp_path)]) == 2
