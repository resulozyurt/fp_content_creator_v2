from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import os
import json

from models import SerpRequest, ScrapeRequest, GenerateArticleRequest, AutoGenerateRequest, WPPublishRequest
from services.serp import fetch_serp_data
from services.scraper import fetch_scraped_data
from services.ai import generate_ai_article
from services.wp import publish_to_wordpress
from services.db import get_db, ArticleHistory
from services.image import process_images_in_article # GÖRSEL SERVİSİ İÇE AKTARILDI

load_dotenv()

app = FastAPI(
    title=os.getenv("PROJECT_NAME", "SEO AI API"),
    description="Modüler SEO ve WP İçerik Motoru",
    version="2.3.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/css", StaticFiles(directory="frontend/css"), name="css")
app.mount("/js", StaticFiles(directory="frontend/js"), name="js")

@app.get("/")
async def root():
    return FileResponse("frontend/index.html")

@app.get("/history")
async def history_page():
    return FileResponse("frontend/history.html")

@app.get("/wp-settings")
async def wp_settings_page():
    return FileResponse("frontend/wp-settings.html")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "architecture": "modular"}

@app.post("/api/v1/auto-create-article")
async def auto_create_article_endpoint(request: AutoGenerateRequest, db: Session = Depends(get_db)):
    try:
        # 1. SERP Analizi ve Gelişmiş Filtreleme
        serp_data = await fetch_serp_data(request.keyword, request.language, request.country)
        
        blacklist = ['youtube.com', 'facebook.com', 'instagram.com', 'pinterest.com', 'twitter.com', 'tiktok.com', 'linkedin.com', 'amazon.com', 'hepsiburada.com', 'trendyol.com', 'sahibinden.com', 'eksi']
        
        all_competitors = serp_data.get("competitors", [])
        valid_competitors = []
        ignored_competitors = []

        for comp in all_competitors:
            if any(blocked in comp["link"].lower() for blocked in blacklist):
                ignored_competitors.append(comp)
            else:
                valid_competitors.append(comp)
        
        if not valid_competitors:
             raise HTTPException(status_code=404, detail="Google'da bilgi içeren, taranabilir uygun rakip bulunamadı.")

        top_competitors = valid_competitors[:10]
        urls_to_scrape = [comp["link"] for comp in top_competitors]

        # 2. Kazıma İşlemi
        scrape_data = await fetch_scraped_data(urls_to_scrape)
        competitor_data = [{"url": item["url"], "content": item["content"]} for item in scrape_data.get("data", [])]
        
        if not competitor_data:
             raise HTTPException(status_code=500, detail="İçerikler kazınamadı.")

        # 3. AI İçerik Üretimi
        article_data = generate_ai_article(request.keyword, request.language, competitor_data)
        final_markdown = article_data.get("article_markdown", "")
        
        # 4. GÖRSEL ÜRETİMİ (Eksik olan ve sistemi tetikleyecek kısım)
        final_markdown = await process_images_in_article(final_markdown, request.keyword)

        process_summary = {
            "keyword": request.keyword,
            "total_found": len(all_competitors),
            "analyzed": len(top_competitors),
            "ignored": len(ignored_competitors),
            "successful_scrapes": scrape_data.get("success_count", 0),
            "competitor_details": top_competitors,
            "ignored_details": ignored_competitors
        }

        # 5. Veritabanına Kaydetme
        db_record = ArticleHistory(
            keyword=request.keyword,
            language=request.language,
            country=request.country,
            process_summary=json.dumps(process_summary),
            article_markdown=final_markdown
        )
        db.add(db_record)
        db.commit()
        db.refresh(db_record)

        return {
            "status": "success",
            "history_id": db_record.id,
            "process_summary": process_summary,
            "final_article": final_markdown
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Otomasyon Hatası: {str(e)}")

# --- Geçmiş Verileri API Endpointleri ---
@app.get("/api/v1/history")
def get_history(db: Session = Depends(get_db)):
    records = db.query(ArticleHistory).order_by(ArticleHistory.created_at.desc()).all()
    result = []
    for r in records:
        result.append({
            "id": r.id,
            "keyword": r.keyword,
            "language": r.language,
            "created_at": r.created_at,
            "process_summary": json.loads(r.process_summary),
            "article_markdown": r.article_markdown
        })
    return result

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