import httpx
import asyncio
from typing import List

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