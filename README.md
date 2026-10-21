# dsc26-swe-w04 · Nour transfers: tests that kill mutants

DSC Summer Internship 2026 · Software Engineering track · Week 4
**Python 3.12 · FastAPI 0.141.1 · pytest 9.1.1 · jsonschema 4.26.0** · expected time 2.5–3.5 hours

## Scenario

Nour's head office has a working backend for stock transfers between branches, written by
another team. It is about to go live in 140 pharmacies, and Dr. Mona's team has been burned
before. Your job is not to write the service. It is to write the test suite that would catch it
if anyone broke it. DSC will break it, thirteen different ways, and your score is how many of
those breakages your tests notice.

## Set up

```bash
# repository name exactly dsc26-swe-w04, public, in your own GitHub account
git init -b main
uv venv --python 3.12
source .venv/bin/activate          # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt  # pinned versions; do not change them
pytest -q                           # the 4 public example tests pass already
```

## What you get (do not edit `nour_transfers/` or `contracts/`; the grader replaces both)

- `SPEC.md`: the behaviour, rule by rule. **This is what you test.**
- `nour_transfers/rules.py`: `days_of_cover(stock, avg_daily_sales) -> float | None`,
  `priority(is_chronic, cover_days) -> "urgent" | "high" | "normal"`,
  `can_transfer(from_stock, quantity, reserve) -> bool`.
- `nour_transfers/app.py`: `create_app(stock, items, sales, now) -> FastAPI` with
  `POST /v1/transfers`, `POST /v1/transfers/{id}/approve`, `GET /v1/branches/{branch}/transfers`
  (the destination branch's inbox) and `GET /v1/branches/{branch}/stock/{item_code}`.
- `contracts/transfer_card.schema.json`: the JSON Schema the branch app relies on.
- `tests/conftest.py` with a `client` fixture (two branches, two medicines, a fixed clock) and
  four public example tests in three folders.

The important lines of `SPEC.md`:

- `days_of_cover` is stock divided by average daily sales, and `None` when sales are zero
  ("lasts indefinitely"). Negative inputs raise `ValueError`.
- `priority`: `normal` if cover is `None`; `urgent` if the item is chronic and cover is under 3
  days; otherwise `high` if cover is under 7 days; otherwise `normal`. Priority is computed from
  the **destination** branch's stock and sales when the transfer is requested.
- `can_transfer`: quantity at least 1, and the sending branch keeps at least the item's
  `reserve` afterwards.
- Request: 404 unknown item or branch, 422 same branch or quantity below 1, 409
  `/problems/below-reserve`. Approve: 404 unknown transfer, 409 `/problems/not-pending` if not
  pending, 409 `/problems/below-reserve` if stock has changed; on success, stock moves from
  source to destination exactly once.
- The inbox is sorted urgent, then high, then normal, and by request order within a priority.
- JSON is camelCase; `requestedAt` is ISO 8601 UTC with `Z`. Errors are `application/problem+json`.
- CORS allows exactly `https://branch.nour.example` and `http://localhost:5173`, with credentials.

## What to build

A test suite in three folders, each with at least one passing test:

```
tests/
  conftest.py            # provided; you may add fixtures
  unit/                  # tests of nour_transfers.rules
  api/                   # tests through TestClient
  contract/              # tests of responses against contracts/transfer_card.schema.json
```

Each folder has an `__init__.py` so `pytest -q` can import `nour_transfers` from the repository
root; keep them, and give every new subfolder one too. Test file names must be unique.

Rules for a suite that counts:

- **Test only through the public interface**: the three functions in `rules.py` and the HTTP
  API, as `SPEC.md` describes them. The grader also runs your suite against a rewritten
  implementation with the same behaviour and different internals and private names, so tests
  that import private names (anything not in `SPEC.md`, for example `ALLOWED_ORIGINS`), read or
  hash source files, or patch internals fail there and are dropped. The grader installs every
  implementation **as bytecode only** (no `.py` source), so reading source files fails too.
- Every test must pass on the real implementation, deterministically, with no network.
  Tests that fail are dropped; a suite of `assert False` scores zero.
- No `skip`, `skipif` or `xfail`: they cost you H00.
- The whole suite must run in under 60 s (a careful suite of 20–40 tests takes about 1 s).
- Build your own apps with `create_app(...)` when the shared fixture's data does not set up the
  case you need.

## How grading works

Push to `dsc26-swe-w04`, then press **Submit for grading** on DSC Hex (5 runs per task per day).
The grader clones your latest commit, puts DSC's `nour_transfers/` and `contracts/` over yours,
removes any root `conftest.py` or `pytest.ini` (pytest settings in `pyproject.toml`, `setup.cfg`
or `tox.ini` are ignored), and runs `python -m pytest -q -p no:cacheprovider -p no:warnings
--timeout=20 tests/` from the repository root, network off, 60 s per run, 10 minutes in all:

1. Your suite runs against DSC's reference implementation and against the behaviour-identical
   rewrite. Any test that fails or errors on either is a **false alarm** and is dropped (listed by
   node id in your feedback).
2. The remaining tests run against each of the 13 mutants. A mutant is **killed** if at least
   one of your remaining tests fails.

| ID | Public name | What it checks | Weight |
|---|---|---|---|
| H00 | suite is green and clean | Whole suite passes on the reference and on the rewrite, in under 60 s, with no tests skipped or xfailed and no collection errors | 10 |
| H01 | layout: unit, api and contract each have a passing test | At least one surviving (not dropped) test in each folder | 5 |
| M01 | rules: reserve boundary is off by one | `>=` becomes `>` in `can_transfer` | 7 |
| M02 | rules: zero quantity allowed | Quantity 0 passes `can_transfer` | 6 |
| M03 | rules: chronic flag ignored for urgent | Non-chronic items with low cover become urgent | 7 |
| M04 | rules: urgent boundary moved | Cover of exactly 3 days becomes urgent | 6 |
| M05 | rules: no sales treated as zero cover | `days_of_cover` returns 0.0 instead of `None` | 7 |
| M06 | api: approving twice is allowed | The pending check is removed | 7 |
| M07 | contract: a field leaks in snake_case | One card field is renamed | 7 |
| M08 | contract: requestedAt loses its time zone | Timestamp sent without `Z` or offset | 6 |
| M09 | integration: CORS allows any origin | Origins become `*` | 7 |
| M10 | api: inbox ignores priority | Inbox sorted by request order only | 6 |
| M11 | api: errors lose their problem media type | Errors sent as `application/json` | 6 |
| M12 | api: same-branch transfer accepted | The same-branch check is removed | 6 |
| M13 | api: approval does not credit the destination | Stock leaves the source and never arrives | 7 |
| | | **Total** | **100** |

The four public example tests kill only a few mutants. A careful suite of 20–30 tests kills all
thirteen. The mutant list tells you which areas are attacked, not the exact code change; the only
way to kill them is to test the spec.

## AI_USAGE.md

AI tools are allowed. Keep the three headings `## Tools`, `## What AI got wrong` and
`## In my own words`; if the file or a heading is missing, the grader stops and gives 0 with
the reason "AI_USAGE.md missing or incomplete". Under `## In my own words`, answer without AI:
"Pick one mutant your first draft of tests did not kill. Why not, and what did you add?" and
"Why is a test that only asserts `status_code == 409` weaker than one that asserts the problem
`type`?"

Late policy: ×1.0 within 72 hours of the session starting, ×0.6 for the following 7 days,
×0.5 after that until Thu 3 Dec 23:59. W5 reopens W2–W4 at ×1.0. Your best attempt counts.
