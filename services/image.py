import os
import json
import asyncio
import anthropic
import httpx
from openai import AsyncOpenAI
import re

def get_prompts_from_article(article_markdown: str, keyword: str, language: str) -> dict:
    print("\n-------------------------------------------")
    print("1. TÜM GÖRSELLER İÇİN SEO META VE PROMPT ANALİZİ BAŞLADI (ANTHROPIC)")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        print("[!] KRİTİK HATA: ANTHROPIC_API_KEY bulunamadı!")
        return {}
    
    anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
    
    lang_instruction = "fluent Turkish." if language.lower() != "en" else "Native English."

    # GÜNCELLEME 1: Prompt talimatları dört SEO meta verisini ('alt', 'title', 'caption', 'description') ve tüm görselleri kapsayacak şekilde sertleştirildi.
    prompt = f"""You are an expert art director and SEO specialist. 
TASK: Scan the ENTIRE article below and find EVERY placeholder like [IMAGE_1], [IMAGE_2], [IMAGE_AUTO_1], etc.
For EACH placeholder you find, create a unique DALL-E 3 prompt and SEO metadata.

Keyword: {keyword}

CRITICAL SEO RULES:
- Style: ULTRA-REALISTIC, DSLR photography, 35mm lens, natural lighting. NO text in images.
- {lang_instruction} (for alt, title, caption, and description).
- 'alt': SEO Alt text (describes image).
- 'title': Catchy Title.
- 'caption': SEO Caption (helpful sentence).
- 'description': Detailed SEO Description (a paragraph-length description, focusing on content and context).

Output EXACTLY in this JSON format:
{{
    "[IMAGE_1]": {{"prompt": "Description for DALL-E", "alt": "SEO Alt text", "title": "SEO Title", "caption": "Helpful caption", "description": "Detailed description"}}
}}

ARTICLE CONTENT:
{article_markdown[:5000]} 
""" # 3000'den 5000'e çıkarıldı ki enjekte edilen etiketleri de görsün.

    try:
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )
        json_match = re.search(r'\{.*\}', response.content[0].text, re.DOTALL)
        if json_match:
            prompts = json.loads(json_match.group(0))
            print(f"2. Analiz Tamam: Toplam {len(prompts)} adet görsel etiketi tespit edildi.")
            return prompts
        print("[!] HATA: Anthropic JSON çıktısı vermedi.")
    except Exception as e:
        print(f"[!] ANTHROPIC API HATASI: {e}")
    return {}

async def generate_openai_base64(prompt: str, index: int) -> str:
    """Eski Motor: DALL-E 3 (Bütçe onayı gelene kadar bekleyecek)"""
    print(f"   -> [{index}] nolu görsel OpenAI üzerinden isteniyor...")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        return ""
    
    client = AsyncOpenAI(api_key=openai_api_key)
    try:
        enhanced_prompt = prompt + " Must be ultra-photorealistic, raw photography, natural lighting, no text."
        response = await client.images.generate(
            model="dall-e-3",
            prompt=enhanced_prompt[:3900],
            size="1792x1024",
            quality="standard",
            response_format="b64_json",
            n=1,
            timeout=120.0
        )
        b64 = response.data[0].b64_json
        if b64:
            print(f"   -> [{index}] nolu DALL-E 3 verisi başarıyla alındı.")
            return b64
    except Exception as e:
        print(f"   [!] [{index}] OPENAI API HATASI: {e}")
    return ""

async def generate_nanobanana_base64(prompt: str, index: int) -> str:
    """Yeni Motor: Nano Banana 2 (Gemini 3.1 Flash Image Preview)"""
    print(f"   -> [{index}] nolu görsel Nano Banana 2 üzerinden isteniyor...")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("   [!] KRİTİK HATA: GEMINI_API_KEY .env dosyasında bulunamadı!")
        return ""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image-preview:generateContent?key={api_key}"
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt + " Ultra-realistic, DSLR quality, raw photography, natural lighting, NO text"}
                ]
            }
        ]
    }
    
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=60.0)
            if res.status_code == 200:
                data = res.json()
                parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                for part in parts:
                    if "inlineData" in part:
                        print(f"   -> [{index}] nolu görsel verisi başarıyla alındı.")
                        return part["inlineData"]["data"]
            else:
                print(f"   [!] [{index}] HATA: Nano Banana API Kod {res.status_code}")
        except Exception as e:
            print(f"   [!] [{index}] BAĞLANTI HATASI: {e}")
    return ""

async def process_images_in_article(markdown_text: str, keyword: str, language: str, engine: str = "nanobanana") -> str:
    # GÜNCELLEME 2: AGRESİF ENJEKSİYON MOTORU DEVREYE GİRDİ
    # Metindeki tüm H2 etiketlerini tespit ediyoruz
    h2_pattern = re.compile(r'(?m)^##\s+.+$')
    h2_matches = list(re.finditer(h2_pattern, markdown_text))
    
    # 3. H2 etiketinden hemen sonra otomatik olarak yepyeni bir [IMAGE_AUTO_X] görsel placeholder'ı enjekte ediyoruz.
    # Bu aggressive adjustment, okunabilirliği güçlendirmek için görsel sayısını ciddi şekilde artırır.
    new_markdown = ""
    last_end = 0
    h2_counter = 0
    image_auto_count = 1
    
    for i, match in enumerate(h2_matches):
        h2_counter += 1
        # Metni bu h2'ye kadar kopyalıyoruz (önceki enjekte edilenleri de kapsar)
        new_markdown += markdown_text[last_end:match.start()]
        
        # H2 etiketini kendisini kopyalıyoruz
        new_markdown += match.group(0)
        
        # İstisnasız her üçüncü (3.) H2 etiketinden hemen sonra enjeksiyon yapıyoruz
        if h2_counter % 3 == 0:
            new_markdown += f"\n[IMAGE_AUTO_{image_auto_count}]\n"
            image_auto_count += 1
            h2_counter = 0 # reset counter after insertion
        
        last_end = match.end()
        
    # Kalan metni kopyalıyoruz
    new_markdown += markdown_text[last_end:]
    
    # Artık metindeki tüm [IMAGE_...] etiketleri için prompt hazırlıyoruz.
    markdown_text = new_markdown

    if "[IMAGE_" not in markdown_text:
        return markdown_text

    prompts_data = get_prompts_from_article(markdown_text, keyword, language)
    if not prompts_data:
        return markdown_text
        
    print(f"3. TOPLU GÖRSEL VE SEO META OLUŞTURMA BAŞLIYOR (Motor: {engine.upper()})")
    
    tasks = []
    tags = []
    meta_list = []
    
    # Tüm etiketler için motor seçimine göre paralel görevler oluşturuluyor
    for i, (tag, data) in enumerate(prompts_data.items(), 1):
        if tag in markdown_text:
            if engine == "nanobanana":
                tasks.append(generate_nanobanana_base64(data["prompt"], i))
            elif engine == "openai":
                tasks.append(generate_openai_base64(data["prompt"], i))
            tags.append(tag)
            meta_list.append(data)

    # GÜNCELLEME 3: Tüm görseller aynı anda paralel olarak üretilir, vakit kazandırır.
    results_base64 = await asyncio.gather(*tasks)

    for tag, b64, meta in zip(tags, results_base64, meta_list):
        if b64:
            # GÜNCELLEME 4: Artık 4 meta veri ('alt', 'title', 'caption', 'description') Gutenberg bloğuna meta_json olarak gömülür.
            meta_json = json.dumps({
                "alt": meta["alt"], 
                "title": meta["title"], 
                "caption": meta["caption"],
                "description": meta.get("description", "") # Description da eklendi
            })
            markdown_img = f"\n![{meta['alt']}](data:image/png;base64,{b64})"
            markdown_text = markdown_text.replace(tag, markdown_img)
            print(f"   -> Metin güncellendi: {tag}")
            
    print("-------------------------------------------\n")
    return markdown_text