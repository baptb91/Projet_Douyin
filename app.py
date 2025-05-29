from fastapi import FastAPI
from TikTokApi import TikTokApi
from datetime import datetime, timedelta

app = FastAPI()

USER_IDS = [
    "MS4wLjABAAAAXVtb4r6Wt_11upXRGFzZFswSIQDnSdiHA_4_lF0Lqa4",
    # Ajoute d'autres IDs ici
]

@app.get("/videos")
async def get_videos():
    videos = []
    now = datetime.utcnow()
    # Utilisation correcte du contexte asynchrone TikTokApi
    async with TikTokApi() as api:
        for user_id in USER_IDS:
            try:
                # La méthode .videos() retourne un générateur asynchrone
                user = api.user(user_id=user_id)
                async for video in user.videos(count=5):
                    # Filtrer les vidéos des dernières 24h
                    create_time = datetime.utcfromtimestamp(video.create_time)
                    if (now - create_time) < timedelta(hours=24):
                        videos.append({
                            "user_id": user_id,
                            "id": video.id,
                            "desc": video.desc,
                            "create_time": create_time.isoformat(),
                            "video_url": video.video_url,
                        })
            except Exception as e:
                videos.append({
                    "user_id": user_id,
                    "error": str(e)
                })
    return {"count": len(videos), "videos": videos}
