from pydantic import BaseModel
from typing import List, Dict, Any

class SerpRequest(BaseModel):
    keyword: str
    language: str = "tr"
    country: str = "tr"

class ScrapeRequest(BaseModel):
    urls: List[str]

class GenerateArticleRequest(BaseModel):
    keyword: str
    language: str = "tr"
    # Artık sadece metin değil, [{"url": "...", "content": "..."}] formatında veri alacak
    competitor_data: List[Dict[str, Any]] 

class AutoGenerateRequest(BaseModel):
    keyword: str
    language: str = "tr"
    country: str = "tr"