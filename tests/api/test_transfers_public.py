def test_request_transfer_returns_a_pending_card(client):
    r = client.post("/v1/transfers", json={"itemCode": "MET500", "fromBranch": "heliopolis",
                                           "toBranch": "tanta", "quantity": 20})
    assert r.status_code == 201
    assert r.json()["status"] == "pending"
