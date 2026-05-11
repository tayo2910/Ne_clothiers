from supabase_client import supabase


def add_customer(data: dict) -> dict:
    """Insert a new customer record into Supabase."""
    return supabase.table("customers").insert(data).execute()


def get_customers() -> list:
    """Fetch all customer records from Supabase."""
    return supabase.table("customers").select("*").execute().data


def update_customer(record_id: int, data: dict) -> dict:
    """Update an existing customer record by id."""
    return supabase.table("customers").update(data).eq("id", record_id).execute()


def delete_customer(record_id: int) -> dict:
    """Delete a customer record by id."""
    return supabase.table("customers").delete().eq("id", record_id).execute()
