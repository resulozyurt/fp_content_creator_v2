from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os
import httpx
import asyncio
from dotenv import load_dotenv
import anthropic
from datetime import datetime
from fastapi.responses import FileResponse

# .env dosyasındaki değişkenleri sisteme yükler
load_dotenv()

app = FastAPI(
    title=os.getenv("PROJECT_NAME", "SEO AI API"),
    description="Frase.io benzeri gelişmiş içerik üretim motoru",
    version="1.5.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Anthropic İstemcisi
anthropic_client = anthropic.Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

# --- VERİ MODELLERİ ---
class SerpRequest(BaseModel):
    keyword: str
    language: str = "tr"
    country: str = "tr"

class ScrapeRequest(BaseModel):
    urls: List[str]

class GenerateArticleRequest(BaseModel):
    keyword: str
    language: str = "tr"
    competitor_contexts: List[str]

class AutoGenerateRequest(BaseModel):
    keyword: str
    language: str = "tr"
    country: str = "tr"

# ==========================================
# --- SERVİS FONKSİYONLARI (İŞ MANTIĞI) ---
# ==========================================

async def fetch_serp_data(keyword: str, language: str, country: str):
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        raise ValueError("SERPER_API_KEY bulunamadı.")

    url = "https://google.serper.dev/search"
    payload = {"q": keyword, "hl": language, "gl": country, "num": 10}
    headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload, timeout=15.0)
        
        if response.status_code != 200:
            raise ValueError(f"Serper API Hatası (Kod: {response.status_code}): {response.text}")
        
        data = response.json()
        organic_results = data.get("organic", [])
        extracted_urls = [
            {"position": item.get("position"), "title": item.get("title"), "link": item.get("link")}
            for item in organic_results
        ]
        return {
            "keyword": keyword,
            "target_market": f"{language.upper()}-{country.upper()}",
            "competitors": extracted_urls
        }

async def fetch_scraped_data(urls: List[str]):
    async def fetch_content(client, url):
        jina_url = f"https://r.jina.ai/{url}"
        headers = {"X-Return-Format": "markdown"}
        try:
            response = await client.get(jina_url, headers=headers, timeout=30.0)
            if response.status_code == 200:
                return {"url": url, "status": "success", "content": response.text}
            else:
                return {"url": url, "status": "failed", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"url": url, "status": "failed", "error": str(e)}

    async with httpx.AsyncClient() as client:
        tasks = [fetch_content(client, url) for url in urls]
        results = await asyncio.gather(*tasks)

    successful_scrapes = [res for res in results if res["status"] == "success"]
    return {"success_count": len(successful_scrapes), "data": successful_scrapes}

def generate_ai_article(keyword: str, language: str, competitor_contexts: List[str]):
    combined_context = "\n\n---\n\n".join([text[:3000] for text in competitor_contexts])
    current_year = datetime.now().year

    # Dil bazlı özel komutlar
    if language.lower() == "en":
        lang_rules = "Write in Native US English. Use AP Style, active voice, and professional corporate idioms."
        brand_name = "FieldPie"
        faq_title = "Frequently Asked Questions (FAQ)"
    else:
        lang_rules = "Kusursuz, akıcı ve doğal bir Türkçe kullan. Çeviri kokmayan, dönüşüm odaklı (conversion-focused) bir dil benimse. Edilgen yapıları kullanma."
        brand_name = "FieldPie"
        faq_title = "Sıkça Sorulan Sorular (SSS)"

    # Gelişmiş SEO ve Dönüşüm Promptu (Mühendislik Harikası)
    system_prompt = f"""Sen dünya standartlarında bir SEO uzmanı, içerik stratejisti ve metin yazarısın.
Amacın, '{keyword}' anahtar kelimesi için Google'da 1. sıraya yerleşecek, yüksek CTR ve dönüşüm oranına sahip mükemmel bir makale yazmaktır.

Aşağıda rakiplerin içeriklerini (Bağlam) veriyorum. Rakiplerden daha kapsayıcı, daha pratik ve tamamen ÖZGÜN bir içerik üret. 
Aşağıdaki KESİN SEO KURALLARINA harfiyen uymak zorundasın:

### 1. SEO VE BAŞLIK STRATEJİSİ
- **H1 Başlığı:** Tıklama oranını (CTR) artıracak, dikkat çekici ve '{keyword}' ile birlikte '{current_year}', 'Kapsamlı Rehber', 'Checklist' gibi güncellik/fayda sinyalleri içeren güçlü bir başlık yaz.
- **H2 ve H3 Başlıkları:** Soru formatında (örn: Nasıl yapılır?, Nedir?, Neden önemlidir?) ve long-tail anahtar kelimeler içerecek şekilde kurgula.
- **Keyword Density:** Anahtar kelimeyi ('{keyword}') ilk 100 kelime içinde geçir. Metin geneline %1 ile %1.5 yoğunluğunda, doğal bir şekilde (bold yaparak) dağıt.

### 2. ARAMA NİYETİ VE KULLANICI DENEYİMİ (UX)
- **Featured Snippet Bloğu:** H1'den hemen sonra, 'What is [Keyword]?' / '[Anahtar Kelime] Nedir?' sorusuna yanıt veren, maksimum 45-50 kelimelik, net ve kutu içi (blockquote veya kalın) bir tanım paragrafı ekle.
- **Pratiklik:** İçerik teorik olmamalı. Mutlaka uygulanabilir bir "Checklist" (Kontrol Listesi) veya adım adım (step-by-step) rehber bölümü barındırmalı.
- **Okunabilirlik:** Paragrafları kısa tut (maksimum 3-4 cümle). Bol bol madde işareti (bullet points), numaralandırılmış listeler ve en az 1 adet HTML Tablo kullan.

### 3. GÖRSEL VE LİNKLEME STRATEJİSİ
- **Görseller:** İçeriğin uygun yerlerine en az 2-3 adet görsel yer tutucusu ekle. Formatı şu olmalı: `[Görsel Önerisi: Buraya içeriği anlatan, anahtar kelimeyi içeren açıklayıcı bir Alt Text ve başlık yazılacak]`
- **İç Linkler:** İçeriğin doğal akışında en az 2 yere iç link yer tutucusu ekle. Formatı: `[İç Link Önerisi: Bu kelimeden 'ilgili-kategori-veya-blog-yazisi' sayfasına link verin]`
- **Dış Linkler:** Güvenilirlik (E-E-A-T) için CDC, FDA, WHO, Forbes, Gartner vb. gibi otoriter kurumlara 1-2 adet doğal atıf yap ve link yer tutucusu koy.

### 4. DÖNÜŞÜM VE ÜRÜN ENTEGRASYONU (CRITICAL)
- İçeriğin sorun-çözüm bölümünde '{brand_name}' yazılımını (saha yönetim / operasyon platformu) doğal bir çözüm olarak konumlandır. Kaba bir reklam dili değil, "zaman kazandıran ve standartları otomatize eden teknolojik bir çözüm" olarak anlat.
- İçeriğin en sonuna çok güçlü bir **Call to Action (CTA)** ekle. (Örn: "Operasyonlarınızı dijitalleştirmek ve standartlarınızı yükseltmek için FieldPie'ı bugün ücretsiz deneyin.")

### 5. SIKÇA SORULAN SORULAR (FAQ)
- Makalenin sonuna '{faq_title}' başlığı altında, kullanıcıların Google'da en çok arattığı (PAA) 3 adet soruyu ve SEO uyumlu kısa cevaplarını ekle.

DİL VE TON KURALI: {lang_rules}
Sadece Markdown formatında makaleyi ver. Ekstra bir mesaj yazma.

RAKİP VERİLERİ (BAĞLAM):
{combined_context}
"""
    response = anthropic_client.messages.create(
        model="claude-sonnet-4-6", 
        max_tokens=4000, 
        temperature=0.75, # Yaratıcılığı ve akıcılığı biraz daha artırmak için 0.75 yapıldı
        system=system_prompt,
        messages=[{"role": "user", "content": f"Lütfen '{keyword}' konulu SEO uyumlu makaleyi yazmaya başla."}]
    )
    return {"keyword": keyword, "language": language, "article_markdown": response.content[0].text}

# ==========================================
# --- ENDPOINTLER (API YÖNLENDİRMELERİ) ---
# ==========================================

@app.get("/")
async def root():
    # Artık API durum mesajı yerine doğrudan Yönetim Panelimizi (Arayüzü) açacak
    return FileResponse("frontend/index.html")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/api/v1/analyze-serp")
async def analyze_serp_endpoint(request: SerpRequest):
    try:
        return await fetch_serp_data(request.keyword, request.language, request.country)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SERP API Hatası: {str(e)}")

@app.post("/api/v1/scrape-competitors")
async def scrape_competitors_endpoint(request: ScrapeRequest):
    if not request.urls:
        raise HTTPException(status_code=400, detail="URL listesi boş olamaz.")
    return await fetch_scraped_data(request.urls)

@app.post("/api/v1/generate-article")
async def generate_article_endpoint(request: GenerateArticleRequest):
    if not request.competitor_contexts:
        raise HTTPException(status_code=400, detail="Rakip verisi bulunamadı.")
    try:
        return generate_ai_article(request.keyword, request.language, request.competitor_contexts)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Üretim Hatası: {str(e)}")

@app.post("/api/v1/auto-create-article")
async def auto_create_article_endpoint(request: AutoGenerateRequest):
    try:
        serp_data = await fetch_serp_data(request.keyword, request.language, request.country)
        urls_to_scrape = [comp["link"] for comp in serp_data.get("competitors", [])]
        
        if not urls_to_scrape:
             raise HTTPException(status_code=404, detail="Google'da rakip bulunamadı.")

        top_5_urls = urls_to_scrape[:5]
        scrape_data = await fetch_scraped_data(top_5_urls)
        scraped_contexts = [item["content"] for item in scrape_data.get("data", [])]
        
        if not scraped_contexts:
             raise HTTPException(status_code=500, detail="Rakip sitelerin içerikleri kazınamadı.")

        article_data = generate_ai_article(request.keyword, request.language, scraped_contexts)

        return {
            "status": "success",
            "process_summary": {
                "keyword": request.keyword,
                "competitors_analyzed": len(top_5_urls),
                "successful_scrapes": scrape_data.get("success_count", 0)
            },
            "final_article": article_data.get("article_markdown", "")
        }

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Otomasyon Hatası: {str(e)}")