# Nour stock transfers · behaviour specification

This is what `nour_transfers/` does. Write your tests against this document and the public
interface only: the three functions in `nour_transfers/rules.py` and the HTTP API built by
`nour_transfers.app.create_app`. Anything not written here is an implementation detail that
the grader's rewrite does differently.

## 1. Rules (`nour_transfers/rules.py`)

### `days_of_cover(stock, avg_daily_sales) -> float | None`

- How many days the stock lasts: `stock / avg_daily_sales` (true division, a float).
- If `avg_daily_sales` is 0, returns `None` ("no sales, lasts indefinitely"), whatever the stock.
- If `stock` or `avg_daily_sales` is negative, raises `ValueError`.

### `priority(is_chronic, cover_days) -> "urgent" | "high" | "normal"`

1. `cover_days` is `None` → `"normal"`.
2. `is_chronic` and `cover_days < 3` → `"urgent"`.
3. otherwise `cover_days < 7` → `"high"` (chronic or not).
4. otherwise → `"normal"`.

### `can_transfer(from_stock, quantity, reserve) -> bool`

`True` exactly when `quantity >= 1` and `from_stock - quantity >= reserve` (the sending branch
keeps at least the item's reserve afterwards). Always returns a real `bool`.

## 2. The app: `create_app(stock, items, sales, now) -> FastAPI`

- `stock`: `{(branch, item_code): units}`. The known branches are exactly the branches that
  appear in `stock`. A (branch, item) pair not in `stock` has 0 units.
- `items`: `{item_code: {"chronic": bool, "reserve": int}}`. The known items.
- `sales`: `{(branch, item_code): average daily sales}`; a missing pair means 0.
- `now`: a callable returning a timezone-aware `datetime`, called once per transfer request.
- Every call to `create_app` starts with no transfers. Data passed in is copied.

### JSON and errors

- All JSON field names are camelCase.
- A **transfer card** (every transfer the API returns) is exactly:
  `id` (`"tr_1"`, `"tr_2"`, … in request order, per app), `itemCode`, `fromBranch`, `toBranch`,
  `quantity`, `priority`, `status` (`"pending"` or `"approved"`), `requestedAt`.
  It matches `contracts/transfer_card.schema.json` (no other fields).
- `requestedAt` is `now()` at request time in ISO 8601; for a UTC time it ends in `Z`
  (for example `2026-11-03T09:30:00Z`).
- **Every** error is `application/problem+json` with `type`, `title` and `status` (the HTTP
  status). Body validation errors also have `errors`, a list of `{"loc", "msg"}`.

### `POST /v1/transfers`

Body: `{"itemCode": str, "fromBranch": str, "toBranch": str, "quantity": int}`. Unknown extra
fields are ignored. Checked in this order:

| Check | Status | Problem `type` |
|---|---|---|
| Body is not valid (missing field, wrong type, `quantity` below 1) | 422 | `/problems/validation` |
| `itemCode` is not a known item | 404 | `/problems/unknown-item` |
| `fromBranch` or `toBranch` is not a known branch | 404 | `/problems/unknown-branch` |
| `fromBranch` equals `toBranch` | 422 | `/problems/same-branch` |
| `can_transfer(source units, quantity, item reserve)` is false | 409 | `/problems/below-reserve` |

On success: **201** with the new card, `status: "pending"`. Its `priority` is
`priority(item chronic, days_of_cover(destination units, destination sales))`, computed from the
**destination** branch's stock and sales at request time and never recomputed. A request does
not move any stock.

### `POST /v1/transfers/{id}/approve`

| Check | Status | Problem `type` |
|---|---|---|
| No transfer with this id | 404 | `/problems/unknown-transfer` |
| Transfer is not pending (already approved) | 409 | `/problems/not-pending` |
| `can_transfer(current source units, quantity, reserve)` is false (stock has changed since the request) | 409 | `/problems/below-reserve` |

On success: **200** with the card, `status: "approved"`, and the quantity moves from the source
branch to the destination branch exactly once (source minus quantity, destination plus quantity).
A refused approval changes nothing.

### `GET /v1/branches/{branch}/transfers` (the destination branch's inbox)

**200** `{"items": [cards]}`: every transfer whose `toBranch` is `branch`, pending and approved,
sorted `urgent`, then `high`, then `normal`, and by request order within a priority. A branch
with no transfers (or an unknown branch) gets `{"items": []}`.

### `GET /v1/branches/{branch}/stock/{itemCode}`

**200** `{"branch": branch, "itemCode": itemCode, "units": int}` with the current units
(0 for an unknown branch or item).

### CORS

The branch web app calls the API from the browser. CORS allows exactly the origins
`https://branch.nour.example` and `http://localhost:5173`, with credentials
(`Access-Control-Allow-Credentials: true`), methods `GET` and `POST`, and request headers
`Authorization` and `Content-Type`.

- A preflight (`OPTIONS` with `Origin` and `Access-Control-Request-Method`) from an allowed
  origin gets 200 and `Access-Control-Allow-Origin` equal to that origin.
- A preflight from any other origin gets 400 and no `Access-Control-Allow-Origin` header.
- A normal request from an allowed origin gets `Access-Control-Allow-Origin` equal to that
  origin; from any other origin it gets no `Access-Control-Allow-Origin` header.
