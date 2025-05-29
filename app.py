from fastapi import FastAPI
from TikTokApi import TikTokApi

app = FastAPI()

USER_IDS = [
    "MS4wLjABAAAAXVtb4r6Wt_11upXRGFzZFswSIQDnSdiHA_4_lF0Lqa4",
    # Ajoute d'autres IDs ici
]

@app.get("/videos")
async def get_videos():
    api = TikTokApi()
    videos = []
    for user_id in USER_IDS:
        try:
            user_videos = api.user(username=user_id).videos(count=5)
            for video in user_videos:
                videos.append({
                    "user_id": user_id,
                    "id": video.id,
                    "desc": video.desc,
                    "create_time": video.create_time,
                    "video_url": video.video_url,
                })
        except Exception as e:
            videos.append({
                "user_id": user_id,
                "error": str(e)
            })
    return {"count": len(videos), "videos": videos}
