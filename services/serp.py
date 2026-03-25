import os
import httpx

async def fetch_serp_data(keyword: str, language: str, country: str):
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        raise ValueError("SERPER_API_KEY bulunamadı.")

    url = "https://google.serper.dev/search"
    payload = {"q": keyword, "hl": language, "gl": country, "num": 10}
    headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload, timeout=15.0)
        
        if response.status_code != 200:
            raise ValueError(f"Serper API Hatası (Kod: {response.status_code}): {response.text}")
        
        data = response.json()
        organic_results = data.get("organic", [])
        extracted_urls = [
            {"position": item.get("position"), "title": item.get("title"), "link": item.get("link")}
            for item in organic_results
        ]
        return {
            "keyword": keyword,
            "target_market": f"{language.upper()}-{country.upper()}",
            "competitors": extracted_urls
        }