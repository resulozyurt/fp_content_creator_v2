import os
import json
import asyncio
import anthropic
from openai import AsyncOpenAI
import re

def get_prompts_from_article(article_markdown: str, keyword: str) -> dict:
    """Makaleyi okuyup, her IMAGE etiketi için DALL-E 3'e uygun promptlar üretir."""
    anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    prompt = f"""İşte yazılmış bir blog makalesi. İçinde [IMAGE_1], [IMAGE_2] vb. etiketler var.
Anahtar kelime: {keyword}

Görevin, bu etiketlerin geçtiği bağlamı okuyarak OpenAI DALL-E 3 yapay zekasının profesyonel, yatay (horizontal) kurumsal blog illüstrasyonları çizebilmesi için İngilizce promptlar üretmek.
Görsellerde ASLA yazı (text/typography) olmamalıdır. Temiz, modern, minimalist flat illustration veya fotogerçekçi kurumsal tarzda olmalıdır.

Aşağıdaki JSON formatında çıktıyı ver, başka hiçbir açıklama yazma:
{{
    "[IMAGE_1]": {{"prompt": "A professional flat illustration of...", "alt": "Seo uyumlu türkçe alt etiket"}},
    "[IMAGE_2]": {{"prompt": "A modern corporate photography showing...", "alt": "Seo uyumlu türkçe alt etiket"}}
}}

MAKALE METNİ:
{article_markdown[:4000]}
"""
    try:
        # Prompt üretimi için senin yetkili olduğun en güçlü modeli kullanıyoruz
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-6", 
            max_tokens=1000,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # JSON yanıtını güvenli şekilde parse et
        json_match = re.search(r'\{.*\}', response.content[0].text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
    except Exception as e:
        print(f"Prompt üretim hatası (Anthropic API): {e}")
    return {}

async def generate_openai_base64(prompt: str) -> str:
    """OpenAI DALL-E 3 API'ye bağlanıp 1792x1024 yatay resmi çizer ve doğrudan Base64 döndürür."""
    api_key = os.getenv("OPENAI_API_KEY") 
    if not api_key:
        print("KRİTİK HATA: Railway Variables içinde 'OPENAI_API_KEY' bulunamadı!")
        return ""

    client = AsyncOpenAI(api_key=api_key)
    try:
        response = await client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1792x1024", # Tam blog boyutlarına uygun yatay (widescreen) format
            quality="standard",
            response_format="b64_json", # Resmi indirmekle uğraşmadan direkt şifrelenmiş kodu alırız
            n=1,
        )
        return response.data[0].b64_json
    except Exception as e:
        print(f"OpenAI DALL-E 3 API bağlantı hatası: {e}")
    return ""

async def process_images_in_article(markdown_text: str, keyword: str) -> str:
    """Makaledeki tüm yer tutucuları gerçek görsellerle değiştirir."""
    if "[IMAGE_" not in markdown_text:
        return markdown_text

    prompts_data = get_prompts_from_article(markdown_text, keyword)
    
    if not prompts_data:
        print("UYARI: Görsel promptları üretilemediği için metin ham haliyle bırakıldı.")
        return markdown_text
        
    # Tüm görselleri paralel olarak (asenkron) hızlıca çizdir
    tasks = []
    tags = []
    alts = []
    
    for tag, data in prompts_data.items():
        if tag in markdown_text:
            tasks.append(generate_openai_base64(data["prompt"]))
            tags.append(tag)
            alts.append(data["alt"])

    results_base64 = await asyncio.gather(*tasks)

    # Markdown içindeki [IMAGE_X] etiketlerini Base64 formatıyla değiştir
    for tag, b64, alt in zip(tags, results_base64, alts):
        if b64:
            # Tarayıcıda doğrudan görünmesi için Base64 Data URI şeması
            markdown_img = f"![{alt}](data:image/jpeg;base64,{b64})"
            markdown_text = markdown_text.replace(tag, markdown_img)
        else:
            print(f"UYARI: {tag} etiketi için resim çizilemedi, ham metin bırakılıyor.")
            
    return markdown_text