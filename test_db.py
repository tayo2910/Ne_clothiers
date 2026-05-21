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

# Add root folder to sys.path so we can import from database.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from database import get_customers
    customers = get_customers()
    print("SUCCESS! Customers fetched:", len(customers))
    if customers:
        print("First customer keys:", list(customers[0].keys()))
        print("First customer sample data:", customers[0])
    else:
        print("No customers found in database.")
except Exception as e:
    print("FAILED:", e)
