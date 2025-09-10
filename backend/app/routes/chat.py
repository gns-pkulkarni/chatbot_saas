from fastapi import APIRouter, HTTPException, Depends
from backend.app.models.schemas import ChatInput, ChatResponse
from backend.app.services.chat_agent import get_chat_response
from backend.app.utils.supabase_client import supabase
from .auth import get_current_active_user

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("/ask", response_model=ChatResponse)
async def chat_with_knowledge_base(data: ChatInput, current_user: dict = Depends(get_current_active_user)):
    # Validate user
    if current_user["id"] != data.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to interact with this knowledge base.")

    # Get chat response
    response = get_chat_response(
        user_id=data.user_id,
        message=data.message,
        chat_history=data.chat_history or []
    )

    # print(response)

    if not response:
        raise HTTPException(status_code=500, detail="Failed to generate response.")
    return ChatResponse(response=response)

@router.post("/public/ask", response_model=ChatResponse)
async def public_chat_with_knowledge_base(data: ChatInput):
    """
    Public endpoint for embedded chatbot - no authentication required
    but validates that the user_id owns active knowledge bases and has valid subscription
    """
    print(f"Public chat request - User ID: {data.user_id}, Message: {data.message}")
    
    # First, check if user has a valid subscription
    from datetime import datetime, date
    
    # Get client profile for the user
    client_result = supabase.table("saas_client_profiles")\
        .select("id")\
        .eq("user_id", data.user_id)\
        .execute()
    
    if not client_result.data:
        print(f"No client profile found for user {data.user_id}")
        raise HTTPException(status_code=403, detail="User profile not found")
    
    client_id = client_result.data[0]["id"]
    
    # Check subscription validity
    sub_result = supabase.table("saas_subscriptions")\
        .select("end_date, status")\
        .eq("client_id", client_id)\
        .eq("status", "active")\
        .execute()
    
    if sub_result.data:
        subscription = sub_result.data[0]
        end_date = datetime.strptime(subscription["end_date"], "%Y-%m-%d").date() if isinstance(subscription["end_date"], str) else subscription["end_date"]
        
        if end_date < date.today():
            print(f"Subscription expired for user {data.user_id}. End date: {end_date}")
            raise HTTPException(status_code=403, detail="Subscription has expired. Please renew your subscription to continue using the chatbot.")
    else:
        print(f"No active subscription found for user {data.user_id}")
        raise HTTPException(status_code=403, detail="No active subscription found. Please subscribe to use the chatbot.")
    
    # Verify that the user_id exists and has active knowledge bases
    kb_result = supabase.table("saas_knowledge_base")\
        .select("id")\
        .eq("user_id", data.user_id)\
        .eq("status", "active")\
        .execute()
    
    if not kb_result.data:
        print(f"No active knowledge bases found for user {data.user_id}")
        raise HTTPException(status_code=403, detail="No active knowledge bases found for this user")
    
    print(f"Found {len(kb_result.data)} active knowledge bases")
    
    # Get chat response
    try:
        response = get_chat_response(
            user_id=data.user_id,
            message=data.message,
            chat_history=data.chat_history or []
        )
        
        print(f"Chat response generated: {response[:100]}..." if response else "No response generated")
        
        if not response:
            raise HTTPException(status_code=500, detail="Failed to generate response.")
            
        return ChatResponse(response=response)
    except Exception as e:
        print(f"Error in public chat: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")
