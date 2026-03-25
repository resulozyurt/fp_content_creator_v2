import httpx
import markdown
import base64

async def publish_to_wordpress(data):
    # 1. Markdown'ı WP uyumlu HTML'e çevir (Tablolar ve kod blokları desteğiyle)
    html_content = markdown.markdown(data.content_markdown, extensions=['tables', 'fenced_code'])
    
    # 2. Basic Auth için Uygulama Şifresini Encode et
    credentials = f"{data.wp_username}:{data.wp_app_password}"
    token = base64.b64encode(credentials.encode()).decode('utf-8')
    
    headers = {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # 3. URL Temizliği ve Endpoint Hazırlığı
    base_url = data.wp_url.rstrip('/')
    api_url = f"{base_url}/wp-json/wp/v2/posts"
    
    payload = {
        "title": data.title,
        "content": html_content,
        "status": data.status
        # Not: İleride MetaBox/ACF için "meta": {"alan_adi": "deger"} eklenebilir.
    }
    
    # 4. Asenkron İstek
    async with httpx.AsyncClient() as client:
        response = await client.post(api_url, headers=headers, json=payload, timeout=30.0)
        
        if response.status_code in (200, 201):
            return response.json()
        else:
            raise ValueError(f"WP REST API Hatası (Kod: {response.status_code}): {response.text}")