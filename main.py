from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import os

from models import SerpRequest, ScrapeRequest, GenerateArticleRequest, AutoGenerateRequest, WPPublishRequest
from services.serp import fetch_serp_data
from services.scraper import fetch_scraped_data
from services.ai import generate_ai_article
from services.wp import publish_to_wordpress

load_dotenv()

app = FastAPI(
    title=os.getenv("PROJECT_NAME", "SEO AI API"),
    description="Modüler SEO ve WP İçerik Motoru",
    version="2.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Frontend dosyalarını statik olarak sunma
app.mount("/css", StaticFiles(directory="frontend/css"), name="css")
app.mount("/js", StaticFiles(directory="frontend/js"), name="js")

@app.get("/")
async def root():
    return FileResponse("frontend/index.html")

@app.get("/wp-settings")
async def wp_settings_page():
    return FileResponse("frontend/wp-settings.html")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "architecture": "modular"}

@app.post("/api/v1/auto-create-article")
async def auto_create_article_endpoint(request: AutoGenerateRequest):
    try:
        serp_data = await fetch_serp_data(request.keyword, request.language, request.country)
        blacklist = ['youtube.com', 'facebook.com', 'instagram.com', 'pinterest.com', 'twitter.com', 'tiktok.com', 'linkedin.com', 'amazon.com']
        
        valid_competitors = [
            comp for comp in serp_data.get("competitors", [])
            if not any(blocked in comp["link"].lower() for blocked in blacklist)
        ]
        
        if not valid_competitors:
             raise HTTPException(status_code=404, detail="Google'da taranabilir uygun rakip bulunamadı.")

        top_10_competitors = valid_competitors[:10]
        urls_to_scrape = [comp["link"] for comp in top_10_competitors]

        scrape_data = await fetch_scraped_data(urls_to_scrape)
        competitor_data = [{"url": item["url"], "content": item["content"]} for item in scrape_data.get("data", [])]
        
        if not competitor_data:
             raise HTTPException(status_code=500, detail="İçerikler kazınamadı.")

        article_data = generate_ai_article(request.keyword, request.language, competitor_data)

        return {
            "status": "success",
            "process_summary": {
                "keyword": request.keyword,
                "competitors_analyzed": len(urls_to_scrape),
                "successful_scrapes": scrape_data.get("success_count", 0),
                "competitor_details": top_10_competitors 
            },
            "final_article": article_data.get("article_markdown", "")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Otomasyon Hatası: {str(e)}")

@app.post("/api/v1/publish-to-wp")
async def publish_to_wp_endpoint(request: WPPublishRequest):
    try:
        result = await publish_to_wordpress(request)
        return {
            "status": "success", 
            "message": "İçerik başarıyla WordPress'e aktarıldı.",
            "post_id": result.get("id"),
            "post_url": result.get("link")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))