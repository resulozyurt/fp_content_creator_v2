import httpx
import markdown
import base64
import re
import uuid
from bs4 import BeautifulSoup

def convert_html_to_gutenberg(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    gutenberg_blocks = []
    
    for element in soup.contents:
        if element.name == 'p':
            # Resimler <p> etiketleri içinde gelir, onları ayıklayıp image bloklarına çeviriyoruz
            if element.find('img'):
                img = element.find('img')
                gutenberg_blocks.append(f'\n<figure class="wp-block-image aligncenter size-large"><img src="{img["src"]}" alt="{img.get("alt", "")}"/></figure>\n')
            else:
                gutenberg_blocks.append(f'\n{str(element)}\n')
        elif element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            level = element.name[1]
            gutenberg_blocks.append(f'\n{str(element)}\n')
        elif element.name in ['ul', 'ol']:
            tag_type = "ordered" if element.name == 'ol' else "unordered"
            gutenberg_blocks.append(f'\n{str(element)}\n')
        elif element.name == 'blockquote':
            inner_html = element.encode_contents().decode('utf-8')
            gutenberg_blocks.append(f'\n<blockquote class="wp-block-quote">{inner_html}</blockquote>\n')
        elif element.name == 'table':
            gutenberg_blocks.append(f'\n<figure class="wp-block-table">{str(element)}</figure>\n')
            
    return "\n\n".join(gutenberg_blocks)

async def upload_media_to_wp(client, base_url, token, b64_data):
    """Base64 veriyi WordPress medya kütüphanesine yükler ve URL'sini döndürür."""
    media_url = f"{base_url}/wp-json/wp/v2/media"
    image_bytes = base64.b64decode(b64_data)
    unique_name = f"fieldpie-seo-{uuid.uuid4().hex[:8]}.jpg"
    
    headers = {
        "Authorization": f"Basic {token}",
        "Content-Disposition": f'attachment; filename="{unique_name}"',
        "Content-Type": "image/jpeg"
    }
    
    res = await client.post(media_url, headers=headers, content=image_bytes, timeout=60.0)
    if res.status_code in (200, 201):
        return res.json().get("source_url")
    return None

async def process_and_publish(data):
    markdown_content = data.content_markdown
    credentials = f"{data.wp_username}:{data.wp_app_password}"
    token = base64.b64encode(credentials.encode()).decode('utf-8')
    base_url = data.wp_url.rstrip('/')
    
    async with httpx.AsyncClient() as client:
        # 1. Metin içindeki tüm Base64 resimleri bul
        # Regex formatı: ![Alt Text](data:image/jpeg;base64,.....)
        pattern = r'!\[([^\]]*)\]\(data:image\/[^;]+;base64,([^\)]+)\)'
        matches = re.findall(pattern, markdown_content)
        
        for alt_text, b64_data in matches:
            # 2. Resmi fiziksel olarak WP Medya Kütüphanesine yükle
            wp_image_url = await upload_media_to_wp(client, base_url, token, b64_data)
            
            # 3. Markdown içindeki Base64 yığınını, temiz WordPress URL'si ile değiştir
            if wp_image_url:
                old_markdown_tag = f"![{alt_text}](data:image/jpeg;base64,{b64_data})"
                new_markdown_tag = f"![{alt_text}]({wp_image_url})"
                markdown_content = markdown_content.replace(old_markdown_tag, new_markdown_tag)

        # 4. Temizlenen Markdown'ı HTML'e ve ardından Gutenberg'e çevir
        raw_html = markdown.markdown(markdown_content, extensions=['tables', 'fenced_code', 'sane_lists'])
        gutenberg_content = convert_html_to_gutenberg(raw_html)
        
        # 5. Makaleyi Yayınla
        api_url = f"{base_url}/wp-json/wp/v2/posts"
        headers = {"Authorization": f"Basic {token}", "Content-Type": "application/json"}
        payload = {"title": data.title, "content": gutenberg_content, "status": data.status}
        
        response = await client.post(api_url, headers=headers, json=payload, timeout=45.0)
        
        if response.status_code in (200, 201):
            return response.json()
        else:
            raise ValueError(f"WP REST API Hatası (Kod: {response.status_code}): {response.text}")

async def publish_to_wordpress(data):
    return await process_and_publish(data)