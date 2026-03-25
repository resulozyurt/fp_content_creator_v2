from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import os

# Modülleri içe aktarıyoruz
from models import SerpRequest, ScrapeRequest, GenerateArticleRequest, AutoGenerateRequest
from services.serp import fetch_serp_data
from services.scraper import fetch_scraped_data
from services.ai import generate_ai_article

load_dotenv()

app = FastAPI(
    title=os.getenv("PROJECT_NAME", "SEO AI API"),
    description="Modüler Frase.io Klonu",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return FileResponse("frontend/index.html")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "architecture": "modular"}

@app.post("/api/v1/analyze-serp")
async def analyze_serp_endpoint(request: SerpRequest):
    try:
        return await fetch_serp_data(request.keyword, request.language, request.country)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/scrape-competitors")
async def scrape_competitors_endpoint(request: ScrapeRequest):
    return await fetch_scraped_data(request.urls)

@app.post("/api/v1/generate-article")
async def generate_article_endpoint(request: GenerateArticleRequest):
    try:
        return generate_ai_article(request.keyword, request.language, request.competitor_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Üretim Hatası: {str(e)}")

@app.post("/api/v1/auto-create-article")
async def auto_create_article_endpoint(request: AutoGenerateRequest):
    try:
        # 1. SERP
        serp_data = await fetch_serp_data(request.keyword, request.language, request.country)
        urls_to_scrape = [comp["link"] for comp in serp_data.get("competitors", [])]
        
        if not urls_to_scrape:
             raise HTTPException(status_code=404, detail="Google'da rakip bulunamadı.")

        # 2. KAZIMA
        top_5_urls = urls_to_scrape[:5]
        scrape_data = await fetch_scraped_data(top_5_urls)
        
        # URL ve İçeriği eşleştirerek AI servisine gönderilecek yeni formatı hazırlıyoruz
        competitor_data = [{"url": item["url"], "content": item["content"]} for item in scrape_data.get("data", [])]
        
        if not competitor_data:
             raise HTTPException(status_code=500, detail="İçerikler kazınamadı.")

        # 3. AI ÜRETİMİ
        article_data = generate_ai_article(request.keyword, request.language, competitor_data)

        return {
            "status": "success",
            "process_summary": {
                "keyword": request.keyword,
                "competitors_analyzed": len(top_5_urls),
                "successful_scrapes": scrape_data.get("success_count", 0)
            },
            "final_article": article_data.get("article_markdown", "")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Otomasyon Hatası: {str(e)}")