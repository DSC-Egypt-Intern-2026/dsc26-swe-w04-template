from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from nour_transfers.app import create_app

FIXED_NOW = datetime(2026, 11, 3, 9, 30, tzinfo=UTC)


@pytest.fixture
def client():
    app = create_app(
        stock={("heliopolis", "MET500"): 40, ("tanta", "MET500"): 2,
               ("heliopolis", "AMOX250"): 30, ("tanta", "AMOX250"): 25},
        items={"MET500": {"chronic": True, "reserve": 10},    # metformin 500 mg
               "AMOX250": {"chronic": False, "reserve": 5}},  # amoxicillin 250 mg
        sales={("tanta", "MET500"): 1.0, ("tanta", "AMOX250"): 5.0},
        now=lambda: FIXED_NOW,
    )
    return TestClient(app)
