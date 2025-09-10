from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
import uuid

# User schemas
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    plan_id: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# Knowledge Base schemas
class KnowledgeBaseCreate(BaseModel):
    name: str
    type: str  # 'url' or 'document'
    source_url: Optional[str] = None

class KnowledgeBaseResponse(BaseModel):
    id: str
    user_id: str
    name: str
    type: str
    source_url: Optional[str] = None
    document_name: Optional[str] = None
    status: str
    created_at: datetime

# Chat schemas
class ChatInput(BaseModel):
    user_id: str
    knowledge_base_id: Optional[str] = None  # Made optional since chat_agent doesn't use it
    message: str
    chat_history: Optional[List[List[str]]] = []

class ChatResponse(BaseModel):
    response: str

# Dashboard schemas
class DashboardData(BaseModel):
    user: UserResponse
    knowledge_bases: List[KnowledgeBaseResponse]
    embed_code: str
    plan_details: dict
