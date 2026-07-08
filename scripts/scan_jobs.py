#!/usr/bin/env python3
"""
Queries Greenhouse, Lever, and Ashby public job-board APIs directly for the
companies in agent/companies.json, filters by title/location against
agent/criteria.json, and prints matches as JSON.

This talks to the open internet directly (no Claude tools involved), so it
must be run somewhere with real outbound HTTPS access — it will NOT work
inside a network-restricted sandbox. Run it on your own machine, a CI job,
or a cron box.

Usage:
    pip install requests
    python3 scripts/scan_jobs.py [--out results.json]

Notes:
- ats_guess in companies.json is unverified; this script tries the guessed
  ATS first, and silently skips companies where the guess is wrong or the
  board doesn't exist (rather than trying every ATS for every company).
- Company "slugs" (the token in the API URL) are inferred from the company
  name and may not match reality — check results.json's "errors" list for
  companies that failed to resolve and fix the slug in companies.json.
"""
import argparse
import json
import re
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE_DIR = Path(__file__).resolve().parent.parent
AGENT_DIR = BASE_DIR / "agent"


def slugify(name: str) -> str:
    name = re.split(r"[\(/]", name)[0].strip()
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def fetch_json(url: str, timeout: int = 10):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (job-scanner)"})
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_greenhouse(slug: str):
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    data = fetch_json(url)
    out = []
    for job in data.get("jobs", []):
        out.append({
            "title": job.get("title", ""),
            "location": (job.get("location") or {}).get("name", ""),
            "url": job.get("absolute_url", ""),
        })
    return out


def fetch_lever(slug: str):
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    data = fetch_json(url)
    out = []
    for job in data:
        out.append({
            "title": job.get("text", ""),
            "location": (job.get("categories") or {}).get("location", ""),
            "url": job.get("hostedUrl", ""),
        })
    return out


def fetch_ashby(slug: str):
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    data = fetch_json(url)
    out = []
    for job in data.get("jobs", []):
        out.append({
            "title": job.get("title", ""),
            "location": job.get("location", ""),
            "url": job.get("jobUrl", ""),
        })
    return out


FETCHERS = {"greenhouse": fetch_greenhouse, "lever": fetch_lever, "ashby": fetch_ashby}


def load_criteria():
    return json.loads((AGENT_DIR / "criteria.json").read_text())


def load_companies():
    return json.loads((AGENT_DIR / "companies.json").read_text())["companies"]


def title_matches(title: str, criteria: dict):
    title_l = title.lower()
    if any(kw in title_l for kw in criteria["exclude_keywords"]):
        return None
    for role in criteria["roles"]:
        names = [role["title"]] + role["aliases"]
        if any(n.lower() in title_l for n in names):
            return role["id"]
    return None


def location_matches(location: str, criteria: dict):
    loc_l = location.lower()
    return any(inc.lower() in loc_l for inc in criteria["locations"]["include"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(BASE_DIR / "results.json"))
    args = parser.parse_args()

    criteria = load_criteria()
    companies = load_companies()

    matches = []
    errors = []

    for company in companies:
        name = company["name"]
        ats = company.get("ats_guess")
        fetcher = FETCHERS.get(ats)
        if not fetcher:
            continue
        slug = slugify(name)
        try:
            jobs = fetcher(slug)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as e:
            errors.append({"company": name, "slug": slug, "ats": ats, "error": str(e)})
            continue

        for job in jobs:
            role_id = title_matches(job["title"], criteria)
            if not role_id:
                continue
            if not location_matches(job.get("location", ""), criteria):
                continue
            matches.append({
                "company": name,
                "role_id": role_id,
                "title": job["title"],
                "location": job.get("location", ""),
                "url": job.get("url", ""),
            })

    result = {"matches": matches, "errors": errors}
    Path(args.out).write_text(json.dumps(result, indent=2))
    print(f"Found {len(matches)} matches, {len(errors)} companies failed to resolve.", file=sys.stderr)
    print(f"Wrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
