from flask import Flask, jsonify
import json
import datetime
import requests
import bs4 as bs
import os

app = Flask(__name__)

# ============================================
# 🎯 CONFIGURATION - MODIFIEZ ICI LA NICHE
# ============================================
TARGET_NICHE = "美食"  # ← CHANGEZ ICI POUR UNE AUTRE NICHE

# Niches disponibles (pour référence) :
AVAILABLE_NICHES = {
    "美食": "Nourriture",
    "美妆": "Beauté", 
    "旅行": "Voyage",
    "时尚": "Mode",
    "舞蹈": "Danse",
    "音乐": "Musique",
    "运动": "Sport",
    "搞笑": "Humour",
    "宠物": "Animaux",
    "健身": "Fitness",
    "游戏": "Gaming",
    "科技": "Tech"
}
# ============================================

def is_within_24h(timestamp):
    """Vérifie si le timestamp est dans les dernières 24h"""
    now = datetime.datetime.now().timestamp()
    return (now - timestamp) <= 86400

def scrape_target_niche():
    """Scrape la niche configurée et retourne URLs + thumbnails"""
    topic_api = 'https://aweme-hl.snssdk.com/aweme/v1/hot/search/video/list/?hotword='
    
    try:
        response = requests.get(topic_api + TARGET_NICHE, timeout=15)
        soup = bs.BeautifulSoup(response.content, 'html.parser')
        data = json.loads(soup.text)
        videos = data['aweme_list']
    except Exception as e:
        return {"error": f"Erreur API: {str(e)}"}
    
    # Filtrer les vidéos des dernières 24h
    filtered_videos = [v for v in videos if is_within_24h(v['create_time'])]
    
    if not filtered_videos:
        return {"error": f"Aucune vidéo trouvée dans les dernières 24h pour '{TARGET_NICHE}'"}
    
    # Extraire URLs et thumbnails uniquement
    results = []
    for video in filtered_videos:
        try:
            # Récupérer l'URL de la vidéo
            video_url = None
            try:
                video_urls = video['video']['download_addr']['url_list']
                video_url = next((url for url in video_urls if 'default' in url), video_urls[0] if video_urls else None)
            except:
                pass
            
            # Récupérer le thumbnail
            thumbnail_url = None
            try:
                thumbnail_url = video['video']['cover']['url_list'][0]
            except:
                pass
            
            if video_url or thumbnail_url:  # Au moins une URL valide
                results.append({
                    "video_url": video_url,
                    "thumbnail_url": thumbnail_url,
                    "timestamp": video['create_time'],
                    "desc": video.get('desc', ''),
                    "author": video['author'].get('nickname', '')
                })
        except:
            continue
    
    return {
        "success": True,
        "niche": TARGET_NICHE,
        "niche_name": AVAILABLE_NICHES.get(TARGET_NICHE, "Inconnu"),
        "count": len(results),
        "videos": results
    }

@app.route('/api/scrape')
def api_scrape():
    """API endpoint pour scraper la niche configurée"""
    result = scrape_target_niche()
    return jsonify(result)

@app.route('/api/scrape/urls-only')
def api_urls_only():
    """API endpoint qui retourne seulement les URLs"""
    result = scrape_target_niche()
    
    if "error" in result:
        return jsonify(result)
    
    # Extraire seulement les URLs
    urls_data = {
        "success": True,
        "niche": TARGET_NICHE,
        "niche_name": AVAILABLE_NICHES.get(TARGET_NICHE, "Inconnu"),
        "count": result["count"],
        "video_urls": [v["video_url"] for v in result["videos"] if v["video_url"]],
        "thumbnail_urls": [v["thumbnail_url"] for v in result["videos"] if v["thumbnail_url"]]
    }
    
    return jsonify(urls_data)

@app.route('/')
def home():
    """Documentation de l'API et configuration actuelle"""
    return jsonify({
        "message": "Douyin Scraper API - Niche Fixe",
        "configuration": {
            "niche_actuelle": TARGET_NICHE,
            "nom_niche": AVAILABLE_NICHES.get(TARGET_NICHE, "Inconnu")
        },
        "endpoints": {
            "/api/scrape": "Données complètes pour la niche configurée",
            "/api/scrape/urls-only": "URLs uniquement"
        },
        "comment_changer_niche": {
            "instruction": "Modifiez la variable TARGET_NICHE ligne 12 du code",
            "exemple": "TARGET_NICHE = '美妆'  # pour changer vers Beauté"
        },
        "niches_disponibles": AVAILABLE_NICHES
    })

@app.route('/health')
def health():
    """Health check pour Render"""
    return jsonify({
        "status": "healthy", 
        "timestamp": datetime.datetime.now().isoformat(),
        "current_niche": TARGET_NICHE
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
