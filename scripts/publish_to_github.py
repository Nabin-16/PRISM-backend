#!/usr/bin/env python3
"""
publish_to_github.py
====================
PRISM Backend Publishing Tool.

Fetches approved benchmark runs (approved=true) from Supabase and publishes the
clean, public results dataset directly to the public GitHub repository:
https://github.com/Nabin-16/Reliability-test-result-model-versions

Usage:
    # 1. Provide credentials in environment (or .env):
    export PRISM_SUPABASE_URL="https://memineeqsblrgyyjxtpa.supabase.co"
    export PRISM_SUPABASE_SECRET_KEY="<your-secret-key>"
    export GITHUB_PAT="<github-personal-access-token-with-repo-scope>"

    # 2. Run publisher:
    python scripts/publish_to_github.py
"""

from __future__ import annotations

import csv
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

REQUEST_TIMEOUT = 30
PUBLIC_REPO_URL = "https://github.com/Nabin-16/Reliability-test-result-model-versions.git"

CSV_METRIC_COLUMNS = [
    ("prompt_response_accuracy", "Accuracy (%)"),
    ("conditional_accuracy", "Conditional Accuracy (%)"),
    ("answer_recovery_rate", "Answer Recovery (%)"),
    ("instruction_compliance_rate", "Instruction Compliance (%)"),
    ("question_majority_accuracy", "Question Majority Accuracy (%)"),
    ("mean_agreement", "Agreement (%)"),
    ("mean_prompt_sensitivity", "Prompt Sensitivity (%)"),
    ("answer_unanimous_rate", "Answer Unanimous Rate (%)"),
    ("prompt_invariant_incorrect_rate", "Prompt-Invariant Incorrect Rate (%)"),
]


def safe_model_filename(model_name: str) -> str:
    clean = model_name.replace(":", "_").replace("/", "_").replace("-", "_")
    if clean.endswith("_latest"):
        clean = clean[:-7]
    return clean


def format_percent(value: Any) -> str:
    if value is None:
        return ""
    try:
        f = float(value)
        return f"{f * 100:.1f}"
    except (ValueError, TypeError):
        return str(value)


def get_client() -> tuple[str, dict[str, str]]:
    url = (
        os.environ.get("PRISM_SUPABASE_URL")
        or os.environ.get("SUPABASE_URL", "")
    ).rstrip("/")
    key = (
        os.environ.get("PRISM_SUPABASE_SECRET_KEY")
        or os.environ.get("SUPABASE_SECRET_KEY")
        or os.environ.get("PRISM_SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    )

    if not url or not key:
        print(
            "ERROR: Missing Supabase credentials. Set PRISM_SUPABASE_URL and "
            "PRISM_SUPABASE_SECRET_KEY in your environment.",
            file=sys.stderr,
        )
        sys.exit(1)

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    return url, headers


def fetch_approved_runs(url: str, headers: dict) -> list[dict]:
    resp = requests.get(
        f"{url}/rest/v1/runs",
        headers=headers,
        params={
            "select": "*",
            "approved": "eq.true",
            "status": "eq.completed",
            "order": "created_utc.desc",
        },
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_run_results(url: str, headers: dict, run_id: str) -> list[dict]:
    resp = requests.get(
        f"{url}/rest/v1/run_results",
        headers=headers,
        params={
            "select": "*",
            "benchmark_run_id": f"eq.{run_id}",
        },
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def build_model_record(run: dict, results: list[dict]) -> dict:
    datasets_dict = {}
    for r in sorted(results, key=lambda x: x.get("dataset", "")):
        d_name = r.get("dataset", "")
        if not d_name:
            continue
        datasets_dict[d_name] = {
            "n_questions": r.get("n_questions", 200),
            "accuracy": r.get("prompt_response_accuracy"),
            "conditional_accuracy": r.get("conditional_accuracy"),
            "answer_recovery_rate": r.get("answer_recovery_rate"),
            "instruction_compliance_rate": r.get("instruction_compliance_rate"),
            "question_majority_accuracy": r.get("question_majority_accuracy"),
            "agreement": r.get("mean_agreement"),
            "prompt_sensitivity": r.get("mean_prompt_sensitivity"),
            "answer_unanimous_rate": r.get("answer_unanimous_rate"),
            "prompt_invariant_incorrect_rate": r.get("prompt_invariant_incorrect_rate"),
        }

    return {
        "benchmark_run_id": run["benchmark_run_id"],
        "model": run["model"],
        "model_digest": run.get("model_digest"),
        "protocol_version": run.get("protocol_version", "1.0"),
        "created_utc": run["created_utc"],
        "datasets": datasets_dict,
    }


def generate_results_tree(out_dir: Path, runs: list[dict], all_results: dict[str, list]) -> None:
    results_dir = out_dir / "results"
    models_dir = results_dir / "models"

    if models_dir.exists():
        shutil.rmtree(models_dir)
    models_dir.mkdir(parents=True)

    index_entries = []
    summary_rows = []

    for run in runs:
        run_id = run["benchmark_run_id"]
        results = all_results.get(run_id, [])

        record = build_model_record(run, results)
        fname = safe_model_filename(run["model"]) + ".json"
        (models_dir / fname).write_text(
            json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        index_entries.append({
            "benchmark_run_id": run_id,
            "created_utc": run["created_utc"],
            "datasets": sorted(run.get("datasets") or []),
            "model": run["model"],
            "model_digest": run.get("model_digest"),
            "protocol_version": run.get("protocol_version", "1.0"),
        })

        for r in results:
            row = {
                "model": run["model"],
                "dataset": r.get("dataset", ""),
                "n_questions": r.get("n_questions", ""),
                "n_prompt_variants": r.get("n_prompt_variants", ""),
            }
            for key, _ in CSV_METRIC_COLUMNS:
                row[key] = format_percent(r.get(key))
            summary_rows.append(row)

    (results_dir / "index.json").write_text(
        json.dumps(index_entries, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    if summary_rows:
        csv_fieldnames = (
            ["model", "dataset", "n_questions", "n_prompt_variants"]
            + [col for _, col in CSV_METRIC_COLUMNS]
        )
        display_rows = []
        for row in summary_rows:
            d = {
                "model": row["model"],
                "dataset": row["dataset"],
                "n_questions": row["n_questions"],
                "n_prompt_variants": row["n_prompt_variants"],
            }
            for key, header in CSV_METRIC_COLUMNS:
                d[header] = row[key]
            display_rows.append(d)

        with (results_dir / "summary.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=csv_fieldnames)
            writer.writeheader()
            writer.writerows(display_rows)

    summary_json = []
    for run in runs:
        run_id = run["benchmark_run_id"]
        for r in all_results.get(run_id, []):
            entry = {
                "model": run["model"],
                "dataset": r.get("dataset", ""),
                "n_questions": r.get("n_questions"),
                "n_prompt_variants": r.get("n_prompt_variants"),
            }
            for key, _ in CSV_METRIC_COLUMNS:
                entry[key] = r.get(key)
            summary_json.append(entry)

    (results_dir / "summary.json").write_text(
        json.dumps(summary_json, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def publish_via_git(repo_dir: Path, github_pat: str | None = None) -> bool:
    import subprocess

    def run_git(args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "-C", str(repo_dir)] + args,
            capture_output=True,
            text=True,
            check=True,
        )

    try:
        run_git(["config", "user.name", "PRISM Publisher Bot"])
        run_git(["config", "user.email", "actions@github.com"])
        run_git(["add", "results/"])

        diff = subprocess.run(
            ["git", "-C", str(repo_dir), "diff", "--staged", "--quiet"]
        )
        if diff.returncode == 0:
            print("No changes detected in results/. Public repo is already up to date.")
            return True

        run_git(["commit", "-m", "update verified benchmark results snapshot"])

        if github_pat:
            auth_url = PUBLIC_REPO_URL.replace("https://", f"https://x-access-token:{github_pat}@")
            run_git(["push", auth_url, "main"])
        else:
            run_git(["push", "origin", "main"])

        print("Successfully published updated results to GitHub.")
        return True
    except subprocess.CalledProcessError as exc:
        print(f"Git operation failed: {exc.stderr}", file=sys.stderr)
        return False


def main() -> int:
    url, headers = get_client()

    print("Querying Supabase for approved benchmark runs...")
    runs = fetch_approved_runs(url, headers)

    if not runs:
        print("No approved runs found in Supabase staging queue.")
        return 0

    print(f"Found {len(runs)} approved run(s). Fetching metrics...")
    all_results: dict[str, list] = {}
    for run in runs:
        rid = run["benchmark_run_id"]
        all_results[rid] = fetch_run_results(url, headers, rid)

    pat = os.environ.get("GITHUB_PAT") or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    local_target = os.environ.get("PUBLIC_REPO_PATH")

    if local_target and Path(local_target).exists():
        target_path = Path(local_target)
        generate_results_tree(target_path, runs, all_results)
        print(f"Results generated at: {target_path / 'results'}")
        publish_via_git(target_path, pat)
    else:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_repo = Path(tmpdir) / "repo"
            import subprocess
            print("Cloning public repository...")
            clone_url = PUBLIC_REPO_URL
            if pat:
                clone_url = PUBLIC_REPO_URL.replace("https://", f"https://x-access-token:{pat}@")
            subprocess.run(["git", "clone", "--depth", "1", clone_url, str(temp_repo)], check=True)

            generate_results_tree(temp_repo, runs, all_results)
            publish_via_git(temp_repo, pat)

    print("Publish process completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
