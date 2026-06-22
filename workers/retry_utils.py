import random


def compute_backoff(retries: int, base: int = 20, cap: int = 600) -> int:
    """Exponential backoff in seconds (with jitter) for a Celery retry countdown.

    retries=0 -> ~20-25s, retries=1 -> ~40-45s, retries=2 -> ~80-85s, ... capped at `cap`.
    """
    delay = min(cap, base * (2 ** retries))
    return delay + random.randint(0, 5)
