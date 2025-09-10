from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from backend.app.utils.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from backend.app.utils.supabase_client import supabase
import uuid
import re

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
        return email
    except JWTError:
        return None

async def register_user(email: str, password: str, full_name: str, plan_id: str = None) -> dict:
    try:
        # Check if user exists
        existing = supabase.table("saas_users").select("id").eq("email", email).execute()
        if existing.data:
            raise ValueError("User with this email already exists")
        
        # Create user
        user_id = str(uuid.uuid4())
        hashed_password = get_password_hash(password)
        
        user_data = {
            "id": user_id,
            "email": email,
            "password_hash": hashed_password,
            "full_name": full_name
        }
        
        result = supabase.table("saas_users").insert(user_data).execute()
        
        # Also create client profile
        client_data = {
            "user_id": user_id,
            "email": email,
            "full_name": full_name
        }
        client_result = supabase.table("saas_client_profiles").insert(client_data).execute()
        client_id = client_result.data[0]["id"]
        
        # Create subscription based on selected plan or default to Freemium
        # Handle empty string or None for plan_id
        # UUID pattern for validation
        uuid_pattern = re.compile(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', re.IGNORECASE)
        
        # Check if plan_id is valid UUID
        if plan_id and isinstance(plan_id, str) and uuid_pattern.match(plan_id):
            # Valid UUID provided, use it
            pass
        else:
            # Invalid or no plan_id, default to Freemium
            plan_result = supabase.table("saas_plans").select("id").eq("name", "Freemium").execute()
            if plan_result.data:
                plan_id = plan_result.data[0]["id"]
            else:
                # If Freemium plan doesn't exist, skip subscription creation
                plan_id = None
        
        requires_payment = False
        plan_name = "Freemium"
        stripe_checkout_url = None
        
        if plan_id:
            # Verify the plan exists
            plan_check = supabase.table("saas_plans").select("*").eq("id", plan_id).execute()
            if plan_check.data:
                plan = plan_check.data[0]
                plan_name = plan.get("name", "Freemium")
                today = datetime.utcnow().date()
                
                # Check if this is a paid plan that requires Stripe payment
                # All plans except Freemium and Starter require payment
                if plan["price"] > 0 and plan_name not in ["Freemium", "Starter"]:
                    # Paid plan - mark for Stripe redirect, don't create subscription yet
                    requires_payment = True
                    # We'll return the user data with requires_payment flag
                    # The frontend will need to handle the Stripe checkout
                else:
                    # Free plan or Starter - create subscription immediately
                    if plan["price"] == 0:  # Free plan
                        end_date = today + timedelta(days=14)  # 14-day trial
                    else:
                        end_date = today + timedelta(days=30)  # 30 days for Starter
                    
                    subscription_data = {
                        "client_id": client_id,
                        "plan_id": plan_id,
                        "start_date": today.isoformat(),
                        "end_date": end_date.isoformat(),
                        "status": "active"
                    }
                    supabase.table("saas_subscriptions").insert(subscription_data).execute()
        
        # Return complete user data
        user_response = {
            "id": user_id,
            "email": email,
            "full_name": full_name,
            "created_at": result.data[0].get("created_at", datetime.utcnow().isoformat()),
            "requires_payment": requires_payment,
            "plan_name": plan_name,
            "client_id": client_id
        }
        return user_response
    except Exception as e:
        # Log the error for debugging
        print(f"Registration error in auth_service: {str(e)}")
        raise

async def authenticate_user(email: str, password: str):
    result = supabase.table("saas_users").select("*").eq("email", email).execute()
    if not result.data:
        return None
    
    user = result.data[0]
    if not verify_password(password, user["password_hash"]):
        return None
    
    return user

async def get_current_user(email: str):
    result = supabase.table("saas_users").select("*").eq("email", email).execute()
    if result.data:
        return result.data[0]
    return None
