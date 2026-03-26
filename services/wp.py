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
        if element.name is None or element.name == '\n':
            continue
            
        if element.name == 'p':
            if element.find('img'):
                img = element.find('img')
                img_src = img.get("src", "")
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
        else:
            gutenberg_blocks.append(f'\n{str(element)}\n')
            
    return "\n\n".join(gutenberg_blocks)

async def upload_bytes_to_wp(client, base_url, token, image_bytes, meta):
    """Resim byte verisini WP Medya Kütüphanesine yükler"""
    media_url = f"{base_url}/wp-json/wp/v2/media"
    unique_name = f"fieldpie-seo-{uuid.uuid4().hex[:8]}.jpg"
    
    headers = {
        "Authorization": f"Basic {token}",
        "Content-Disposition": f'attachment; filename="{unique_name}"',
        "Content-Type": "image/jpeg",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        res = await client.post(media_url, headers=headers, content=image_bytes, timeout=60.0)
        if res.status_code in (200, 201):
            data = res.json()
            media_id = data.get("id")
            source_url = data.get("source_url")
            
            update_payload = {
                "title": meta.get("title", ""),
                "alt_text": meta.get("alt", ""),
                "caption": meta.get("caption", "")
            }
            await client.post(f"{media_url}/{media_id}", headers=headers, json=update_payload, timeout=30.0)
            return source_url
        else:
            print(f"[HATA] WP Medya Yükleme Reddedildi: {res.status_code} - {res.text[:200]}")
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
    
    # Geçmişteki eski makalelerin devasa verilerini (Base64) ve yeni URL'leri bulacak çift taraflı radarımız
    b64_pattern = r'\s*!\[([^\]]*)\]\(data:image\/[^;]+;base64,([^\)]+)\)'
    url_pattern = r'\s*!\[([^\]]*)\]\((https?:\/\/[^\)]+)\)'
    
    b64_matches = re.findall(b64_pattern, markdown_content)
    url_matches = re.findall(url_pattern, markdown_content)

    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=10)) as client:
        
        # 1. Eski Makalelerdeki Devasa Base64 Verileri İşle ve Metinden Sil
        for meta_str, alt_text, b64_data in b64_matches:
            meta = json.loads(meta_str) if meta_str else {"alt": alt_text}
            image_bytes = base64.b64decode(b64_data)
            
            wp_image_url = await upload_bytes_to_wp(client, base_url, token, image_bytes, meta)
            
            # Eski devasa blokları temizle
            old_block_png = f"\n![{alt_text}](data:image/png;base64,{b64_data})"
            old_block_jpg = f"\n![{alt_text}](data:image/jpeg;base64,{b64_data})"
            
            if wp_image_url:
                image_meta_map[wp_image_url] = meta
                markdown_content = markdown_content.replace(old_block_png, f"![{alt_text}]({wp_image_url})")
                markdown_content = markdown_content.replace(old_block_jpg, f"![{alt_text}]({wp_image_url})")
            else:
                markdown_content = markdown_content.replace(old_block_png, "").replace(old_block_jpg, "")

        # 2. Yeni Makalelerdeki URL'leri İşle
        for meta_str, alt_text, img_url in url_matches:
            meta = json.loads(meta_str) if meta_str else {"alt": alt_text}
            
            try:
                img_res = await client.get(img_url, timeout=30.0)
                if img_res.status_code == 200:
                    wp_image_url = await upload_bytes_to_wp(client, base_url, token, img_res.content, meta)
                else:
                    wp_image_url = None
            except:
                wp_image_url = None
                
            old_block = f"\n![{alt_text}]({img_url})"
            
            if wp_image_url:
                image_meta_map[wp_image_url] = meta
                markdown_content = markdown_content.replace(old_block, f"![{alt_text}]({wp_image_url})")
            else:
                markdown_content = markdown_content.replace(old_block, "")

        # EN KRİTİK ADIM: Eğer regex'ten kaçan ham bir Base64 resmi varsa onu zorla sil ki WP çökmesin!
        markdown_content = re.sub(r'!\[.*?\]\(data:image\/.*?;base64,.*?\)', '', markdown_content)

        # Temizlenen ve WP linkleriyle değiştirilen içeriği HTML'e çevir
        raw_html = markdown.markdown(markdown_content, extensions=['tables', 'fenced_code', 'sane_lists'])
        gutenberg_content = convert_html_to_gutenberg(raw_html, image_meta_map)
        
        # WP'ye Gönderim
        api_url = f"{base_url}/wp-json/wp/v2/posts"
        headers = {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        payload = {"title": data.title, "content": gutenberg_content, "status": data.status}
        
        try:
            response = await client.post(api_url, headers=headers, json=payload, timeout=60.0)
            if response.status_code in (200, 201):
                return response.json()
            else:
                raise ValueError(f"WP Sunucu Hatası: {response.text[:200]}")
        except httpx.ReadTimeout:
            raise ValueError("WordPress yanıt vermedi (Zaman Aşımı). Lütfen WP sitenizi kontrol edin.")
        except Exception as e:
            raise ValueError(f"WordPress bağlantısı sırasında ağ hatası oluştu: {str(e)}")

async def publish_to_wordpress(data):
    return await process_and_publish(data)