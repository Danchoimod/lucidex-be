COMMON_ERROR_RESPONSES = {
    401: {"description": "UNAUTHORIZED or INVALID_OWNER_ACCOUNT."},
    403: {
        "description": "OWNER_ACCESS_REQUIRED or OWNER_INACTIVE."
    },
    422: {"description": "VALIDATION_ERROR."},
    500: {"description": "INTERNAL_SERVER_ERROR."},
}

DETAIL_ERROR_RESPONSES = {
    **COMMON_ERROR_RESPONSES,
    404: {"description": "CREDENTIAL_NOT_FOUND."},
}

CLAIM_ERROR_RESPONSES = {
    **DETAIL_ERROR_RESPONSES,
    403: {
        "description": (
            "OWNER_ACCESS_REQUIRED, OWNER_INACTIVE, EKYC_NOT_VERIFIED, "
            "or CREDENTIAL_NOT_MATCHED."
        )
    },
    409: {"description": ("CREDENTIAL_ALREADY_CLAIMED or MATCH_NOT_CLAIMABLE.")},
}
