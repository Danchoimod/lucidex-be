class InviteLinkError(Exception):
    """Base exception for invitation link operations."""


class InviteLinkCreationFailedError(InviteLinkError):
    """Raised when an invite link cannot be persisted."""
