import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

def _get_secret(key: str) -> str:
    """Read from env first, then Streamlit secrets."""
    val = os.getenv(key, "").strip()
    if not val:
        try:
            import streamlit as st
            val = str(st.secrets.get(key, "")).strip()
        except Exception:
            pass
    return val

SUPABASE_URL = _get_secret("SUPABASE_URL")
SUPABASE_KEY = _get_secret("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env or Streamlit secrets.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
