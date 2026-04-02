from pydantic import BaseModel, EmailStr
from typing import List, Dict, Any, Optional
from datetime import datetime

# --- EXISTING MODELS (Untouched) ---

class SerpRequest(BaseModel):
    keyword: str
    language: str = "tr"
    country: str = "tr"

class ScrapeRequest(BaseModel):
    urls: List[str]

class GenerateArticleRequest(BaseModel):
    keyword: str
    language: str = "tr"
    competitor_data: List[Dict[str, Any]] 

class AutoGenerateRequest(BaseModel):
    keyword: str
    language: str = "tr"
    country: str = "tr"

class WPPublishRequest(BaseModel):
    wp_url: Optional[str] = None
    wp_username: Optional[str] = None
    wp_app_password: Optional[str] = None
    title: str
    content_markdown: str
    status: str = "draft"
# --- NEW: User Auth & Registration Models ---

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    role: str
    is_active: bool
    balance: float
    created_at: datetime

    class Config:
        from_attributes = True

# --- NEW: Tenant WP Settings Models ---

class WPSettingsCreate(BaseModel):
    website_name: Optional[str] = "Default Site"
    wp_url: str
    wp_username: str
    wp_app_password: str

class WPSettingsResponse(BaseModel):
    id: int
    website_name: Optional[str]
    wp_url: str
    wp_username: str
    
    class Config:
        from_attributes = True