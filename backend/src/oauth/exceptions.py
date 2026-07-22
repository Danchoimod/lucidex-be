class OAuthVerificationError(Exception):
    """Raised when an external credential cannot be safely verified."""


class OAuthEmailNotVerifiedError(OAuthVerificationError):
    """Raised when the provider has not verified the identity email."""


class OAuthConfigurationError(Exception):
    """Raised when a provider is not configured on the server."""


class UnsupportedOAuthProviderError(Exception):
    """Raised when no verifier is registered for a provider."""
