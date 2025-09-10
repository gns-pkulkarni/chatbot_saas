from fastapi import APIRouter, Response, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
from backend.app.utils.supabase_client import supabase
from datetime import datetime, date

router = APIRouter(tags=["Embed"])

@router.get("/embed.js", response_class=PlainTextResponse)
def serve_embed_script():
    try:
        with open("frontend-embed/embed.js", "r") as file:
            js_code = file.read()
        return Response(content=js_code, media_type="application/javascript")
    except Exception as e:
        return Response(content=f"// Error loading embed.js: {e}", media_type="application/javascript")

@router.get("/check-subscription/{user_id}", response_class=JSONResponse)
def check_subscription_status(user_id: str):
    """
    Check if a user has a valid subscription for the chatbot
    """
    try:
        # Get client profile for the user
        client_result = supabase.table("saas_client_profiles")\
            .select("id")\
            .eq("user_id", user_id)\
            .execute()
        
        if not client_result.data:
            return JSONResponse(content={"valid": False, "message": "User profile not found"})
        
        client_id = client_result.data[0]["id"]
        
        # Check subscription validity with plan features
        sub_result = supabase.table("saas_subscriptions")\
            .select("end_date, status, saas_plans(name, max_sites, max_documents, can_use_voice, can_upload_docs, branding_removed)")\
            .eq("client_id", client_id)\
            .eq("status", "active")\
            .execute()
        
        if not sub_result.data:
            return JSONResponse(content={"valid": False, "message": "No active subscription found"})
        
        subscription = sub_result.data[0]
        end_date = datetime.strptime(subscription["end_date"], "%Y-%m-%d").date() if isinstance(subscription["end_date"], str) else subscription["end_date"]
        
        if end_date < date.today():
            return JSONResponse(content={
                "valid": False, 
                "message": f"Subscription expired on {end_date}",
                "expired": True,
                "end_date": str(end_date)
            })
        
        # Check if user has active knowledge bases
        kb_result = supabase.table("saas_knowledge_base")\
            .select("id")\
            .eq("user_id", user_id)\
            .eq("status", "active")\
            .execute()
        
        if not kb_result.data:
            return JSONResponse(content={
                "valid": False,
                "message": "No active knowledge bases configured",
                "has_subscription": True
            })
        
        plan_info = subscription.get("saas_plans", {})
        plan_name = plan_info.get("name", "Unknown")
        
        return JSONResponse(content={
            "valid": True,
            "active": True,
            "message": "Subscription is active",
            "end_date": str(end_date),
            "plan": {
                "name": plan_name,
                "max_sites": plan_info.get("max_sites", 1),
                "max_documents": plan_info.get("max_documents", 0),
                "can_use_voice": plan_info.get("can_use_voice", False),
                "can_upload_docs": plan_info.get("can_upload_docs", False),
                "branding_removed": plan_info.get("branding_removed", False)
            },
            "knowledge_bases": len(kb_result.data)
        })
        
    except Exception as e:
        print(f"Error checking subscription status: {str(e)}")
        return JSONResponse(
            content={"valid": False, "message": f"Error checking subscription: {str(e)}"},
            status_code=500
        )
