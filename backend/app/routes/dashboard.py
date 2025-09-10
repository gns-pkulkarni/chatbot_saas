from fastapi import APIRouter, HTTPException, Depends
from backend.app.utils.supabase_client import supabase
from .auth import get_current_active_user
from typing import List

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/data")
async def get_dashboard_data(current_user: dict = Depends(get_current_active_user)):
    user_id = current_user["id"]
    
    # Get user's knowledge bases
    kb_result = supabase.table("saas_knowledge_base")\
        .select("*")\
        .eq("user_id", user_id)\
        .execute()
    
    # Get client profile to get the correct client_id
    client_result = supabase.table("saas_client_profiles")\
        .select("id")\
        .eq("user_id", user_id)\
        .execute()
    
    # Get user's plan details
    plan_details = {}
    if client_result.data:
        client_id = client_result.data[0]["id"]
        sub_result = supabase.table("saas_subscriptions")\
            .select("*, saas_plans(*)")\
            .eq("client_id", client_id)\
            .eq("status", "active")\
            .execute()
    
        if sub_result.data:
            plan = sub_result.data[0]
            selected_plan = plan["saas_plans"]
            plan_details = {
                "name": selected_plan["name"],
                "max_messages": selected_plan["max_messages"],
                "max_sites": selected_plan["max_sites"],
                "max_documents": selected_plan["max_documents"],
                "can_upload_docs": selected_plan["can_upload_docs"],
                "end_date": plan["end_date"]
            }
    
    # Generate embed code
    embed_code = f'<script src="http://localhost:8000/embed.js?id={user_id}"></script>'
    
    # Prepare user info
    user_info = {
        "name": current_user.get("full_name", "User"),
        "email": current_user.get("email", ""),
        "subscription": plan_details.get("name", "Free"),
        "created_at": current_user.get("created_at")
    }
    
    return {
        "user": current_user,
        "user_info": user_info,
        "knowledge_bases": kb_result.data or [],
        "embed_code": embed_code,
        "plan_details": plan_details
    }

@router.get("/knowledge-bases")
async def list_knowledge_bases(current_user: dict = Depends(get_current_active_user)):
    result = supabase.table("saas_knowledge_base")\
        .select("*")\
        .eq("user_id", current_user["id"])\
        .order("created_at", desc=True)\
        .execute()
    
    return result.data or []

@router.delete("/knowledge-base/{kb_id}")
async def delete_knowledge_base(kb_id: str, current_user: dict = Depends(get_current_active_user)):
    # Check if KB belongs to user
    check_result = supabase.table("saas_knowledge_base")\
        .select("id")\
        .eq("id", kb_id)\
        .eq("user_id", current_user["id"])\
        .execute()
    
    if not check_result.data:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    
    # Delete knowledge base (cascades to vectors)
    supabase.table("saas_knowledge_base").delete().eq("id", kb_id).execute()
    
    return {"message": "Knowledge base deleted successfully"}
