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
      "national_id_hash": "owner.verified_national_id_hash"
    }
  ]
}
```

When the Owner has no verified hash, only the claimed branch is used.
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
actual model fields `major`, `classification`, and a masked `phone`.

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
  "national_id_hash": "owner.verified_national_id_hash"
}
```

It sets `owner_id`, `status: claimed`, `claimed_at`, and
`claim_method: manual`. A retry by the same Owner returns HTTP 200 with
`already_claimed: true`; a credential claimed by another Owner returns 409.
Soft-deleted credentials are reported as not found and are never mutated.

## Internal eKYC persistence guard

The internal verified-hash service is not exposed as a public route. It only
matches active, non-deleted, unclaimed credentials. Re-verifying the same hash
is idempotent; attempting to replace an existing verified hash with a
different hash returns 409 and requires a separate identity-change flow.

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

Dedicated credential error codes are not registered yet. The API therefore
uses the existing global fallback convention:

| HTTP | Current code | Meaning |
|---:|---|---|
| 401 | `UNAUTHORIZED` or `HTTP_401` | Invalid authentication |
| 403 | `HTTP_403` | Owner/eKYC/hash authorization failed |
| 404 | `HTTP_404` | Credential missing or outside owner scope |
| 409 | `HTTP_409` | Claimed by another Owner or not claimable |
| 422 | `VALIDATION_ERROR` | Invalid path/query/body |

Pending Error Code Registration:

- `EKYC_NOT_VERIFIED`
- `CREDENTIAL_NOT_MATCHED`
- `CREDENTIAL_NOT_FOUND`
- `CREDENTIAL_ALREADY_CLAIMED`
- `MATCH_NOT_CLAIMABLE`
