# LabelConflict

A product listing can say "free from milk" while its public ingredient record lists milk. LabelConflict checks that specific mismatch. It is a standalone GenLayer contract that records source-bound observations other builders can read; it is not a food-safety app.

**Current status:** deployed and exercised on GenLayer Studionet (chain 61999). Five transactions finalized with successful GenVM execution and accepted consensus. Local checks: GenVM lint and type checking passed; 43 Direct Mode tests passed with mocked web and model responses.

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

## Live Studionet record

Contract: [`0x1Dd826F32a12A1483cBf812e28738E3dacFdfA72`](https://explorer-studio.genlayer.com/address/0x1Dd826F32a12A1483cBf812e28738E3dacFdfA72). Deployer: `0x3d9E39265d74511065f88C987f898c1d02892f3e`. These are hosted-development results, not mainnet or production claims.

| Step | Explorer transaction | Finalized result |
| --- | --- | --- |
| Deploy | [`0xd95cabbf...018be016`](https://explorer-studio.genlayer.com/tx/0xd95cabbf553bd5ca332965f3a68c05e4306fc92c2112e7c8918e483a018be016) | GenVM `SUCCESS` |
| Open `3017620422003:milk` | [`0x096f6d5b...12168fb9`](https://explorer-studio.genlayer.com/tx/0x096f6d5b5f8de2f95a63a846388ea95d24f0c2dd6a2d464c0d3dcc4212168fb9) | Case opened |
| Review first case | [`0xc2c7c142...13d38e09`](https://explorer-studio.genlayer.com/tx/0xc2c7c142197d87926a3d2c03b985ed7a311e1f80e80183fee778b06513d38e09) | `CONFLICT` / `DECLARED_TAG` / `en:milk` |
| Open `5449000000996:milk` | [`0xc7f9f749...83906aec`](https://explorer-studio.genlayer.com/tx/0xc7f9f749487784653cfc4ab930a98572254f6a326a5c08db2aeabd1c83906aec) | Case opened |
| Review second case | [`0xc94ea9bc...7308cc81`](https://explorer-studio.genlayer.com/tx/0xc94ea9bc5584b247388fc19f95c800170d4cfe04b37586dda0302fb07308cc81) | `NO_CONFLICT_FOUND` / `NO_MENTION` via ingredient text |

Both `get_case` reads were checked against **Finalized** state in Studio: first case `ever_conflicted=true`, second case `ever_conflicted=false`, and each had one stored observation. The source-projection hashes from both review receipts were reproduced from the respective live Open Food Facts API records after finalization. The public data may change later.

**Source parity:** `gen_getContractCode` returned the deployed Python source. Its raw SHA-256 differs from the GitHub file because Studio stored CRLF line endings and omitted the final newline. After normalizing only those line endings, the source text matches `contracts/label_conflict.py`; this is **normalized text parity, not byte-for-byte parity**. The observed hashes and reproduction notes are in [docs/DEPLOY.md](docs/DEPLOY.md).

## Limits and attribution

Open Food Facts is a community-edited source, not a physical label or independent laboratory. A matching source record does not prove its contents are true, and a missing allergen mention does not prove the food is safe. The contract does not authenticate the caller as a manufacturer, inspect packaging, make medical claims or move funds. Exact-quote agreement is deliberately conservative and may fail to reach consensus when honest models choose different valid spans. The API has rate limits; multiple validator fetches can make a review unavailable.

[Open Food Facts API and reuse terms](https://openfoodfacts.github.io/openfoodfacts-server/api/) describe the data's ODbL/DbCL licenses and lack of accuracy guarantees. Contract code is MIT-licensed; see [LICENSE](LICENSE).
