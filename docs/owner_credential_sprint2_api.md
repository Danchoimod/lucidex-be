# Owner Credential API — Sprint 2

## Status

Implementation complete for the three scoped APIs, but not production-ready until:

- Credential Import writes `national_id_hash` with the approved HMAC helper.
- Existing credential hashes are verified or affected data is re-imported.
- An end-to-end import → eKYC → list/detail → claim test passes.

## Authentication and security scope

All endpoints require an authenticated, active, non-deleted Owner. `owner_id`
is taken from the validated access token/session and is never accepted from
the request. Inactive, locked, or soft-deleted Owners receive HTTP 403 before
credential data is queried.

The shared read scope is:

```json
{
  "deleted_at": null,
  "$or": [
    {"owner_id": "current_owner_id", "status": "claimed"},
    {
      "owner_id": null,
      "status": "unclaimed",
      "national_id_hash": "owner_ekyc_identities.national_id_hash"
    }
  ]
}
```

When the Owner has no verified eKYC identity, only the claimed branch is used.
`national_id_hash` is never returned by the API. Because the soft-delete
condition is part of the database scope before the list facet, deleted
credentials are excluded from items, summary counts, and pagination totals.

## GET `/api/v1/owner/credentials`

Query parameters:

| Parameter | Default | Notes |
|---|---:|---|
| `page` | `1` | Minimum 1 |
| `limit` | `20` | Range 1–100 |
| `student_id` | — | Exact match |
| `graduation_year` | — | Exact match |
| `status` | — | `claimed` or `unclaimed` |
| `search` | — | Escaped literal search over allowlisted fields |
| `sort` | `_id:desc` | Allowlisted `field:asc` or `field:desc` |

`summary` is calculated over the full authorized and filtered set before
pagination. `created_at` is not part of the response because the current
Credential/import contract has no canonical timestamp source. The default
`_id:desc` order provides deterministic insertion order without backfilling
legacy data.

`class_id` is not returned because no canonical source exists in the current
Credential model/import contract.

## GET `/api/v1/owner/credentials/{credential_id}`

The credential ID and security scope are applied in one query. A missing or
out-of-scope credential returns the same not-found response. Detail exposes the
actual model fields `major`, `classification`, a masked `phone`, and a nested
public `issuer` profile containing `id`, `name`, `address`, `contact_email`,
and `contact_phone`. Registration-only fields such as tax code, legal
representative, documents, and account credentials are not exposed.

## POST `/api/v1/owner/claim/credentials/{credential_id}`

Request body:

```json
{}
```

The happy path uses one conditional `find_one_and_update`:

```json
{
  "_id": "credential_id",
  "deleted_at": null,
  "owner_id": null,
  "status": "unclaimed",
  "national_id_hash": "owner_ekyc_identities.national_id_hash"
}
```

It sets `owner_id`, `status: claimed`, `claimed_at`, and
`claim_method: manual`. A retry by the same Owner returns HTTP 200 with
`already_claimed: true`; a credential claimed by another Owner returns 409.
Soft-deleted credentials are reported as not found and are never mutated.

## POST `/api/v1/owner/ekyc/verify`

Request body:

```json
{
  "national_id": "079203001234"
}
```

The endpoint validates the national-ID format, computes its normalized HMAC,
and persists the verified identity on the active Owner. It does not query or
mutate Credential records. It is not provider, liveness, face-matching, or
image-based eKYC.

`owner_ekyc_identities` is the single source of truth for the national-ID
hash. It stores `owner_id`, `national_id_hash`, `status`, and `verified_at`.
The Owner document stores no eKYC state. Verification removes the legacy
`ekyc_verified`, `ekyc_verified_at`, and `verified_national_id_hash` fields.

Both `owner_id` and `national_id_hash` are unique in the eKYC identity
collection. Re-verifying the same Owner/hash is idempotent, a different hash
for the same Owner returns 403, and a hash already linked to another Owner
returns 409. Credential list/detail/claim load the verified hash from the eKYC
identity repository.

The response never includes the submitted national ID or any national-ID hash.

## Hash contract

1. Trim the input.
2. Remove whitespace and `-`.
3. Require exactly 12 ASCII digits.
4. Compute `HMAC-SHA256(NATIONAL_ID_HASH_SECRET, normalized_id)`.
5. Store lowercase hexadecimal output only.

The application has a single environment source in `src.config.Settings`.
`src.credential.config` reads that settings object and does not read the
environment independently. Missing secret fails settings validation only when
`ENV=production`; in other environments it fails only if a hash operation is
attempted without an injected/configured secret.

## Current error contract

All business error codes are defined as `AppError` subclasses in the module
`exceptions.py` files. FastAPI request parsing continues to use the global
`VALIDATION_ERROR` convention.

| HTTP | Code | Meaning |
|---:|---|---|
| 401 | `UNAUTHORIZED` | Invalid or expired access token |
| 401 | `INVALID_OWNER_ACCOUNT` | Authenticated Owner has no valid ID |
| 403 | `OWNER_ACCESS_REQUIRED` | Actor is not an Owner |
| 403 | `OWNER_INACTIVE` | Owner is inactive, locked, or deleted |
| 403 | `EKYC_NOT_VERIFIED` | Claim requires verified eKYC |
| 403 | `CREDENTIAL_NOT_MATCHED` | Credential hash differs from Owner identity |
| 403 | `IDENTITY_CHANGE_NOT_ALLOWED` | Attempt to replace verified identity |
| 404 | `OWNER_NOT_FOUND` | Owner disappeared during persistence |
| 404 | `CREDENTIAL_NOT_FOUND` | Credential missing or outside Owner scope |
| 409 | `CREDENTIAL_ALREADY_CLAIMED` | Another Owner already claimed it |
| 409 | `IDENTITY_ALREADY_LINKED` | National ID is linked to another Owner |
| 409 | `MATCH_NOT_CLAIMABLE` | Matching credential is not claimable |
| 422 | `VALIDATION_ERROR` | Invalid request path/query/body |
| 422 | `INVALID_NATIONAL_ID_FORMAT` | Invalid normalized national ID |
| 500 | `EKYC_PERSISTENCE_FAILED` | Conditional persistence failed unexpectedly |
| 500 | `EKYC_TIMESTAMP_UNAVAILABLE` | Verified state has no timestamp |
| 500 | `NATIONAL_ID_HASH_SECRET_NOT_CONFIGURED` | HMAC secret is missing |
