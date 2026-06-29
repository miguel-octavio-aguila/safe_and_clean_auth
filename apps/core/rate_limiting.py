from django.core.cache import cache
from django.conf import settings

_WINDOWS = {
    '1h': 3600,
    '6h': 21600,
    '1d': 86400,
}

_WINDOW_LABELS = {
    '1h': 'hora',
    '6h': '6 horas',
    '1d': 'día',
}


class RateLimitExceeded(Exception):
    def __init__(self, window, limit, scope):
        self.window = window
        self.limit = limit
        self.scope = scope
        label = _WINDOW_LABELS.get(window, window)
        scope_text = 'global' if scope == 'global' else 'por usuario'
        super().__init__(f"Límite de {limit} mensajes por {label} ({scope_text}) excedido.")


def _increment(key, window_seconds):
    count = cache.incr(key)
    if count == 1:
        cache.expire(key, window_seconds)
    return count


def enforce_rate_limit(service_name, user_id=None):
    """
    Reads SMS_RATE_LIMITS or EMAIL_RATE_LIMITS from settings and enforces them.
    First checks all windows (read phase), then increments counters (write phase).
    Raises RateLimitExceeded if any limit is exceeded — no counters are incremented.

    service_name: 'sms' or 'email'
    user_id: UUID of the user (used for per-user limits)
    """
    config = getattr(settings, f'{service_name.upper()}_RATE_LIMITS', {})
    per_user = config.get('per_user', {})
    global_limits = config.get('global', {})

    keys_to_increment = []

    for window, seconds in _WINDOWS.items():
        global_limit = global_limits.get(window)
        if global_limit is not None:
            key = f"rate:{service_name}:global:{window}"
            current = cache.get(key, 0)
            if current >= global_limit:
                raise RateLimitExceeded(window, global_limit, 'global')
            keys_to_increment.append((key, seconds))

        per_user_limit = per_user.get(window)
        if per_user_limit is not None and user_id is not None:
            key = f"rate:{service_name}:user:{user_id}:{window}"
            current = cache.get(key, 0)
            if current >= per_user_limit:
                raise RateLimitExceeded(window, per_user_limit, 'per_user')
            keys_to_increment.append((key, seconds))

    for key, seconds in keys_to_increment:
        _increment(key, seconds)
