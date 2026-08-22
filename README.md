# PRISM Backend

Private maintainer tools and publishing service for the **PRISM** benchmark pipeline.

- Desktop App: [`Nabin-16/PRISM-Reliability-test-`](https://github.com/Nabin-16/PRISM-Reliability-test-)
- Public Data Archive: [`Nabin-16/Reliability-test-result-model-versions`](https://github.com/Nabin-16/Reliability-test-result-model-versions)

---

## Architecture

```text
PRISM Desktop App  (runs benchmark locally, submits result)
        │
        ▼
    Supabase        (private review queue — submissions land as approved=false)
        │
        │  ◄── Review/Approve/Publish using tools in THIS repository
        ▼
Public GitHub Repo  (Nabin-16/Reliability-test-result-model-versions)
        │
        ▼
Desktop App / Website  (fetch verified results directly from GitHub)
```

---

## Maintainer Tools

### 1. `scripts/approve_runs.py` — Review Queue

Inspect, approve, or reject user submissions in the Supabase staging queue:

```powershell
# Set credentials:
$env:PRISM_SUPABASE_URL="https://memineeqsblrgyyjxtpa.supabase.co"
$env:PRISM_SUPABASE_SECRET_KEY="<your-secret-key>"

# View pending submissions
python scripts/approve_runs.py list

# Approve a run by ID
python scripts/approve_runs.py approve <benchmark_run_id> --by "YourName"

# Approve all pending runs
python scripts/approve_runs.py approve-all --by "YourName"

# Reject and remove a bad submission
python scripts/approve_runs.py reject <benchmark_run_id>
```

### 2. `scripts/publish_to_github.py` — Publish Approved Results

Fetches all `approved = true` runs from Supabase and pushes the clean result files directly to the public GitHub repository:

```powershell
$env:PRISM_SUPABASE_URL="https://memineeqsblrgyyjxtpa.supabase.co"
$env:PRISM_SUPABASE_SECRET_KEY="<your-secret-key>"
$env:GITHUB_PAT="<github-personal-access-token-with-repo-write-scope>"

python scripts/publish_to_github.py
```

---

## Automated Publishing

This repository includes a GitHub Actions workflow (`.github/workflows/publish-results.yml`) that runs on a weekly schedule or manual dispatch.

Configure the following GitHub Secrets in **PRISM-backend → Settings → Secrets & Variables → Actions**:
- `PRISM_SUPABASE_URL`
- `PRISM_SUPABASE_SECRET_KEY`
- `PUBLIC_REPO_PUBLISH_PAT` (GitHub PAT with write access to `Nabin-16/Reliability-test-result-model-versions`)

---

## Setup & Dependencies

```bash
pip install requests
```
