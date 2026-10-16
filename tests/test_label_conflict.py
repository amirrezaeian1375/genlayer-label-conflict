"""Direct-mode tests execute the actual GenLayer contract with mocked web/LLM calls."""

import json

import pytest


NUTELLA = "3017620422003"
COLA = "5449000000996"
WEB_PATTERN = r"world\.openfoodfacts\.org/api/v3/product/\d+\.json"
LLM_PATTERN = r"Classify ONLY the ingredient statement"
CONTRACT = "contracts/label_conflict.py"


def product(code=NUTELLA, ingredients="Milk, hazelnuts.", allergens=None, traces=None):
    return {
        "code": code,
        "status": "success",
        "result": {"id": "product_found"},
        "errors": [],
        "warnings": [],
        "product": {
            "code": code,
            "ingredients_text": ingredients,
            "allergens_tags": [] if allergens is None else allergens,
            "traces_tags": [] if traces is None else traces,
        },
    }


def web(vm, payload, status=200):
    vm.mock_web(WEB_PATTERN, {"status": status, "body": json.dumps(payload)})


def llm(vm, label, quote=""):
    vm.mock_llm(LLM_PATTERN, json.dumps({"label": label, "quote": quote}))


def case(contract, key):
    return json.loads(contract.get_case(key))


def observation(contract, key, index=0):
    return json.loads(contract.get_observation(key, index))


def test_open_case_is_deterministic_and_attributed(direct_deploy, direct_alice, direct_vm):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    key = contract.open_case(NUTELLA, "milk")
    assert key == NUTELLA + ":milk"
    assert contract.count() == 1
    assert case(contract, key)["opened_by"].lower() == "0x" + direct_alice.hex()
    assert not contract.has_conflict(key)
    assert contract.get_observation(key, 0) == ""
    with direct_vm.expect_revert("Case already exists"):
        contract.open_case(NUTELLA, "milk")
    assert contract.count() == 1


@pytest.mark.parametrize("code", ["", "123", "3017620422004", "A017620422003", "３０１７６２０４２２００３"])
def test_bad_gtin_rejected(direct_deploy, direct_vm, code):
    contract = direct_deploy(CONTRACT)
    with direct_vm.expect_revert("Expected a valid GTIN"):
        contract.open_case(code, "milk")
    assert contract.count() == 0


@pytest.mark.parametrize("allergen", ["wheat", "MILK", "", "nuts", None])
def test_bad_allergen_rejected(direct_deploy, direct_vm, allergen):
    contract = direct_deploy(CONTRACT)
    with direct_vm.expect_revert("Unsupported allergen code"):
        contract.open_case(NUTELLA, allergen)


def test_fixed_source_and_declared_tag_contradiction(direct_deploy, direct_vm):
    contract = direct_deploy(CONTRACT)
    key = contract.open_case(NUTELLA, "milk")
    web(direct_vm, product(allergens=["en:milk", "en:nuts"]))
    direct_vm.strict_mocks = True
    assert contract.review(key) == "CONFLICT"
    row = observation(contract, key)
    assert row["basis"] == "TAG" and row["reason"] == "DECLARED_TAG"
    assert row["quote"] == "en:milk"
    assert row["source_url"].startswith(
        "https://world.openfoodfacts.org/api/v3/product/3017620422003.json?fields="
    )
    assert len(row["source_hash"]) == 64
    assert case(contract, key)["reviews"] == 1
    assert contract.has_conflict(key)
    assert direct_vm.run_validator() is True


def test_trace_is_not_a_proven_ingredient_conflict(direct_deploy, direct_vm):
    contract = direct_deploy(CONTRACT)
    key = contract.open_case(NUTELLA, "milk")
    web(direct_vm, product(ingredients="Chocolate.", traces=["en:milk"]))
    assert contract.review(key) == "TRACE"
    assert observation(contract, key)["reason"] == "DECLARED_TRACE"
    assert not contract.has_conflict(key)
    assert direct_vm.run_validator() is True


def test_text_mention_requires_verbatim_quote_and_consensus(direct_deploy, direct_vm):
    contract = direct_deploy(CONTRACT)
    key = contract.open_case(NUTELLA, "milk")
    web(direct_vm, product(ingredients="Sugar, whey powder, cocoa."))
    llm(direct_vm, "PRESENT", "whey powder")
    direct_vm.strict_mocks = True
    assert contract.review(key) == "CONFLICT"
    assert direct_vm.run_validator() is True
    row = observation(contract, key)
    assert row["quote"] == "whey powder"
    assert row["reason"] == "INGREDIENT_MENTION"
    assert contract.has_conflict(key)


def test_precautionary_ingredient_text_is_trace_only(direct_deploy, direct_vm):
    contract = direct_deploy(CONTRACT)
    key = contract.open_case(COLA, "milk")
    web(direct_vm, product(code=COLA, ingredients="Water. May contain milk."))
    llm(direct_vm, "TRACE", "May contain milk")
    assert contract.review(key) == "TRACE"
    assert observation(contract, key)["basis"] == "TEXT"
    assert not contract.has_conflict(key)


def test_not_found_is_not_a_food_safety_certificate(direct_deploy, direct_vm):
    contract = direct_deploy(CONTRACT)
    key = contract.open_case(COLA, "milk")
    web(direct_vm, product(code=COLA, ingredients="Water, sugar, carbon dioxide."))
    llm(direct_vm, "NOT_FOUND")
    assert contract.review(key) == "NO_CONFLICT_FOUND"
    assert observation(contract, key)["quote"] == ""
    assert not contract.has_conflict(key)  # Only a sticky positive flag, not a safety claim.
    assert direct_vm.run_validator() is True


@pytest.mark.parametrize("label", ["UNKNOWN", "NOT_FOUND"])
def test_unavailable_or_ambiguous_ingredients_are_never_conflict(direct_deploy, direct_vm, label):
    contract = direct_deploy(CONTRACT)
    key = contract.open_case(COLA, "milk")
    if label == "UNKNOWN":
        web(direct_vm, product(code=COLA, ingredients="Untranslated incomplete text."))
        llm(direct_vm, label)
        assert contract.review(key) == "UNRESOLVED"
        assert observation(contract, key)["reason"] == "AMBIGUOUS_TEXT"
    else:
        web(direct_vm, product(code=COLA, ingredients=""))
        assert contract.review(key) == "UNRESOLVED"
        assert observation(contract, key)["reason"] == "NO_INGREDIENTS"
    assert not contract.has_conflict(key)


@pytest.mark.parametrize("bad_result", [
    {"label": "PRESENT", "quote": "not in source"},
    {"label": "PRESENT", "quote": ""},
    {"label": "TRACE", "quote": "milk" * 60},
    {"label": "NO_CONFLICT_FOUND", "quote": ""},
    {"label": "NOT_FOUND", "quote": "milk"},
    {"label": True, "quote": "milk"},
    ["PRESENT", "milk"],
])
def test_malformed_model_result_cannot_write_state(direct_deploy, direct_vm, bad_result):
    contract = direct_deploy(CONTRACT)
    key = contract.open_case(NUTELLA, "milk")
    web(direct_vm, product(ingredients="Contains milk."))
    direct_vm.mock_llm(LLM_PATTERN, json.dumps(bad_result))
    with direct_vm.expect_revert():
        contract.review(key)
    assert case(contract, key)["reviews"] == 0
    assert not contract.has_conflict(key)


@pytest.mark.parametrize("payload,status,expected_status,reason", [
    ({"code": NUTELLA, "status": "failure", "result": {"id": "product_not_found"}},
     404, "UNRESOLVED", "NO_RECORD"),
    ({"code": NUTELLA, "status": "failure", "result": {"id": "product_not_found"}},
     200, "UNRESOLVED", "NO_RECORD"),
    ({"error": "route missing"}, 404, "SOURCE_UNAVAILABLE", "HTTP_ERROR"),
    ({"error": "rate limited"}, 503, "SOURCE_UNAVAILABLE", "HTTP_ERROR"),
    ({**product(), "warnings": [{"id": "incomplete"}]},
     200, "UNRESOLVED", "BAD_ENVELOPE"),
    (product(code=COLA), 200, "UNRESOLVED", "IDENTITY_MISMATCH"),
    (product(ingredients="", allergens=[], traces=[]), 200, "UNRESOLVED", "NO_INGREDIENTS"),
    (product(ingredients=1), 200, "UNRESOLVED", "BAD_FIELDS"),
])
def test_nondecisions_stay_nondecisions(direct_deploy, direct_vm,
                                         payload, status, expected_status, reason):
    contract = direct_deploy(CONTRACT)
    key = contract.open_case(NUTELLA, "milk")
    web(direct_vm, payload, status)
    assert contract.review(key) == expected_status
    assert observation(contract, key)["reason"] == reason
    assert not contract.has_conflict(key)
    assert direct_vm.run_validator() is True


def test_body_limit_prevents_truncation_to_false_negative(direct_deploy, direct_vm):
    contract = direct_deploy(CONTRACT)
    key = contract.open_case(NUTELLA, "milk")
    direct_vm.mock_web(WEB_PATTERN, {"status": 200, "body": "a" * 17000})
    assert contract.review(key) == "UNRESOLVED"
    assert observation(contract, key)["reason"] == "SOURCE_TOO_LARGE"


def test_identical_projection_is_idempotent_despite_volatile_metadata(direct_deploy, direct_vm):
    contract = direct_deploy(CONTRACT)
    key = contract.open_case(NUTELLA, "milk")
    first = product(allergens=["en:milk"])
    first["last_modified_t"] = 1
    web(direct_vm, first)
    contract.review(key)
    direct_vm.clear_mocks()
    second = product(allergens=["en:milk"])
    second["last_modified_t"] = 9999999
    web(direct_vm, second)
    assert contract.review(key) == "CONFLICT"
    assert case(contract, key)["reviews"] == 1
    assert contract.get_observation(key, 1) == ""


def test_later_edit_does_not_erase_prior_contradiction(direct_deploy, direct_vm):
    contract = direct_deploy(CONTRACT)
    key = contract.open_case(NUTELLA, "milk")
    web(direct_vm, product(allergens=["en:milk"]))
    assert contract.review(key) == "CONFLICT"
    old_digest = observation(contract, key)["source_hash"]
    direct_vm.clear_mocks()
    web(direct_vm, product(ingredients="Sugar, cocoa.", allergens=[]))
    llm(direct_vm, "NOT_FOUND")
    assert contract.review(key) == "NO_CONFLICT_FOUND"
    state = case(contract, key)
    assert state["reviews"] == 2
    assert state["ever_conflicted"] is True
    assert state["last_status"] == "NO_CONFLICT_FOUND"
    assert observation(contract, key, 1)["source_hash"] != old_digest
    assert contract.has_conflict(key) is True
    direct_vm.clear_mocks()
    web(direct_vm, {"error": "upstream down"}, 503)
    assert contract.review(key) == "SOURCE_UNAVAILABLE"
    assert contract.has_conflict(key) is True
    assert case(contract, key)["reviews"] == 3


def test_dissenting_validator_rejects_changed_source(direct_deploy, direct_vm):
    contract = direct_deploy(CONTRACT)
    key = contract.open_case(NUTELLA, "milk")
    web(direct_vm, product(allergens=["en:milk"]))
    contract.review(key)
    direct_vm.clear_mocks()
    web(direct_vm, product(ingredients="Sugar.", allergens=[]))
    llm(direct_vm, "NOT_FOUND")
    assert direct_vm.run_validator() is False
    assert case(contract, key)["reviews"] == 1


def test_dissenting_validator_rejects_forged_hash_or_quote(direct_deploy, direct_vm):
    contract = direct_deploy(CONTRACT)
    key = contract.open_case(NUTELLA, "milk")
    web(direct_vm, product(ingredients="Contains milk."))
    llm(direct_vm, "PRESENT", "milk")
    contract.review(key)
    row = observation(contract, key)
    result = {
        "gtin": NUTELLA,
        "allergen": "milk",
        "status": "CONFLICT",
        "basis": "TEXT",
        "reason": "INGREDIENT_MENTION",
        "source_hash": row["source_hash"],
        "quote": "milk",
    }
    assert direct_vm.run_validator(leader_result=result) is True
    assert direct_vm.run_validator(leader_result={**result, "quote": "false quote"}) is False
    assert direct_vm.run_validator(leader_result={**result, "source_hash": "0" * 64}) is False
    assert direct_vm.run_validator(leader_result={**result, "status": "NO_CONFLICT_FOUND"}) is False
    assert direct_vm.run_validator(leader_result={"status": "CONFLICT"}) is False
    assert direct_vm.run_validator(leader_error=RuntimeError("model crashed")) is False


def test_unknown_case_and_missing_observation(direct_deploy, direct_vm):
    contract = direct_deploy(CONTRACT)
    assert contract.get_case("missing") == ""
    assert contract.get_observation("missing", 0) == ""
    assert contract.has_conflict("missing") is False
    with direct_vm.expect_revert("Unknown case"):
        contract.review("missing")


def test_body_missing_and_invalid_v3_envelope_fail_closed(direct_deploy, direct_vm):
    contract = direct_deploy(CONTRACT)
    key = contract.open_case(NUTELLA, "milk")
    direct_vm.mock_web(WEB_PATTERN, {"status": 200, "body": None})
    assert contract.review(key) == "SOURCE_UNAVAILABLE"
    assert observation(contract, key)["reason"] == "EMPTY_BODY"
    direct_vm.clear_mocks()
    malformed = product(allergens=["en:milk"])
    del malformed["result"]
    web(direct_vm, malformed)
    assert contract.review(key) == "UNRESOLVED"
    assert observation(contract, key, 1)["reason"] == "BAD_ENVELOPE"
    assert not contract.has_conflict(key)


def test_validator_disagrees_on_same_bytes_but_different_meaning(direct_deploy, direct_vm):
    contract = direct_deploy(CONTRACT)
    key = contract.open_case(NUTELLA, "milk")
    payload = product(ingredients="Contains casein.")
    web(direct_vm, payload)
    llm(direct_vm, "PRESENT", "casein")
    assert contract.review(key) == "CONFLICT"
    direct_vm.clear_mocks()
    web(direct_vm, payload)
    llm(direct_vm, "UNKNOWN")
    assert direct_vm.run_validator() is False
    assert case(contract, key)["reviews"] == 1


def test_validator_rejects_different_quote_even_same_label(direct_deploy, direct_vm):
    contract = direct_deploy(CONTRACT)
    key = contract.open_case(NUTELLA, "milk")
    payload = product(ingredients="Whey powder and skim milk.")
    web(direct_vm, payload)
    llm(direct_vm, "PRESENT", "Whey powder")
    contract.review(key)
    direct_vm.clear_mocks()
    web(direct_vm, payload)
    llm(direct_vm, "PRESENT", "skim milk")
    assert direct_vm.run_validator() is False


def test_multiple_valid_gtin_lengths(direct_deploy):
    contract = direct_deploy(CONTRACT)
    for code in ("96385074", "036000291452", NUTELLA, "00012345678905"):
        contract.open_case(code, "milk")
    assert contract.count() == 4
