# Deploy and evidence checklist

Current state: **NOT DEPLOYED**. This checklist is for the builder who controls the development wallet. Never send a private key, seed phrase or authenticated RPC URL to a reviewer, chat, or public repository.

## 1. Check the exact source first

From the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python scripts/prepare_test_sdk.py
.venv/bin/genvm-lint check contracts/label_conflict.py
.venv/bin/python -m pytest tests -q
sha256sum contracts/label_conflict.py
```

Record the hash and the test count you actually observed. Do not edit the contract after hashing without re-running lint and tests. GenVM runner hash is pinned in line one; keep it there.

## 2. Deploy on Studionet with a burner wallet

1. Open https://studio.genlayer.com/ and select **Studionet**, chain ID **61999**. Use its built-in faucet if the wallet needs test GEN.
2. Create a new Intelligent Contract and paste the **entire unchanged** `contracts/label_conflict.py` file. No constructor arguments.
3. Deploy; wait for a finalized transaction and successful GenVM execution. Save the contract address and deploy transaction link from https://explorer-studio.genlayer.com/.
4. Check that the contract schema exposes `open_case`, `review`, `get_case`, `get_observation`, `has_conflict`, and `count`. If deployment fails, do not substitute a different contract while still citing this source hash.

Studionet state is temporary. Re-verify the address before submission. Studio-dev (chain 61997) uses a separate RC SDK/network definition: do not copy its RPC into the Studionet preset.

## 3. Real-source cases

Use the Studio method controls or a network-compatible client. Each `open_case` and `review` is a separate wallet-signed write. Wait for finalization and successful execution **before** reading durable state or sending the next write. Input codes are **strings** (retain leading zeroes).

### Possible positive control (product data can change)

```text
open_case("3017620422003", "milk")
review("3017620422003:milk")
get_case("3017620422003:milk")
get_observation("3017620422003:milk", 0)
has_conflict("3017620422003:milk")
```

A past OFF read declared `en:milk` for this GTIN. If the live record still does, the review should report `CONFLICT` / `DECLARED_TAG`. If not, record the real result; do not edit a screenshot or invent a favorable verdict.

### Negative control (never a safety certificate)

```text
open_case("5449000000996", "milk")
review("5449000000996:milk")
get_case("5449000000996:milk")
get_observation("5449000000996:milk", 0)
```

The record's ingredient language or content may change. `NO_CONFLICT_FOUND` means only no detected mention in this specific public record; `UNRESOLVED` is also a legitimate result. Neither means safe for someone with an allergy.

The missing/oversize/lying-leader and history cases are covered locally by mocked direct tests. Do not label those cases "verified onchain" unless you actually run them onchain and save their real transaction IDs.

## 4. Evidence to preserve

Fill in only from observed transactions:

| Item | Value |
| --- | --- |
| Network / chain ID | Studionet / 61999 (confirm) |
| Local source SHA-256 (2026-10-16) | `0dbab93fbf59a00c71a6eec27e092d49c4b80a6588f40c801dec7140996f9c79` |
| Contract address | Not deployed |
| Deployment transaction | Not deployed |
| Case 1 open / review transactions | Not run |
| Case 1 final status / source hash | Not read |
| Case 2 open / review transactions | Not run |
| Case 2 final status / source hash | Not read |
| Local lint / test log (2026-10-16) | `genvm-lint check`: passed; `genvm-lint typecheck`: passed; `pytest`: 43 passed. Direct Mode only. |

For each transaction, check network, FINALIZED status, successful GenVM execution and consensus result. A transaction can finalize with an execution error; never treat `FINALIZED` alone as success. Save an Explorer link rather than only a screenshot. For the v0.6 RC SDK, use its `isSuccessful` receipt helper and matching fee policy; do not apply RC assumptions blindly to stable Studionet.

## 5. Submit as Intelligent Contracts

Upload the standalone source, tests, requirements, docs and license in a **public** repository. Use the contract address, repository URL and actual transactions in the Portal form. No frontend is required for this category. The submission text should state plainly: this is a warning about contradictions in community-edited data, **not** proof of food safety or manufacturer identity. Don't claim results that tests or Explorer do not show.
