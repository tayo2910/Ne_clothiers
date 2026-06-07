import os
import sys
import toml

# Load .streamlit/secrets.toml if it exists
secrets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".streamlit", "secrets.toml")
if os.path.exists(secrets_path):
    try:
        secrets = toml.load(secrets_path)
        for k, v in secrets.items():
            os.environ[k] = str(v)
    except Exception as e:
        print("Failed to load secrets.toml:", e)

# Add root folder to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from supabase_client import supabase

try:
    dummy = {
        "order_id": "NEC-2026-TEST",
        "name": "Test Column Check",
        "phone": "00000000000",
        "email": "test@example.com",
        "order_status": "Pending",
        "amount_paid": 0.0,
        "unit": "inches"
    }
    res = supabase.table("customers").insert(dummy).execute()
    print("SUCCESS! Inserted:", res.data)
    # Clean up
    if res.data:
        supabase.table("customers").delete().eq("id", res.data[0]["id"]).execute()
except Exception as e:
    print("FAILED insert:", e)
