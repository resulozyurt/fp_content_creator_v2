import os
import json
import httpx
import asyncio
import anthropic

def get_prompts_from_article(article_markdown: str, keyword: str) -> dict:
    """Makaleyi okuyup, her IMAGE etiketi için detaylı bir görsel promptu üretir."""
    anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    prompt = f"""İşte yazılmış bir blog makalesi. İçinde [IMAGE_1], [IMAGE_2] vb. etiketler var.
Anahtar kelime: {keyword}

Görevin, bu etiketlerin geçtiği bağlamı okuyarak Google Imagen yapay zekasının profesyonel, 16:9 yatay (horizontal) kurumsal blog illüstrasyonları çizebilmesi için İngilizce promptlar üretmek.
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
        response = anthropic_client.messages.create(
            model="claude-3-haiku-20240307", # Prompt analizi için hızlı ve ucuz model
            max_tokens=1000,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}]
        )
        # JSON yanıtını güvenli şekilde parse et
        import re
        json_match = re.search(r'\{.*\}', response.content[0].text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
    except Exception as e:
        print(f"Prompt üretim hatası: {e}")
    return {}

async def generate_imagen_base64(prompt: str) -> str:
    """Google Imagen 3 API'ye bağlanıp 16:9 resmi çizer ve Base64 formatında döndürür."""
    api_key = os.getenv("GEMINI_API_KEY") # Google AI Studio'dan alınacak
    if not api_key:
        return ""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-images:predict?key={api_key}"
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {"sampleCount": 1, "aspectRatio": "16:9"}
    }
    
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(url, json=payload, timeout=45.0)
            if res.status_code == 200:
                data = res.json()
                if "predictions" in data and len(data["predictions"]) > 0:
                    # Google Imagen 3 doğrudan Base64 döndürür
                    return data["predictions"][0]["bytesBase64Encoded"]
        except Exception as e:
            print(f"Imagen API hatası: {e}")
    return ""

async def process_images_in_article(markdown_text: str, keyword: str) -> str:
    """Makaledeki tüm yer tutucuları gerçek görsellerle (Base64) değiştirir."""
    if "[IMAGE_" not in markdown_text:
        return markdown_text

    prompts_data = get_prompts_from_article(markdown_text, keyword)
    
    # Tüm görselleri paralel olarak (asenkron) hızlıca çizdir
    tasks = []
    tags = []
    alts = []
    
    for tag, data in prompts_data.items():
        if tag in markdown_text:
            tasks.append(generate_imagen_base64(data["prompt"]))
            tags.append(tag)
            alts.append(data["alt"])

    results_base64 = await asyncio.gather(*tasks)

    # Markdown içindeki [IMAGE_X] etiketlerini Base64 formatıyla değiştir
    for tag, b64, alt in zip(tags, results_base64, alts):
        if b64:
            # Tarayıcıda doğrudan görünmesi için Base64 Data URI şeması
            markdown_img = f"![{alt}](data:image/jpeg;base64,{b64})"
            markdown_text = markdown_text.replace(tag, markdown_img)
            
    return markdown_text