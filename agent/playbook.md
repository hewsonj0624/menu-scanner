# Job scan playbook

This is what the scheduled Routine (and any on-demand run) executes. It's
written for Claude to follow inside this session, using the `WebSearch` tool
— not a script — because this sandbox's egress policy blocks direct fetches
to job boards and ATS APIs (`WebFetch` and raw HTTP both return 403 to hosts
like `boards-api.greenhouse.io`, `api.lever.co`, even generic sites). `WebSearch`
works because it's Anthropic-hosted rather than a direct fetch from this
container.

## Steps

1. Read `agent/criteria.json` for roles, spaces, locations, exclusions.
2. Read `agent/companies.json` for the curated company list (search hints).
3. Read `agent/seen_jobs.json` for postings already surfaced — never re-report
   these unless they've materially changed.
4. Run a batch of `WebSearch` queries covering:
   - Role x space x location combos, e.g. `"senior product manager" fraud jobs San Francisco`,
     `"senior product manager" payments jobs New York`, `chief of staff startup jobs Seattle`.
   - ATS-flavored queries to surface Greenhouse/Lever/Ashby postings, e.g.
     `senior product manager fraud jobs greenhouse OR lever OR ashby`.
   - A handful of company-specific queries from `companies.json` for the
     highest-priority names (rotate through the list across runs so every
     company gets checked periodically, not just the first few).
5. From results, extract candidate postings (title, company, location, URL).
6. Filter against criteria.json:
   - Title must match one of the role names/aliases.
   - Location must be SF/Bay Area, NYC, or Seattle (or explicit remote-eligible
     from a company HQ'd in one of those).
   - Exclude junior/intern/associate-level titles.
   - For Senior PM: prefer postings that clearly signal fraud, payments, or
     startup/high-growth context (job title, snippet, or known company space).
7. Drop anything already in `seen_jobs.json` (match by URL; fall back to
   normalized title+company if URL varies).
8. Rank remaining matches: fraud/payments PM roles and CoS-to-CEO roles at
   named startups rank highest; generic/large-company matches rank lower.
9. Append newly surfaced postings to `agent/seen_jobs.json` with today's date.
10. Write a dated digest to `digests/YYYY-MM-DD.md` (see existing digests for
    format).
11. Commit and push the updated `seen_jobs.json` and digest to the repo.
12. Message the user with the ranked shortlist, grouped by Senior PM vs Chief
    of Staff, each with title, company, location, link, and a one-line reason
    it fits. If a cycle turns up nothing new, say so briefly rather than
    sending an empty digest.

## Known limitation

Coverage depends on what's indexed by web search, not a live ATS crawl — it
will lag or miss postings a direct API poll would catch. `scripts/scan_jobs.py`
exists for exactly that gap: run it from a machine with normal internet access
for a direct, complete pull from Greenhouse/Lever/Ashby's public APIs.
