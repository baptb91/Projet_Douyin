from fastapi import FastAPI, HTTPException
from TikTokApi import TikTokApi
from datetime import datetime, timedelta
import asyncio
import logging

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Configuration des timeouts - VALEURS MAXIMALES
REQUEST_TIMEOUT = 300   # 5 minutes par utilisateur
TOTAL_TIMEOUT = 1800    # 30 minutes total pour toute l'opération

USER_IDS = [
    "MS4wLjABAAAAXVtb4r6Wt_11upXRGFzZFswSIQDnSdiHA_4_lF0Lqa4",
    # Ajoute d'autres IDs ici
]

async def fetch_user_videos(api, user_id, max_videos=50):
    """Fonction pour récupérer les vidéos d'un utilisateur avec timeout"""
    videos = []
    try:
        user = api.user(user_id=user_id)
        now = datetime.utcnow()
        
        # Timeout pour chaque utilisateur - SANS LIMITE STRICTE DE VIDEOS
        video_count = 0
        async for video in user.videos(count=100):  # Récupère jusqu'à 100 vidéos
            try:
                # Filtrer les vidéos des dernières 24h
                create_time = datetime.utcfromtimestamp(video.create_time)
                if (now - create_time) < timedelta(hours=24):
                    videos.append({
                        "user_id": user_id,
                        "id": video.id,
                        "desc": video.desc,
                        "create_time": create_time.isoformat(),
                        "video_url": video.video.download_url if hasattr(video.video, 'download_url') else None,
                    })
                video_count += 1
                
                # Log du progrès toutes les 10 vidéos
                if video_count % 10 == 0:
                    logger.info(f"Utilisateur {user_id}: {video_count} vidéos traitées, {len(videos)} récentes trouvées")
                    
            except Exception as video_error:
                logger.error(f"Erreur lors du traitement d'une vidéo pour {user_id}: {video_error}")
                continue
                
    except Exception as e:
        logger.error(f"Erreur pour l'utilisateur {user_id}: {e}")
        return {
            "user_id": user_id,
            "error": str(e),
            "videos": []
        }
    
    return {
        "user_id": user_id,
        "videos": videos,
        "count": len(videos)
    }

@app.get("/videos")
async def get_videos():
    all_videos = []
    results = []
    
    try:
        # Configuration TikTokApi avec timeout personnalisé
        async with TikTokApi() as api:
            # Créer les tâches pour tous les utilisateurs
            tasks = []
            for user_id in USER_IDS:
                # Timeout par utilisateur
                task = asyncio.wait_for(
                    fetch_user_videos(api, user_id),
                    timeout=REQUEST_TIMEOUT
                )
                tasks.append(task)
            
            # Exécuter toutes les tâches avec un timeout global
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=TOTAL_TIMEOUT
                )
            except asyncio.TimeoutError:
                logger.error(f"Timeout global de {TOTAL_TIMEOUT}s (30 minutes) atteint")
                raise HTTPException(
                    status_code=408, 
                    detail=f"Timeout: L'opération a pris plus de {TOTAL_TIMEOUT//60} minutes. Réessaye ou réduis le nombre d'utilisateurs."
                )
            
            # Traiter les résultats
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Erreur dans une tâche: {result}")
                    continue
                
                if isinstance(result, dict):
                    if "error" in result:
                        # Ajouter les erreurs aux résultats pour debugging
                        all_videos.append(result)
                    else:
                        # Ajouter les vidéos valides
                        all_videos.extend(result.get("videos", []))
            
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=408, 
            detail="Délai d'attente de 30 minutes dépassé lors de la récupération des vidéos"
        )
    except Exception as e:
        logger.error(f"Erreur générale: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Erreur interne: {str(e)}"
        )
    
    return {
        "count": len([v for v in all_videos if "error" not in v]),
        "videos": all_videos,
        "timestamp": datetime.utcnow().isoformat(),
        "processing_info": {
            "total_users_processed": len(USER_IDS),
            "timeout_settings": {
                "per_user_timeout": f"{REQUEST_TIMEOUT//60} minutes",
                "total_timeout": f"{TOTAL_TIMEOUT//60} minutes"
            }
        }
    }

# Endpoint pour tester la connectivité
@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

# Endpoint pour récupérer les vidéos d'un seul utilisateur (plus rapide)
@app.get("/videos/{user_id}")
async def get_user_videos(user_id: str):
    try:
        async with TikTokApi() as api:
            result = await asyncio.wait_for(
                fetch_user_videos(api, user_id, max_videos=10),
                timeout=REQUEST_TIMEOUT
            )
            return result
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=408,
            detail=f"Timeout: L'utilisateur {user_id} n'a pas pu être traité dans les {REQUEST_TIMEOUT//60} minutes"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
