import httpx
import markdown
import uuid
import json
import re
from bs4 import BeautifulSoup

def convert_html_to_gutenberg(html_content, image_meta_map):
    soup = BeautifulSoup(html_content, 'html.parser')
    gutenberg_blocks = []
    
    for element in soup.contents:
        if element.name is None: continue
        if element.name == 'p':
            if element.find('img'):
                img = element.find('img')
                img_src = img["src"]
                alt_text = img.get("alt", "")
                
                meta = image_meta_map.get(img_src, {})
                caption = meta.get("caption", "")
                caption_html = f'<figcaption class="wp-element-caption">{caption}</figcaption>' if caption else ""
                
                block = f'\n'
                block += f'<figure class="wp-block-image aligncenter size-large"><img src="{img_src}" alt="{alt_text}"/>{caption_html}</figure>\n'
                block += ''
                gutenberg_blocks.append(block)
            else:
                gutenberg_blocks.append(f'\n{str(element)}\n')
        elif element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            gutenberg_blocks.append(f'\n{str(element)}\n')
        elif element.name in ['ul', 'ol']:
            gutenberg_blocks.append(f'\n{str(element)}\n')
        elif element.name == 'blockquote':
            gutenberg_blocks.append(f'\n<blockquote class="wp-block-quote">{element.encode_contents().decode("utf-8")}</blockquote>\n')
        elif element.name == 'table':
            gutenberg_blocks.append(f'\n<figure class="wp-block-table">{str(element)}</figure>\n')
            
    return "\n\n".join(gutenberg_blocks)

async def download_and_upload_to_wp(client, base_url, token, image_url, meta):
    """OpenAI URLsinden resmi indirip WP'ye fiziksel olarak yükler"""
    # 1. Resmi OpenAI'dan indir
    img_res = await client.get(image_url, timeout=30.0)
    if img_res.status_code != 200:
        return None
        
    # 2. Resmi WP'ye yükle
    media_url = f"{base_url}/wp-json/wp/v2/media"
    unique_name = f"fieldpie-seo-{uuid.uuid4().hex[:8]}.png"
    
    headers = {
        "Authorization": f"Basic {token}",
        "Content-Disposition": f'attachment; filename="{unique_name}"',
        "Content-Type": "image/png",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64)"
    }
    
    res = await client.post(media_url, headers=headers, content=img_res.content, timeout=60.0)
    if res.status_code in (200, 201):
        data = res.json()
        media_id = data.get("id")
        source_url = data.get("source_url")
        
        # 3. Meta Verilerini (Title, Alt, Caption) Güncelle
        update_payload = {"title": meta.get("title", ""), "alt_text": meta.get("alt", ""), "caption": meta.get("caption", "")}
        await client.post(f"{media_url}/{media_id}", headers=headers, json=update_payload, timeout=30.0)
        return source_url
    return None

async def process_and_publish(data):
    markdown_content = data.content_markdown
    credentials = f"{data.wp_username}:{data.wp_app_password}"
    token = base64.b64encode(credentials.encode()).decode('utf-8')
    base_url = data.wp_url.rstrip('/')
    image_meta_map = {}
    
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=10)) as client:
        # Regex artık geçici OpenAI URL'lerini yakalıyor
        pattern = r'\s*!\[([^\]]*)\]\((https?:\/\/[^\)]+)\)'
        matches = re.findall(pattern, markdown_content)
        
        for meta_str, alt_text, temp_url in matches:
            meta = json.loads(meta_str) if meta_str else {"alt": alt_text}
            
            # OpenAI'dan indir -> WP'ye yükle
            wp_image_url = await download_and_upload_to_wp(client, base_url, token, temp_url, meta)
            
            old_block = f"\n![{alt_text}]({temp_url})"
            if wp_image_url:
                image_meta_map[wp_image_url] = meta
                new_block = f"![{alt_text}]({wp_image_url})"
                markdown_content = markdown_content.replace(old_block, new_block)
            else:
                markdown_content = markdown_content.replace(old_block, "") # Hata olursa sil

        raw_html = markdown.markdown(markdown_content, extensions=['tables', 'fenced_code', 'sane_lists'])
        gutenberg_content = convert_html_to_gutenberg(raw_html, image_meta_map)
        
        api_url = f"{base_url}/wp-json/wp/v2/posts"
        headers = {"Authorization": f"Basic {token}", "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
        payload = {"title": data.title, "content": gutenberg_content, "status": data.status}
        
        response = await client.post(api_url, headers=headers, json=payload, timeout=60.0)
        if response.status_code in (200, 201):
            return response.json()
        else:
            raise ValueError(f"WP Hata: {response.text[:200]}")

async def publish_to_wordpress(data):
    return await process_and_publish(data)