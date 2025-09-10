import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.utils.supabase_client import supabase

result = supabase.table("saas_plans").select("*").execute()
for plan in result.data:
    print(f"Plan: {plan['name']}, Price: {plan['price']}")
