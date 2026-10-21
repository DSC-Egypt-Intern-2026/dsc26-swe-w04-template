import json
import pathlib

from jsonschema import Draft202012Validator

SCHEMA = json.loads((pathlib.Path(__file__).parents[2] / "contracts/transfer_card.schema.json").read_text())


def test_card_matches_what_the_branch_app_expects(client):
    r = client.post("/v1/transfers", json={"itemCode": "AMOX250", "fromBranch": "heliopolis",
                                           "toBranch": "tanta", "quantity": 5})
    Draft202012Validator(SCHEMA, format_checker=Draft202012Validator.FORMAT_CHECKER).validate(r.json())
