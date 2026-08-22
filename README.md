# PRISM Backend

This repository contains the **maintainer-side tools** for the PRISM benchmark pipeline.

---

## What This Repository Does

PRISM runs on a three-layer architecture:

```text
PRISM Desktop App  (runs benchmark locally, submits result)
        │
        ▼
    Supabase        (private staging queue — all submissions land here as approved=false)
        │
        │  ◄── You review and approve here, using scripts in THIS repo
        ▼
Public GitHub Repo  (Nabin-16/Reliability-test-result-model-versions)
        │
        ▼
Desktop App / Website  (fetch verified results from GitHub)
```

When a user runs a benchmark and submits it:
- Their result goes to **Supabase** with `approved = false`.
- Nothing becomes public automatically.
- A maintainer (you) runs the scripts here to inspect and approve or reject submissions.
- Once approved, the GitHub Actions workflow in the public results repo fetches and publishes only the `approved = true` rows.

---

## Scripts

### `scripts/approve_runs.py`



```powershell
# Set credentials first (never commit these):
$env:PRISM_SUPABASE_URL="https://memineeqsblrgyyjxtpa.supabase.co"
$env:PRISM_SUPABASE_SECRET_KEY="<your-secret-key>"

# See what is waiting for review:
python scripts/approve_runs.py list

# Approve a specific run by its ID:
python scripts/approve_runs.py approve <benchmark_run_id> --by "YourName"

# Approve everything currently pending (use carefully):
python scripts/approve_runs.py approve-all --by "YourName"

# Reject and permanently remove a bad submission:
python scripts/approve_runs.py reject <benchmark_run_id>
```

After running `approve`, trigger the sync workflow in the public results repository to publish:
- Go to **[Reliability-test-result-model-versions → Actions → Sync Verified PRISM Results](https://github.com/Nabin-16/Reliability-test-result-model-versions/actions/workflows/sync-results.yml)**
- Click **Run workflow**.

### `scripts/push_bundled_results_to_supabase.py`

For pushing the project's own validated reference results (the "bundled seed" that ships with the desktop app) into Supabase with the secret key. Regular users never run this.

```powershell
$env:PRISM_SUPABASE_URL="https://memineeqsblrgyyjxtpa.supabase.co"
$env:PRISM_SUPABASE_SECRET_KEY="<your-secret-key>"

python scripts/push_bundled_results_to_supabase.py
```

---

## Setup

1. **Clone this repository.**

2. **Install the only dependency:**
   ```bash
   pip install requests
   ```

3. **Set credentials as environment variables**


---
