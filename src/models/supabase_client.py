import os
from functools import lru_cache

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()


class SupabaseConfigError(Exception):
    """Raised when Supabase client settings are incomplete."""


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Return the shared Supabase client for auth and API work."""
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    key = (
        os.getenv("SUPABASE_ANON_KEY", "").strip()
        or os.getenv("SUPABASE_KEY", "").strip()
    )

    if not url:
        raise SupabaseConfigError("SUPABASE_URL is missing from .env.")
    if not key:
        raise SupabaseConfigError("SUPABASE_ANON_KEY or SUPABASE_KEY is missing from .env.")

    return create_client(url, key)
