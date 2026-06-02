"""Common exceptions for CryptoTracker."""


class CryptoTrackerError(Exception):
    """Base exception for CryptoTracker."""
    pass


class ValidationError(CryptoTrackerError):
    """Validation error."""
    pass


class CurrencyNotFoundError(CryptoTrackerError):
    """Currency not found in the system."""
    pass


class WatchlistNotFoundError(CryptoTrackerError):
    """Watchlist not found."""
    pass


class WatchlistItemNotFoundError(CryptoTrackerError):
    """Watchlist item not found."""
    pass


class DuplicateWatchlistError(CryptoTrackerError):
    """Watchlist with this name already exists."""
    pass


class DuplicateWatchlistItemError(CryptoTrackerError):
    """Currency pair already exists in watchlist."""
    pass


class ExternalAPIError(CryptoTrackerError):
    """Error when calling external API."""
    pass


class FrankfurterUnavailableError(ExternalAPIError):
    """Frankfurter API is unavailable."""
    pass


class CoinGeckoUnavailableError(ExternalAPIError):
    """CoinGecko API is unavailable."""
    pass


class RateLimitExceededError(ExternalAPIError):
    """Rate limit exceeded for external API."""
    pass


class DatabaseError(CryptoTrackerError):
    """Database error."""
    pass


class ServerUnavailableError(CryptoTrackerError):
    """Server is not running or unreachable."""
    pass
