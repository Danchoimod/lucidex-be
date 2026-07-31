VERIFY_ERROR_RESPONSES = {
    401: {"description": "UNAUTHORIZED: invalid or expired access token."},
    403: {
        "description": (
            "OWNER_ACCESS_REQUIRED, OWNER_INACTIVE, IDENTITY_CHANGE_NOT_ALLOWED, "
            "or INVALID_VNPT_ACCESS_TOKEN."
        )
    },
    404: {"description": "OWNER_NOT_FOUND."},
    409: {"description": "IDENTITY_ALREADY_LINKED."},
    422: {"description": "VALIDATION_ERROR or INVALID_NATIONAL_ID_FORMAT."},
    500: {
        "description": (
            "EKYC_PERSISTENCE_FAILED, EKYC_TIMESTAMP_UNAVAILABLE, "
            "NATIONAL_ID_HASH_SECRET_NOT_CONFIGURED, or INTERNAL_SERVER_ERROR."
        )
    },
}
