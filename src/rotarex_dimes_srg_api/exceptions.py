class RotarexError(Exception):
    """Base exception for the Rotarex API."""


class InvalidAuth(RotarexError):
    """Invalid authentication."""


class RotarexConnectionError(RotarexError):
    """Error communicating with the Rotarex API."""
