from fastapi import APIRouter, HTTPException, Depends, Request, Header
from typing import Optional, Dict, Any
from backend.app.services.stripe_service import StripeService
from backend.app.utils.supabase_client import supabase
from .auth import get_current_active_user
import stripe
import os
import json

router = APIRouter(prefix="/payments", tags=["Payments"])
stripe_service = StripeService()

from pydantic import BaseModel

class CheckoutRequest(BaseModel):
    plan_name: str

@router.post("/create-checkout-session")
async def create_checkout_session(
    request: CheckoutRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """Create a Stripe checkout session for subscription"""
    try:
        user_id = current_user["id"]
        user_email = current_user["email"]
        
        # Get client profile
        client_result = supabase.table("saas_client_profiles")\
            .select("id")\
            .eq("user_id", user_id)\
            .execute()
        
        if not client_result.data:
            raise HTTPException(status_code=404, detail="Client profile not found")
        
        client_id = client_result.data[0]["id"]
        
        # Handle Freemium plan separately
        if request.plan_name == "Freemium":
            subscription_id = await stripe_service.create_freemium_subscription(user_id, client_id)
            return {
                "success": True,
                "subscription_id": subscription_id,
                "message": "Freemium subscription created successfully"
            }
        
        # Create Stripe checkout session for paid plans
        result = await stripe_service.create_checkout_session(
            user_id=user_id,
            user_email=user_email,
            plan_name=request.plan_name,
            client_id=client_id
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cancel-subscription")
async def cancel_subscription(
    subscription_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Cancel a subscription"""
    # Verify subscription belongs to user
    sub_result = supabase.table("saas_subscriptions")\
        .select("client_id")\
        .eq("id", subscription_id)\
        .execute()
    
    if not sub_result.data:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    # Verify ownership
    client_result = supabase.table("saas_client_profiles")\
        .select("user_id")\
        .eq("id", sub_result.data[0]["client_id"])\
        .execute()
    
    if not client_result.data or client_result.data[0]["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this subscription")
    
    success = await stripe_service.cancel_subscription(subscription_id)
    
    if success:
        return {"message": "Subscription cancelled successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to cancel subscription")

@router.get("/subscription-status")
async def get_subscription_status(current_user: dict = Depends(get_current_active_user)):
    """Get current subscription status"""
    # Get client profile
    client_result = supabase.table("saas_client_profiles")\
        .select("id")\
        .eq("user_id", current_user["id"])\
        .execute()
    
    if not client_result.data:
        return {"has_subscription": False}
    
    client_id = client_result.data[0]["id"]
    
    # Get active subscription
    sub_result = supabase.table("saas_subscriptions")\
        .select("*, saas_plans(name, max_messages, max_sites, max_documents)")\
        .eq("client_id", client_id)\
        .eq("status", "active")\
        .execute()
    
    if not sub_result.data:
        return {"has_subscription": False}
    
    subscription = sub_result.data[0]
    plan = subscription["saas_plans"]
    
    return {
        "has_subscription": True,
        "subscription": {
            "id": subscription["id"],
            "plan_name": plan["name"],
            "status": subscription["status"],
            "start_date": subscription["start_date"],
            "end_date": subscription["end_date"],
            "features": {
                "max_messages": plan["max_messages"],
                "max_sites": plan["max_sites"],
                "max_documents": plan["max_documents"]
            }
        }
    }


# In Stripe localhost won't work.
# So everytime we want to test payments,
# we need to make localhost url and port public by
# using ngrok. And then update that url to stripe webhook endpoints e.g
# https://83717d1636e3.ngrok-free.app/payments/stripe-webhook
@router.post("/stripe-webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    """Handle Stripe webhooks"""
    payload = await request.body()
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    
    # For testing without webhook secret
    if not webhook_secret or webhook_secret == "whsec_YOUR_WEBHOOK_SECRET_HERE":
        # Parse the payload directly for testing
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid payload")
    else:
        # Verify webhook signature in production
        try:
            event = stripe.Webhook.construct_event(
                payload, stripe_signature, webhook_secret
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Store webhook event (check if already exists first)
    stripe_event_id = event.get("id", "test_event")
    
    # Check if webhook event already exists
    existing_webhook = supabase.table("saas_stripe_webhooks")\
        .select("processed")\
        .eq("stripe_event_id", stripe_event_id)\
        .execute()
    
    if existing_webhook.data:
        # If already processed, return success
        if existing_webhook.data[0]["processed"]:
            return {"status": "already_processed"}
    else:
        # Store new webhook event
        webhook_data = {
            "stripe_event_id": stripe_event_id,
            "event_type": event["type"],
            "payload": event,
            "processed": False
        }
        
        supabase.table("saas_stripe_webhooks")\
            .insert(webhook_data)\
            .execute()
    
    # Handle different event types
    try:
        if event["type"] == "checkout.session.completed":
            await stripe_service.handle_checkout_completed(event["data"]["object"])
        
        elif event["type"] == "customer.subscription.updated":
            await stripe_service.handle_subscription_updated(event["data"]["object"])
        
        elif event["type"] == "customer.subscription.deleted":
            # Handle subscription cancellation
            subscription = event["data"]["object"]
            supabase.table("saas_subscriptions")\
                .update({"status": "cancelled"})\
                .eq("stripe_subscription_id", subscription["id"])\
                .execute()
        
        elif event["type"] == "invoice.payment_succeeded":
            # Handle successful payment
            invoice = event["data"]["object"]
            # Create payment history record
            if invoice.get("subscription"):
                # Get subscription details
                sub_result = supabase.table("saas_subscriptions")\
                    .select("client_id")\
                    .eq("stripe_subscription_id", invoice["subscription"])\
                    .execute()
                
                if sub_result.data:
                    payment_data = {
                        "client_id": sub_result.data[0]["client_id"],
                        "stripe_invoice_id": invoice["id"],
                        "amount": invoice["amount_paid"] / 100,
                        "currency": invoice["currency"].upper(),
                        "status": "succeeded",
                        "payment_method": "card",
                        "description": "Subscription renewal payment"
                    }
                    
                    supabase.table("saas_payment_history")\
                        .insert(payment_data)\
                        .execute()
        
        # Mark webhook as processed
        supabase.table("saas_stripe_webhooks")\
            .update({"processed": True})\
            .eq("stripe_event_id", stripe_event_id)\
            .execute()
        
        return {"status": "success"}
        
    except Exception as e:
        # Log error
        supabase.table("saas_stripe_webhooks")\
            .update({
                "processed": False,
                "error_message": str(e)
            })\
            .eq("stripe_event_id", stripe_event_id)\
            .execute()
        
        raise HTTPException(status_code=500, detail=str(e))
