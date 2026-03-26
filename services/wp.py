import httpx
import markdown
import base64
import re
import uuid
import json
from bs4 import BeautifulSoup

def convert_html_to_gutenberg(html_content, image_meta_map):
    soup = BeautifulSoup(html_content, 'html.parser')
    gutenberg_blocks = []
    
    for element in soup.contents:
        if element.name is None:
            continue
            
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
            level = element.name[1]
            gutenberg_blocks.append(f'\n{str(element)}\n')
        elif element.name in ['ul', 'ol']:
            gutenberg_blocks.append(f'\n{str(element)}\n')
        elif element.name == 'blockquote':
            inner_html = element.encode_contents().decode('utf-8')
            gutenberg_blocks.append(f'\n<blockquote class="wp-block-quote">{inner_html}</blockquote>\n')
        elif element.name == 'table':
            gutenberg_blocks.append(f'\n<figure class="wp-block-table">{str(element)}</figure>\n')
            
    return "\n\n".join(gutenberg_blocks)

async def upload_media_to_wp(client, base_url, token, b64_data, meta):
    media_url = f"{base_url}/wp-json/wp/v2/media"
    image_bytes = base64.b64decode(b64_data)
    unique_name = f"fieldpie-seo-{uuid.uuid4().hex[:8]}.png"
    
    # Kinsta/Cloudflare engelini aşmak için gerçek bir Google Chrome kimliği (User-Agent) kullanıyoruz
    headers = {
        "Authorization": f"Basic {token}",
        "Content-Disposition": f'attachment; filename="{unique_name}"',
        "Content-Type": "image/png",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    
    try:
        res = await client.post(media_url, headers=headers, content=image_bytes, timeout=90.0)
        if res.status_code in (200, 201):
            data = res.json()
            media_id = data.get("id")
            source_url = data.get("source_url")
            
            update_payload = {
                "title": meta.get("title", ""),
                "alt_text": meta.get("alt", ""),
                "caption": meta.get("caption", "")
            }
            await client.post(f"{media_url}/{media_id}", headers=headers, json=update_payload, timeout=45.0)
            return source_url
        else:
            print(f"[HATA] WP Medya Yükleme Başarısız: Kod {res.status_code} - Yanıt: {res.text[:200]}")
            return None
    except Exception as e:
        print(f"[HATA] WP API Medya Bağlantı Hatası: {e}")
        return None

async def process_and_publish(data):
    markdown_content = data.content_markdown
    credentials = f"{data.wp_username}:{data.wp_app_password}"
    token = base64.b64encode(credentials.encode()).decode('utf-8')
    base_url = data.wp_url.rstrip('/')
    
    image_meta_map = {}
    
    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    async with httpx.AsyncClient(limits=limits) as client:
        pattern = r'\s*!\[([^\]]*)\]\(data:image\/[^;]+;base64,([^\)]+)\)'
        matches = re.findall(pattern, markdown_content)
        
        for meta_str, alt_text, b64_data in matches:
            try:
                meta = json.loads(meta_str)
            except:
                meta = {"alt": alt_text, "title": "", "caption": ""}
                
            wp_image_url = await upload_media_to_wp(client, base_url, token, b64_data, meta)
            
            old_block_png = f"\n![{alt_text}](data:image/png;base64,{b64_data})"
            old_block_jpg = f"\n![{alt_text}](data:image/jpeg;base64,{b64_data})"
            
            if wp_image_url:
                image_meta_map[wp_image_url] = meta
                new_block = f"![{alt_text}]({wp_image_url})"
                # Her iki ihtimale karşı temizleme (JPG/PNG)
                markdown_content = markdown_content.replace(old_block_png, new_block).replace(old_block_jpg, new_block)
            else:
                # GÜVENLİK KİLİDİ: Kinsta resmi tamamen reddederse, 15MB'lık kodu metinden silip makaleyi kurtarıyoruz.
                markdown_content = markdown_content.replace(old_block_png, "").replace(old_block_jpg, "")

        raw_html = markdown.markdown(markdown_content, extensions=['tables', 'fenced_code', 'sane_lists'])
        gutenberg_content = convert_html_to_gutenberg(raw_html, image_meta_map)
        
        api_url = f"{base_url}/wp-json/wp/v2/posts"
        headers = {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        payload = {"title": data.title, "content": gutenberg_content, "status": data.status}
        
        try:
            response = await client.post(api_url, headers=headers, json=payload, timeout=90.0)
            if response.status_code in (200, 201):
                return response.json()
            else:
                raise ValueError(f"WP REST API Hatası (Kod: {response.status_code}): {response.text[:200]}")
        except Exception as e:
            raise ValueError(f"WordPress bağlantısı sırasında ağ hatası oluştu: {str(e)}")

async def publish_to_wordpress(data):
    return await process_and_publish(data)