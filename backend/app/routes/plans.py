from fastapi import APIRouter
from backend.app.utils.supabase_client import supabase

router = APIRouter(prefix="/clients", tags=["Plans"])

@router.get("/plans")
def list_plans():
    result = supabase.table("saas_plans").select("id, name, price, description, max_messages, max_sites, max_documents, can_upload_docs, can_use_voice, branding_removed, chat_history_days, api_access").execute()
    return result.data
