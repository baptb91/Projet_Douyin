from fastapi import FastAPI, Query
from douyin_tiktok_scraper.scraper import Scraper
from datetime import datetime, timedelta

app = FastAPI(title="Douyin Multi-User Scraper")

# Mets ici la liste des user_id Douyin à surveiller 
USER_IDS = [
    "MS4wLjABAAAAXVtb4r6Wt_11upXRGFzZFswSIQDnSdiHA_4_lF0Lqa4", 
    "MS4wLjABAAAAC-UO6NnGosBUYJ8ECMZUeh_UBrIUTqsxvpXPhPv0DAXZVjVI1Xqv1oXWbTdOvQ0L",  # Ajoute autant d'IDs que tu veux
]

@app.get("/")
def home():
    return {
        "message": "API Douyin Multi-User Scraper prête !",
        "info": "Modifie la liste USER_IDS dans app.py pour surveiller d'autres comptes."
    }

@app.get("/videos")
async def get_videos(
    count_per_user: int = Query(5, ge=1, le=20, description="Nombre de vidéos à récupérer par utilisateur")
):
    """
    Récupère les vidéos publiées dans les dernières 24h pour chaque user_id.
    """
    scraper = Scraper()
    now = datetime.utcnow()
    videos = []
    for user_id in USER_IDS:
        try:
            result = await scraper.user_videos(user_id, count=count_per_user)
            for video in result.get("aweme_list", []):
                create_time = datetime.utcfromtimestamp(video["create_time"])
                if (now - create_time) < timedelta(hours=24):
                    videos.append({
                        "user_id": user_id,
                        "id": video["aweme_id"],
                        "desc": video["desc"],
                        "create_time": create_time.isoformat(),
                        "author": video["author"]["nickname"],
                        "video_url": video["video"]["play_addr"]["url_list"][0],
                        "cover": video["video"]["cover"]["url_list"][0],
                        "likes": video["statistics"]["digg_count"]
                    })
        except Exception as e:
            videos.append({
                "user_id": user_id,
                "error": str(e)
            })
    return {
        "count": len(videos),
        "videos": videos
    }

# Pour lancer en local : uvicorn app:app --reload --port 8000
