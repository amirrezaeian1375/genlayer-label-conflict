# Design notes - LabelConflict

Status: local GenVM checks and Direct Mode tests passed. A Studionet deployment and two live review paths are documented in [DEPLOY.md](DEPLOY.md). These are hosted-development results, not production behavior or food-safety evidence.

## Problem

A seller or listing operator may assert that a GTIN-identified product is free from a specific allergen. Public product records may contain an ingredient declaration or allergen/trace tags that conflict with the operator's assertion. A single operator should not be able to publish an onchain *contradiction observation* by choosing its own evidence page or a model answer.

This primitive **does not** certify that food is safe, that a label is legally compliant, that the asserted claim appears on the physical package, or that an Open Food Facts entry is accurate. It only assesses whether the caller-declared exclusion is in tension with a specific community-edited public record. `NO_CONFLICT_FOUND` is not a safety certificate. Its safe downstream use is *flagging possible listing errors for human review*; the absence of a flag must not authorize consumption.

## Evidence and authority

- The caller supplies only a valid GTIN-8/12/13/14 and one of a closed list of allergens. It does **not** supply a URL, model result, source body or oracle address.
- The contract constructs the current Open Food Facts v3 product URL and sends a named User-Agent. Leaders and validators fetch it independently inside a GenLayer non-deterministic block. The API is the only external source; validators are independent readers, **not** independent data publishers. The data is community-edited and can be wrong or out of date.
- The data projection is limited to product identity, ingredient text, declared allergen tags and declared trace tags. It is bounded and SHA-256 hashed; dynamic metadata is excluded.
- If a tag explicitly lists the target allergen, the result follows without an LLM. Otherwise the LLM reads the bounded ingredient text and returns only a four-way label plus an exact supporting quote (for positive or trace classifications).
- An LLM answer is not accepted unless the label is allowed, the quote is a literal span of the independently retrieved text, and validators independently agree on identity, evidence digest, decision, basis, reason **and the exact quote**. Different valid quotes can force disagreement; this is a deliberate conservative trade-off. A network failure or missing product cannot become evidence of absence.

## Case state

`open_case(gtin, allergen)` creates a deterministic case ID unique within the deployed contract. `review(case_id)` is permissionless and records a bounded observation once the proposed result is accepted by consensus. A repeated review of the same outcome, reason and projected source hash is idempotent. Individual observations and reads are bounded; the number of genuine source revisions is not hard-capped. Once an explicit contradiction is recorded, `has_conflict(case_id)` remains true even if a later community edit removes the contradictory text. Consumers must perform a separate, human-controlled review to resolve it; the contract deliberately has no unilateral "clear" action.

Outcome vocabulary:

- `CONFLICT`: explicit declared tag or source-grounded ingredient mention conflicts with the caller's exclusion claim.
- `TRACE`: source mentions possible cross-contact; needs review, not a proven ingredient contradiction.
- `NO_CONFLICT_FOUND`: no target allergen detected in the available source data. **Not proof of absence or safety.**
- `UNRESOLVED`: product record or required data is missing/malformed/too large, or the model cannot decide.
- `SOURCE_UNAVAILABLE`: the API fetch failed or returned a temporary error.

No escrow, owner privilege, food-safety approval, browser frontend, or automatic product publication.

## Why this is not a generic claim checker

This is a *closed, source-bound data-consistency primitive* for one product and allergen at a time. It applies a fixed taxonomy mapping, identity and GTIN checks, explicit cross-contact treatment, a sticky audit flag, append-only deduped observations, literal evidence quotes, strict availability semantics, and a narrow, documented consumer use. A free-form claim checker would lack these rules. This project is distinct from product-recall adjudication (whether an official recall includes a lot) and from a clinical safety assessment.

## Threats and limits to test

- An adversary supplies an invalid or mismatched barcode, a fake endpoint, or a fabricated leader verdict.
- Decision-relevant product fields change between leader/validator reads; the projection-digest mismatch prevents agreement. Changes to ignored volatile metadata alone do not.
- Prompt injection appears inside ingredients. Treat source text as data; require a literal quote for positive decisions.
- A fetch fails, a product is missing, declared tags are absent, ingredient data is incomplete, an LLM returns a boolean/string instead of an allowed label, or the source is oversize.
- Repeated calls attempt to overwrite older observations or erase a prior conflict.
- Misinterpretation of `NO_CONFLICT_FOUND` as physical safety: **strictly outside scope**. OFF source is not independently validated against packaging.
- Hosted Studio state may reset; deployments need both Explorer evidence and exact source identity, not a bare address.
