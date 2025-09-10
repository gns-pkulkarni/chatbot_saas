from app.utils.supabase_client import supabase
from datetime import datetime

# Get the most recent subscription
result = supabase.table('saas_subscriptions')\
    .select('*, saas_plans(name, price)')\
    .order('created_at', desc=True)\
    .limit(1)\
    .execute()

if result.data:
    sub = result.data[0]
    print("Latest Subscription Details:")
    print("-" * 50)
    print(f"Subscription ID: {sub['id']}")
    print(f"Plan: {sub['saas_plans']['name'] if sub.get('saas_plans') else 'N/A'}")
    print(f"Price: ${sub['saas_plans']['price'] if sub.get('saas_plans') else 'N/A'}")
    print(f"Status: {sub['status']}")
    print(f"Payment Status: {sub.get('payment_status', 'N/A')}")
    print(f"Start Date: {sub['start_date']}")
    print(f"End Date: {sub['end_date']}")
    print(f"Stripe Subscription ID: {sub.get('stripe_subscription_id', 'N/A')}")
    print(f"Stripe Session ID: {sub.get('stripe_checkout_session_id', 'N/A')[:30]}..." if sub.get('stripe_checkout_session_id') else "N/A")
    print(f"Created At: {sub.get('created_at', 'N/A')}")
    
    # Check if it's active
    if sub['status'] == 'active':
        end_date = datetime.fromisoformat(sub['end_date'])
        today = datetime.now().date()
        days_left = (end_date.date() - today).days if hasattr(end_date, 'date') else (end_date - today).days
        print(f"\n✅ Subscription is ACTIVE with {days_left} days remaining")
    elif sub['status'] == 'incomplete':
        print(f"\n⏳ Subscription is INCOMPLETE (waiting for payment confirmation)")
    else:
        print(f"\n❌ Subscription status: {sub['status']}")
else:
    print("No subscriptions found")
