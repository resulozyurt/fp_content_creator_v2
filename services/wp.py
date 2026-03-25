import httpx
import markdown
import base64
from bs4 import BeautifulSoup

def convert_html_to_gutenberg(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    gutenberg_blocks = []
    
    for element in soup.contents:
        if element.name == 'p':
            gutenberg_blocks.append(f'\n{str(element)}\n')
        elif element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            level = element.name[1]
            gutenberg_blocks.append(f'\n{str(element)}\n')
        elif element.name == 'ul':
            gutenberg_blocks.append(f'\n{str(element)}\n')
        elif element.name == 'ol':
            gutenberg_blocks.append(f'\n{str(element)}\n')
        elif element.name == 'blockquote':
            inner_html = element.encode_contents().decode('utf-8')
            gutenberg_blocks.append(f'\n<blockquote class="wp-block-quote">{inner_html}</blockquote>\n')
        elif element.name == 'table':
            gutenberg_blocks.append(f'\n<figure class="wp-block-table">{str(element)}</figure>\n')
        elif str(element).strip() != '':
            gutenberg_blocks.append(f'\n{str(element)}\n')
            
    return "\n\n".join(gutenberg_blocks)

async def publish_to_wordpress(data):
    # 1. Markdown -> Saf HTML -> Gutenberg Blocks dönüşümü
    raw_html = markdown.markdown(data.content_markdown, extensions=['tables', 'fenced_code', 'sane_lists'])
    gutenberg_content = convert_html_to_gutenberg(raw_html)
    
    credentials = f"{data.wp_username}:{data.wp_app_password}"
    token = base64.b64encode(credentials.encode()).decode('utf-8')
    
    headers = {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    base_url = data.wp_url.rstrip('/')
    api_url = f"{base_url}/wp-json/wp/v2/posts"
    
    payload = {
        "title": data.title,
        "content": gutenberg_content,
        "status": data.status
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(api_url, headers=headers, json=payload, timeout=45.0)
        
        if response.status_code in (200, 201):
            return response.json()
        else:
            raise ValueError(f"WP REST API Hatası (Kod: {response.status_code}): {response.text}")