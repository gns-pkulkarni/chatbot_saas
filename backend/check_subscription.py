import sys
sys.path.append('.')

from app.utils.supabase_client import supabase
import json
from datetime import datetime

# Get recent subscriptions
result = supabase.table('saas_subscriptions')\
    .select('*, saas_plans(name)')\
    .order('created_at', desc=True)\
    .limit(5)\
    .execute()

print("Recent Subscriptions:")
print("-" * 50)
for sub in result.data:
    print(f"ID: {sub['id']}")
    print(f"Plan: {sub['saas_plans']['name'] if sub.get('saas_plans') else 'N/A'}")
    print(f"Status: {sub['status']}")
    print(f"Payment Status: {sub.get('payment_status', 'N/A')}")
    print(f"Start Date: {sub['start_date']}")
    print(f"End Date: {sub['end_date']}")
    print(f"Stripe Session ID: {sub.get('stripe_checkout_session_id', 'N/A')[:20]}..." if sub.get('stripe_checkout_session_id') else "N/A")
    print(f"Created At: {sub.get('created_at', 'N/A')}")
    print("-" * 50)
