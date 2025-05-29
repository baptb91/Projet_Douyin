import asyncio
from fastapi import FastAPI, Query
from douyin_tiktok_scraper.scraper import Scraper
from datetime import datetime, timedelta

app = FastAPI(title="Douyin Scraper API")

# MOT-CLÉ DE LA NICHE À MODIFIER (exemple : 美食 pour "nourriture")
KEYWORD = "美食"  

# Nombre d'heures max pour considérer une vidéo comme "récente"
MAX_AGE_HOURS = 48

@app.get("/")
def home():
    return {
        "message": "API Douyin Scraper prête !",
        "info": "Modifiez la variable KEYWORD dans app.py pour changer de niche."
    }

@app.get("/videos")
async def get_videos(
    keyword: str = Query(None, description="Mot-clé de recherche Douyin (en chinois)"),
    count: int = Query(10, description="Nombre de vidéos à récupérer (max 20)")
):
    """
    Récupère les vidéos récentes d'une niche Douyin selon le mot-clé.
    """
    search_keyword = keyword if keyword else KEYWORD
    scraper = Scraper()
    try:
        # Recherche de vidéos par mot-clé (triées par les plus récentes)
        result = await scraper.search(
            query_type="general",
            keyword=search_keyword,
            sort_type="2",  # 2 = plus récentes d'abord
            count=min(count, 20)
        )
        now = datetime.utcnow()
        recent_videos = []
        for video in result.get("aweme_list", []):
            # Filtrer par date de publication
            create_time = datetime.utcfromtimestamp(video["create_time"])
            if (now - create_time) < timedelta(hours=MAX_AGE_HOURS):
                recent_videos.append({
                    "id": video["aweme_id"],
                    "desc": video["desc"],
                    "create_time": create_time.isoformat(),
                    "author": video["author"]["nickname"],
                    "video_url": video["video"]["play_addr"]["url_list"][0],
                    "cover": video["video"]["cover"]["url_list"][0],
                    "likes": video["statistics"]["digg_count"]
                })
        return {
            "keyword": search_keyword,
            "count": len(recent_videos),
            "videos": recent_videos
        }
    except Exception as e:
        return {"error": str(e)}

# Pour lancer en local : uvicorn app:app --reload --port 8000
