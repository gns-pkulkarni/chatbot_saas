import stripe
import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from backend.app.utils.supabase_client import supabase
from dotenv import load_dotenv

load_dotenv()

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

class StripeService:
    def __init__(self):
        self.stripe = stripe
        self.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:8000")
        self.price_ids = {
            "Starter": os.getenv("STRIPE_PRICE_ID_STARTER"),
            "Pro": os.getenv("STRIPE_PRICE_ID_PRO"),
            "Ultimate": os.getenv("STRIPE_PRICE_ID_ULTIMATE")
        }
    
    async def create_or_get_customer(self, user_email: str, user_id: str) -> str:
        """Create or retrieve a Stripe customer"""
        # Check if customer already exists
        client_result = supabase.table("saas_client_profiles")\
            .select("stripe_customer_id")\
            .eq("user_id", user_id)\
            .execute()
        
        if client_result.data and client_result.data[0].get("stripe_customer_id"):
            return client_result.data[0]["stripe_customer_id"]
        
        # Create new Stripe customer
        customer = stripe.Customer.create(
            email=user_email,
            metadata={"user_id": user_id}
        )
        
        # Update client profile with Stripe customer ID
        supabase.table("saas_client_profiles")\
            .update({"stripe_customer_id": customer.id})\
            .eq("user_id", user_id)\
            .execute()
        
        return customer.id
    
    async def create_checkout_session(
        self, 
        user_id: str, 
        user_email: str,
        plan_name: str,
        client_id: str
    ) -> Dict[str, Any]:
        """Create a Stripe Checkout session for subscription"""
        
        # Get or create Stripe customer
        customer_id = await self.create_or_get_customer(user_email, user_id)
        
        # Get price ID for the plan
        price_id = self.price_ids.get(plan_name)
        if not price_id:
            raise ValueError(f"Invalid plan: {plan_name}")
        
        # Get plan details from database
        plan_result = supabase.table("saas_plans")\
            .select("id, price")\
            .eq("name", plan_name)\
            .execute()
        
        if not plan_result.data:
            raise ValueError(f"Plan not found: {plan_name}")
        
        plan_id = plan_result.data[0]["id"]
        
        # Before creating a new subscription, deactivate any existing active subscriptions
        # This ensures only one subscription is active at a time
        existing_subs = supabase.table("saas_subscriptions")\
            .update({
                "status": "cancelled",
                "payment_status": "cancelled",
                "updated_at": datetime.now().isoformat()
            })\
            .eq("client_id", client_id)\
            .eq("status", "active")\
            .execute()
        
        try:
            # Create checkout session for dashboard upgrade
            # This redirects back to dashboard after payment
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=f"{self.frontend_url}/dashboard.html?payment=success&session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{self.frontend_url}/dashboard.html?payment=cancelled",
                metadata={
                    'user_id': user_id,
                    'client_id': client_id,
                    'plan_id': plan_id,
                    'plan_name': plan_name,
                    'flow_type': 'upgrade'  # Mark as upgrade flow
                },
                # Enable automatic tax calculation if needed
                # automatic_tax={'enabled': True},
            )
            
            # Create a pending subscription record
            subscription_data = {
                "client_id": client_id,
                "plan_id": plan_id,
                "start_date": datetime.now().date().isoformat(),
                "end_date": (datetime.now() + timedelta(days=30)).date().isoformat(),
                "status": "incomplete",
                "payment_status": "pending",
                "stripe_checkout_session_id": session.id,
                "amount": plan_result.data[0]["price"],
                "currency": "USD"
            }
            
            subscription_result = supabase.table("saas_subscriptions")\
                .insert(subscription_data)\
                .execute()
            
            return {
                "checkout_url": session.url,
                "session_id": session.id,
                "subscription_id": subscription_result.data[0]["id"] if subscription_result.data else None
            }
            
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")
    
    async def handle_checkout_completed(self, session: Dict[str, Any]):
        """Handle successful checkout session completion"""
        metadata = session.get("metadata", {})
        user_id = metadata.get("user_id")
        client_id = metadata.get("client_id")
        plan_id = metadata.get("plan_id")
        
        # Get Stripe subscription
        stripe_subscription = stripe.Subscription.retrieve(session["subscription"])
        
        # Update subscription in database
        subscription_update = {
            "stripe_subscription_id": stripe_subscription.id,
            "stripe_price_id": stripe_subscription["items"]["data"][0]["price"]["id"],
            "status": "active",
            "payment_status": "paid",
            "start_date": datetime.fromtimestamp(stripe_subscription.current_period_start).date().isoformat(),
            "end_date": datetime.fromtimestamp(stripe_subscription.current_period_end).date().isoformat(),
        }
        
        # Update subscription
        supabase.table("saas_subscriptions")\
            .update(subscription_update)\
            .eq("stripe_checkout_session_id", session["id"])\
            .execute()
        
        # Create payment history record
        payment_data = {
            "client_id": client_id,
            "stripe_payment_intent_id": session.get("payment_intent"),
            "amount": session["amount_total"] / 100,  # Convert from cents
            "currency": session["currency"].upper(),
            "status": "succeeded",
            "payment_method": "card",
            "description": f"Subscription payment for {metadata.get('plan_name')} plan"
        }
        
        supabase.table("saas_payment_history")\
            .insert(payment_data)\
            .execute()
    
    async def handle_subscription_updated(self, subscription: Dict[str, Any]):
        """Handle subscription updates from webhook"""
        # Update subscription dates
        subscription_update = {
            "status": subscription["status"],
            "start_date": datetime.fromtimestamp(subscription["current_period_start"]).date().isoformat(),
            "end_date": datetime.fromtimestamp(subscription["current_period_end"]).date().isoformat(),
        }
        
        supabase.table("saas_subscriptions")\
            .update(subscription_update)\
            .eq("stripe_subscription_id", subscription["id"])\
            .execute()
    
    async def cancel_subscription(self, subscription_id: str) -> bool:
        """Cancel a subscription at period end"""
        try:
            # Get subscription from database
            sub_result = supabase.table("saas_subscriptions")\
                .select("stripe_subscription_id")\
                .eq("id", subscription_id)\
                .execute()
            
            if not sub_result.data:
                return False
                
            # If it has a Stripe subscription, cancel at period end
            if sub_result.data[0].get("stripe_subscription_id"):
                stripe_sub_id = sub_result.data[0]["stripe_subscription_id"]
                
                # Cancel subscription at period end (user can still use until end_date)
                stripe.Subscription.modify(
                    stripe_sub_id,
                    cancel_at_period_end=True
                )
            
            # Update database - keep status as 'active' but mark as cancelled
            # The subscription remains active until end_date
            supabase.table("saas_subscriptions")\
                .update({
                    "status": "active",  # Keep active until end_date
                    "payment_status": "cancelled"  # Mark as cancelled for renewal
                })\
                .eq("id", subscription_id)\
                .execute()
            
            return True
            
        except Exception as e:
            print(f"Error cancelling subscription: {str(e)}")
            return False
    
    async def create_freemium_subscription(self, user_id: str, client_id: str) -> str:
        """Create a freemium subscription (no Stripe involved)"""
        # Get freemium plan
        plan_result = supabase.table("saas_plans")\
            .select("id")\
            .eq("name", "Freemium")\
            .execute()
        
        if not plan_result.data:
            raise ValueError("Freemium plan not found")
        
        plan_id = plan_result.data[0]["id"]
        
        # Before creating a new subscription, deactivate any existing active subscriptions
        # This ensures only one subscription is active at a time
        existing_subs = supabase.table("saas_subscriptions")\
            .update({
                "status": "cancelled",
                "payment_status": "cancelled",
                "updated_at": datetime.now().isoformat()
            })\
            .eq("client_id", client_id)\
            .eq("status", "active")\
            .execute()
        
        # Create subscription for 15 days
        subscription_data = {
            "client_id": client_id,
            "plan_id": plan_id,
            "start_date": datetime.now().date().isoformat(),
            "end_date": (datetime.now() + timedelta(days=15)).date().isoformat(),
            "status": "active",
            "payment_status": "paid",
            "amount": 0,
            "currency": "USD"
        }
        
        result = supabase.table("saas_subscriptions")\
            .insert(subscription_data)\
            .execute()
        
        return result.data[0]["id"] if result.data else None
    
    async def create_checkout_session_for_registration(
        self, 
        user_id: str, 
        user_email: str,
        plan_name: str,
        client_id: str
    ) -> Dict[str, Any]:
        """Create a Stripe Checkout session for registration flow"""
        
        # Get or create Stripe customer
        customer_id = await self.create_or_get_customer(user_email, user_id)
        
        # Get price ID for the plan
        price_id = self.price_ids.get(plan_name)
        if not price_id:
            raise ValueError(f"Invalid plan: {plan_name}")
        
        # Get plan details from database
        plan_result = supabase.table("saas_plans")\
            .select("id, price")\
            .eq("name", plan_name)\
            .execute()
        
        if not plan_result.data:
            raise ValueError(f"Plan not found: {plan_name}")
        
        plan_id = plan_result.data[0]["id"]
        
        try:
            # Create checkout session that redirects back to landing page after payment
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=f"{self.frontend_url}/?payment=success&registration=complete",
                cancel_url=f"{self.frontend_url}/?payment=cancelled",
                metadata={
                    'user_id': user_id,
                    'client_id': client_id,
                    'plan_id': plan_id,
                    'plan_name': plan_name,
                    'is_registration': 'true'  # Flag to identify registration flow
                },
            )
            
            # Create a pending subscription record
            subscription_data = {
                "client_id": client_id,
                "plan_id": plan_id,
                "start_date": datetime.now().date().isoformat(),
                "end_date": (datetime.now() + timedelta(days=30)).date().isoformat(),
                "status": "incomplete",
                "payment_status": "pending",
                "stripe_checkout_session_id": session.id,
                "amount": plan_result.data[0]["price"],
                "currency": "USD"
            }
            
            subscription_result = supabase.table("saas_subscriptions")\
                .insert(subscription_data)\
                .execute()
            
            return {
                "checkout_url": session.url,
                "session_id": session.id,
                "subscription_id": subscription_result.data[0]["id"] if subscription_result.data else None
            }
            
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")
