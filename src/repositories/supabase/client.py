from functools import lru_cache

from supabase import Client, create_client

from src.config import SUPABASE_ANON_KEY, SUPABASE_KEY, SUPABASE_URL


class SupabaseConfigError(Exception):
    """Raised when Supabase client settings are incomplete."""


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Return the shared Supabase client for auth and API work."""
    url = SUPABASE_URL.strip().rstrip("/")
    key = SUPABASE_ANON_KEY.strip() or SUPABASE_KEY.strip()

    if not url:
        raise SupabaseConfigError("SUPABASE_URL is missing from application config.")
    if not key:
        raise SupabaseConfigError(
            "SUPABASE_ANON_KEY or SUPABASE_KEY is missing from application config."
        )

    return create_client(url, key)
