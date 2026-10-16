# Studionet deployment record

Observed on 2026-10-16. This is a hosted development-network experiment, not mainnet or a food-safety certification.

- Network: GenLayer Studionet, chain ID `61999`.
- Deployer: `0x3d9E39265d74511065f88C987f898c1d02892f3e`.
- [Contract: `0x1Dd826F32a12A1483cBf812e28738E3dacFdfA72`](https://explorer-studio.genlayer.com/address/0x1Dd826F32a12A1483cBf812e28738E3dacFdfA72).
- Runtime dependency: `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6` (pinned in source line one).

## Actual transaction sequence

All five transactions below reached `FINALIZED` with GenVM `SUCCESS` and accepted consensus. Studio used Normal (Full Consensus) mode. The two review receipts show an initial committee of five and zero leader rotations.

| Action | Explorer transaction | Observed result |
| --- | --- | --- |
| Deploy | [`0xd95cabbf...018be016`](https://explorer-studio.genlayer.com/tx/0xd95cabbf553bd5ca332965f3a68c05e4306fc92c2112e7c8918e483a018be016) | Contract created; six public methods present. |
| `open_case("3017620422003", "milk")` | [`0x096f6d5b...12168fb9`](https://explorer-studio.genlayer.com/tx/0x096f6d5b5f8de2f95a63a846388ea95d24f0c2dd6a2d464c0d3dcc4212168fb9) | Case `3017620422003:milk` created. |
| `review("3017620422003:milk")` | [`0xc2c7c142...13d38e09`](https://explorer-studio.genlayer.com/tx/0xc2c7c142197d87926a3d2c03b985ed7a311e1f80e80183fee778b06513d38e09) | `CONFLICT`; basis `TAG`, reason `DECLARED_TAG`, quote `en:milk`. |
| `open_case("5449000000996", "milk")` | [`0xc7f9f749...83906aec`](https://explorer-studio.genlayer.com/tx/0xc7f9f749487784653cfc4ab930a98572254f6a326a5c08db2aeabd1c83906aec) | Case `5449000000996:milk` created. |
| `review("5449000000996:milk")` | [`0xc94ea9bc...7308cc81`](https://explorer-studio.genlayer.com/tx/0xc94ea9bc5584b247388fc19f95c800170d4cfe04b37586dda0302fb07308cc81) | `NO_CONFLICT_FOUND`; basis `TEXT`, reason `NO_MENTION`. |

## Finalized state readback

Studio's Read Methods were set to **Finalized**, not Accepted:

- `get_case("3017620422003:milk")`: `last_status=CONFLICT`, `ever_conflicted=true`, `reviews=1`. `get_observation("3017620422003:milk", 0)` showed the fixed Open Food Facts v3 URL, `DECLARED_TAG`, quote `en:milk` and projection SHA-256 `50adff919fa0536ed14e705fcc25607ad0771b033c54e8a600ac8b76fa30cb26`.
- `get_case("5449000000996:milk")`: `last_status=NO_CONFLICT_FOUND`, `ever_conflicted=false`, `reviews=1`, `last_reason=NO_MENTION`, projection SHA-256 `2ac910293e14ba437de53a2b0d27b75c6f0daaacdfc345654f547c7fee1c118a`.

Both hashes were independently recomputed after finalization from the corresponding Open Food Facts v3 product responses. This verifies what the API returned at those times; it does **not** verify physical packaging or certify an absence of allergens. The source can change after review.

## Deployed source parity

- Repository file: `contracts/label_conflict.py`; 13,225 bytes (LF, final newline); SHA-256 `0dbab93fbf59a00c71a6eec27e092d49c4b80a6588f40c801dec7140996f9c79`.
- Deployed source returned by `gen_getContractCode`: 13,525 bytes (CRLF, no final newline); SHA-256 `077802b11935c2791e0c8f6f4a666b7f7e5fc7aac5b0b29cb6347f0452017528`.
- **Raw byte equality: false. Normalized text equality: true.** Replacing deployed CRLF with LF and adding its missing final LF yields the repository file exactly. There are no code-token differences.

To reproduce, call the Studionet RPC `https://studio.genlayer.com/api` with JSON-RPC method `gen_getContractCode` and `params` containing the contract address **as a string**, then base64-decode `result`. Compare the decoded bytes with the repository file after the two line-ending adjustments above. Do not claim byte-for-byte source equality.

## Reproduce locally

From the repository root, use Python 3.12+:

1. `python3 -m venv .venv`
2. `.venv/bin/python -m pip install -r requirements-dev.txt`
3. `.venv/bin/python scripts/prepare_test_sdk.py`
4. `.venv/bin/genvm-lint check contracts/label_conflict.py`
5. `.venv/bin/python -m pytest tests -q`

Observed local result: GenVM lint/semantic validation passed, type checking passed, and **43 Direct Mode tests passed**. Direct Mode mocks web and LLM calls; it is separate from the five live consensus transactions above. Do not run `open_case` again with the same two case IDs on this deployed instance: duplicates are rejected. For read-only reproduction, import the deployed address into Studio, select **Finalized** state, and call `get_case` and `get_observation`.

This contract is a product-listing data-consistency warning, not proof of a manufacturer's label claim, food safety, or medical suitability. Public data and hosted Studionet state may change or reset.
