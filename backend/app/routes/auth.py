from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from backend.app.models.schemas import UserRegister, UserLogin, UserResponse, Token
from backend.app.services.auth_service import (
    register_user, authenticate_user, create_access_token, verify_token, get_current_user
)
from datetime import timedelta
from backend.app.utils.config import ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_active_user(token: str = Depends(oauth2_scheme)):
    email = verify_token(token)
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await get_current_user(email)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/register")
async def register(user_data: UserRegister):
    try:
        print(f"Registration request - Email: {user_data.email}, Full Name: {user_data.full_name}, Plan ID: {user_data.plan_id}")
        user = await register_user(
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
            plan_id=user_data.plan_id
        )
        
        # If payment is required, we need to create a Stripe checkout session
        checkout_url = None
        if user.get("requires_payment", False):
            from backend.app.services.stripe_service import StripeService
            stripe_service = StripeService()
            
            try:
                # Create checkout session for registration
                checkout_result = await stripe_service.create_checkout_session_for_registration(
                    user_id=user["id"],
                    user_email=user["email"],
                    plan_name=user.get("plan_name"),
                    client_id=user.get("client_id")
                )
                checkout_url = checkout_result.get("checkout_url")
            except Exception as stripe_error:
                print(f"Failed to create Stripe checkout: {str(stripe_error)}")
                # Continue with registration but note the error
        
        # Return user info with plan details
        return {
            "user": {
                "id": user["id"],
                "email": user["email"],
                "full_name": user["full_name"],
                "created_at": user["created_at"]
            },
            "requires_payment": user.get("requires_payment", False),
            "plan_name": user.get("plan_name", "Freemium"),
            "client_id": user.get("client_id"),
            "checkout_url": checkout_url  # Include Stripe checkout URL if payment required
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Registration error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)  # username is email
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["email"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: dict = Depends(get_current_active_user)):
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        created_at=current_user["created_at"]
    )
