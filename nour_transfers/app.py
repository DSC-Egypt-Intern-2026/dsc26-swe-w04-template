"""Nour stock transfers between branches: the HTTP API. DSC-owned; the grader replaces this package."""
import itertools
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from starlette.exceptions import HTTPException as StarletteHTTPException

from nour_transfers import rules

ALLOWED_ORIGINS = ["https://branch.nour.example", "http://localhost:5173"]
PROBLEM = "application/problem+json"


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel)


class TransferRequest(CamelModel):
    item_code: str
    from_branch: str
    to_branch: str
    quantity: int = Field(ge=1)


class ApiError(Exception):
    def __init__(self, status: int, slug: str, title: str):
        self.status, self.slug, self.title = status, slug, title


def create_app(stock: dict | None = None, items: dict | None = None, sales: dict | None = None, now=None) -> FastAPI:
    """stock: {(branch, item): units}; items: {item: {"chronic": bool, "reserve": int}};
    sales: {(branch, item): avg daily sales}; now: callable returning an aware datetime."""
    app = FastAPI(title="Nour stock transfers")
    app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_credentials=True,
                       allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type"])
    stock = dict(stock or {})
    items = dict(items or {})
    sales = dict(sales or {})
    now = now or (lambda: datetime.now(UTC))
    branches = {b for b, _ in stock}
    transfers: dict[str, dict] = {}
    seq = itertools.count(1)

    @app.exception_handler(ApiError)
    async def _err(_: Request, e: ApiError):
        return JSONResponse({"type": f"/problems/{e.slug}", "title": e.title, "status": e.status},
                            status_code=e.status, media_type=PROBLEM)

    @app.exception_handler(RequestValidationError)
    async def _invalid(_: Request, e: RequestValidationError):
        return JSONResponse({"type": "/problems/validation", "title": "Request is not valid", "status": 422,
                             "errors": [{"loc": list(x["loc"]), "msg": x["msg"]} for x in e.errors()]},
                            status_code=422, media_type=PROBLEM)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, e: StarletteHTTPException):
        return JSONResponse({"type": "about:blank", "title": str(e.detail), "status": e.status_code},
                            status_code=e.status_code, media_type=PROBLEM, headers=e.headers)

    def card(t: dict) -> dict:
        return {"id": t["id"], "itemCode": t["item"], "fromBranch": t["from"], "toBranch": t["to"],
                "quantity": t["qty"], "priority": t["priority"], "status": t["status"],
                "requestedAt": t["at"].isoformat().replace("+00:00", "Z")}

    @app.post("/v1/transfers", status_code=201)
    def request_transfer(body: TransferRequest):
        if body.item_code not in items:
            raise ApiError(404, "unknown-item", "Unknown item")
        if body.from_branch not in branches or body.to_branch not in branches:
            raise ApiError(404, "unknown-branch", "Unknown branch")
        if body.from_branch == body.to_branch:
            raise ApiError(422, "same-branch", "Source and destination must differ")
        info = items[body.item_code]
        have = stock.get((body.from_branch, body.item_code), 0)
        if not rules.can_transfer(have, body.quantity, info["reserve"]):
            raise ApiError(409, "below-reserve", "Transfer would break the reserve")
        dest_stock = stock.get((body.to_branch, body.item_code), 0)
        cover = rules.days_of_cover(dest_stock, sales.get((body.to_branch, body.item_code), 0.0))
        t = {"id": f"tr_{next(seq)}", "item": body.item_code, "from": body.from_branch, "to": body.to_branch,
             "qty": body.quantity, "priority": rules.priority(info["chronic"], cover),
             "status": "pending", "at": now()}
        transfers[t["id"]] = t
        return card(t)

    @app.post("/v1/transfers/{transfer_id}/approve")
    def approve(transfer_id: str):
        t = transfers.get(transfer_id)
        if t is None:
            raise ApiError(404, "unknown-transfer", "Unknown transfer")
        if t["status"] != "pending":
            raise ApiError(409, "not-pending", "Only pending transfers can be approved")
        have = stock.get((t["from"], t["item"]), 0)
        if not rules.can_transfer(have, t["qty"], items[t["item"]]["reserve"]):
            raise ApiError(409, "below-reserve", "Transfer would break the reserve")
        stock[(t["from"], t["item"])] = have - t["qty"]
        stock[(t["to"], t["item"])] = stock.get((t["to"], t["item"]), 0) + t["qty"]
        t["status"] = "approved"
        return card(t)

    @app.get("/v1/branches/{branch}/transfers")
    def inbox(branch: str):
        order = {"urgent": 0, "high": 1, "normal": 2}
        mine = [t for t in transfers.values() if t["to"] == branch]
        mine.sort(key=lambda t: (order[t["priority"]], int(t["id"][3:])))
        return {"items": [card(t) for t in mine]}

    @app.get("/v1/branches/{branch}/stock/{item_code}")
    def stock_level(branch: str, item_code: str):
        return {"branch": branch, "itemCode": item_code, "units": stock.get((branch, item_code), 0)}

    return app
