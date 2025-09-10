from backend.app.utils.supabase_client import supabase
from typing import List
import datetime

def save_chat_history(user_id: str, message: str, response: str, input_tokens=0, output_tokens=0, total_cost_usd=0.00):
    try:
        supabase.table("saas_chat_history").insert({
            "user_id": user_id,
            "knowledge_base_id": None,
            "message": message,
            "response": response,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_cost_usd": total_cost_usd,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }).execute()
    except Exception as e:
        print(f"Error saving chat history: {e}")


def get_chat_history(user_id: str, knowledge_base_id: str) -> List[dict]:
    try:
        result = supabase.table("saas_chat_history")\
            .select("message, response, timestamp")\
            .eq("user_id", user_id)\
            .eq("knowledge_base_id", knowledge_base_id)\
            .order("timestamp", desc=False)\
            .execute()
        return result.data or []
    except Exception as e:
        print(f"Error fetching chat history: {e}")
        return []
