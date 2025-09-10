from supabase import create_client, Client
from .config import SUPABASE_URL, SUPABASE_KEY

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("Connected to Supabase")
except Exception as ex:
    print(f"Error while connecting to DB - {ex.__str__()}")
