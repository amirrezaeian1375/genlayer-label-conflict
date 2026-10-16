# LabelConflict

A product listing can say "free from milk" while its public ingredient record lists milk. LabelConflict checks that specific mismatch. It is a standalone GenLayer contract that records source-bound observations other builders can read; it is not a food-safety app.

**Current status:** source linted and type-checked; 43 Direct Mode tests passed with mocked web and model responses. **Not deployed. No live GenLayer consensus result yet.**

## One question, five outcomes

Anyone can open a case for a valid GTIN and one allergen code. `review` constructs a fixed Open Food Facts v3 URL; the caller cannot choose a different evidence site or supply a verdict. The contract compares a caller-declared allergen-exclusion claim with the product's public record.

| Status | What it means |
| --- | --- |
| `CONFLICT` | The source names the allergen in its declared tags or an ingredient statement. A sticky conflict flag is set. |
| `TRACE` | The source mentions possible cross-contact; not the same as an ingredient contradiction. |
| `NO_CONFLICT_FOUND` | No mention was detected in the available record. **Not a safety certificate.** |
| `UNRESOLVED` | The record or the ingredient statement cannot support a decision. |
| `SOURCE_UNAVAILABLE` | The API could not be reached or gave an unusable response. |

The flag never clears automatically. A later edit of the community record creates a new observation instead of erasing the previous one. Applications can use `has_conflict` to **request human review**, not to approve a product as safe when it returns false.

Supported codes: `milk`, `egg`, `peanut`, `tree_nut`, `soy`, `sesame`. Input barcodes must be valid GTIN-8, -12, -13 or -14 values. The opener's address is recorded for attribution only; it does not prove manufacturer identity or ownership of the label claim.

## Why consensus matters here

The leader fetches the product record inside GenVM. An exact allergen or trace tag can decide without an LLM. Otherwise the model classifies the bounded ingredient text and must return an exact quote for a positive or trace finding. Validators independently fetch and classify the record. The custom validator compares the decision, basis, reason, product identity, SHA-256 of the bounded source projection **and** the exact quote. It does more than check JSON formatting.

Only the accepted result enters state. Fetch failure, malformed data or model ambiguity cannot become a favorable absence claim. A repeated observation with the same decision and source projection is idempotent. `get_observation` exposes the source URL, hash, reason and quote; the full source body is not stored onchain.

Public reads: `get_case(case_id)`, `get_observation(case_id, index)`, `has_conflict(case_id)`, `count()`. Writes: `open_case(gtin, allergen)` and permissionless `review(case_id)`. Case IDs have the form `gtin:allergen`. Full state design and failure modes: [docs/DESIGN.md](docs/DESIGN.md).

## Reproduce locally

Install Python 3.12+ and, from the repository root, run these commands in order:

1. `python3 -m venv .venv`
2. `.venv/bin/python -m pip install -r requirements-dev.txt`
3. `.venv/bin/python scripts/prepare_test_sdk.py`
4. `.venv/bin/genvm-lint check contracts/label_conflict.py`
5. `.venv/bin/python -m pytest tests -q`

On Windows, activate the virtual environment and use its `python` and `genvm-lint` commands. The preparation script works around an upstream release-asset naming mismatch in `genlayer-test==0.29.2`; it changes no contract source. Direct Mode tests mock the web and LLM. They cover bad input, contradictions, traces, outages, malformed data, quote validation, repeated reviews and validators rejecting forged or divergent results. **They are not a distributed-network test.**

## Live evidence still needed

The exact contract file is `contracts/label_conflict.py`. Deploy it on GenLayer Studionet, wait for successful finalization, then run both a positive and a negative/control case against the live source. Record the address, source hash and separate transaction links. See [docs/DEPLOY.md](docs/DEPLOY.md) for the exact calls and an evidence checklist. Do not report local mocks as onchain results.

Example GTINs to *re-check at demo time*: `3017620422003` with `milk` has historically had a milk tag; `5449000000996` with `milk` can exercise the ingredient-text path. The underlying records can change.

## Limits and attribution

Open Food Facts is a community-edited source, not a physical label or independent laboratory. A matching source record does not prove its contents are true, and a missing allergen mention does not prove the food is safe. The contract does not authenticate the caller as a manufacturer, inspect packaging, make medical claims or move funds. Exact-quote agreement is deliberately conservative and may fail to reach consensus when honest models choose different valid spans. The API has rate limits; multiple validator fetches can make a review unavailable.

[Open Food Facts API and reuse terms](https://openfoodfacts.github.io/openfoodfacts-server/api/) describe the data's ODbL/DbCL licenses and lack of accuracy guarantees. Contract code is MIT-licensed; see [LICENSE](LICENSE).
