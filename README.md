# Job scanner

Finds and ranks open roles matching:

- **Senior Product Manager** in fraud, payments, or startup spaces
- **Chief of Staff** at startups

Locations: San Francisco, New York City, Seattle.

## How it works

There are two complementary sourcing paths:

1. **`agent/`** — a WebSearch-driven scan that Claude runs on a schedule
   inside this session (see `agent/playbook.md`). It searches LinkedIn and
   ATS-hosted boards (Greenhouse/Lever/Ashby) via search engine results,
   filters against `agent/criteria.json`, dedupes against
   `agent/seen_jobs.json`, and pushes a ranked digest to `digests/`. This is
   the automated path — a recurring Routine triggers it and messages you
   the results.

2. **`scripts/scan_jobs.py`** — a standalone script that hits the
   Greenhouse/Lever/Ashby public job-board APIs directly for the companies
   in `agent/companies.json`. It's more complete and reliable than search-engine
   discovery, but it needs real outbound internet access, which this sandboxed
   session doesn't have (its egress policy blocks direct fetches to job
   boards). Run it yourself:

   ```
   pip install requests
   python3 scripts/scan_jobs.py
   ```

   Check `results.json`'s `errors` list — `ats_guess` and slugs in
   `agent/companies.json` are unverified guesses, so some companies will
   fail to resolve until you fix their entry.

## Files

- `agent/criteria.json` — roles, aliases, space keywords, locations, exclusions.
- `agent/companies.json` — curated target company list (search hints, not exhaustive).
- `agent/seen_jobs.json` — dedup state; postings already surfaced to you.
- `agent/playbook.md` — the step-by-step the automated scan follows.
- `digests/` — one dated markdown file per scan run.
- `scripts/scan_jobs.py` — standalone direct-API scanner (run outside this sandbox).

## Tuning

Edit `agent/criteria.json` to adjust roles, locations, or excluded keywords,
and `agent/companies.json` to add/remove target companies. Next scan picks up
the changes automatically.
