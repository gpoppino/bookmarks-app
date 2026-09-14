"""Remote bookmark metadata retrieval."""

import requests
from bs4 import BeautifulSoup


def fetch_bookmark_metadata(url: str) -> dict:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 "
        "Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        title_tag = soup.find("title")
        title = (
            title_tag.string.strip()
            if title_tag and title_tag.string
            else "No title found"
        )
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if not meta_desc:
            meta_desc = soup.find("meta", attrs={"property": "og:description"})
        description = (
            meta_desc["content"].strip()
            if meta_desc and meta_desc.get("content")
            else "No description available"
        )
        return {"success": True, "url": url, "title": title, "description": description}
    except requests.exceptions.RequestException as error:
        return {"success": False, "url": url, "error": str(error)}
