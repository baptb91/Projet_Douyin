from flask import Flask, jsonify, request
import json
import datetime
import requests
import bs4 as bs
import os
import random

app = Flask(__name__)

# ============================================
# 🎯 CONFIGURATION - MODIFIEZ ICI LA NICHE
# ============================================
TARGET_NICHE = "美食"  # ← CHANGEZ ICI POUR UNE AUTRE NICHE

# Configuration flexible des périodes
TIME_PERIODS = {
    "24h": 86400,      # 24 heures
    "48h": 172800,     # 48 heures  
    "3days": 259200,   # 3 jours
    "7days": 604800    # 7 jours
}

# 🔥 MOTS-CLÉS POUR LA NICHE SÉLECTIONNÉE
# Ajoutez ou modifiez les mots-clés selon votre niche
def get_niche_keywords(niche):
    """Retourne les mots-clés pour la niche sélectionnée"""
    keywords_map = {
        # CUISINE / NOURRITURE
        "美食": ["美食", "料理", "烹饪", "食谱", "小吃", "美味", "厨艺"],
        
        # BEAUTÉ
        "美妆": ["美妆", "化妆", "护肤", "彩妆", "美容", "口红", "眼妆"],
        
        # VOYAGE
        "旅行": ["旅行", "旅游", "风景", "景点", "探索", "旅拍", "度假"],
        
        # MODE
        "时尚": ["时尚", "穿搭", "服装", "潮流", "搭配", "时装", "造型"],
        
        # DANSE
        "舞蹈": ["舞蹈", "跳舞", "舞步", "编舞", "舞蹈教学", "街舞", "现代舞"],
        
        # MUSIQUE
        "音乐": ["音乐", "歌曲", "演唱", "乐器", "音乐教学", "翻唱", "原创"],
        
        # SPORT
        "运动": ["运动", "健身", "锻炼", "体育", "训练", "跑步", "瑜伽"],
        
        # HUMOUR
        "搞笑": ["搞笑", "幽默", "段子", "喜剧", "恶搞", "有趣", "爆笑"],
        
        # ANIMAUX
        "宠物": ["宠物", "猫咪", "狗狗", "萌宠", "动物", "猫", "狗"],
        
        # FITNESS
        "健身": ["健身", "锻炼", "肌肉", "减肥", "塑形", "运动", "训练"],
        
        # GAMING
        "游戏": ["游戏", "电竞", "手游", "攻略", "直播", "王者", "吃鸡"],
        
        # TECH
        "科技": ["科技", "数码", "手机", "电脑", "AI", "技术", "创新"]
    }
    
    return keywords_map.get(niche, [niche])

# Nom de la niche actuelle
def get_niche_name(niche):
    """Retourne le nom français de la niche"""
    names = {
        "美食": "Cuisine/Nourriture",
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
    return names.get(niche, "Inconnu")
# ============================================

def is_within_period(timestamp, period_seconds):
    """Vérifie si le timestamp est dans la période donnée"""
    now = datetime.datetime.now().timestamp()
    return (now - timestamp) <= period_seconds

def get_cache_key():
    """Génère une clé de cache basée sur la date pour éviter le spam"""
    today = datetime.date.today().strftime("%Y-%m-%d")
    return f"{TARGET_NICHE}_{today}"

def scrape_with_fallback(max_videos=50, min_videos=10):
    """Scrape avec système de fallback intelligent pour LA niche sélectionnée"""
    
    # Récupérer les mots-clés pour la niche sélectionnée
    search_terms = get_niche_keywords(TARGET_NICHE)
    periods = ["24h", "48h", "3days", "7days"]
    
    all_results = []
    attempts = []
    
    print(f"🎯 Recherche pour la niche: {TARGET_NICHE} ({get_niche_name(TARGET_NICHE)})")
    print(f"📝 Mots-clés utilisés: {search_terms}")
    
    for period in periods:
        for search_term in search_terms:
            try:
                result = scrape_niche_period(search_term, TIME_PERIODS[period])
                attempts.append({
                    "term": search_term,
                    "period": period,
                    "count": len(result) if isinstance(result, list) else 0,
                    "status": "success" if isinstance(result, list) else "error"
                })
                
                if isinstance(result, list) and result:
                    all_results.extend(result)
                    
                    # Si on a assez de vidéos, on s'arrête
                    if len(all_results) >= min_videos:
                        break
                        
            except Exception as e:
                attempts.append({
                    "term": search_term,
                    "period": period,
                    "count": 0,
                    "status": f"error: {str(e)}"
                })
                continue
        
        # Si on a assez de vidéos, on s'arrête
        if len(all_results) >= min_videos:
            break
    
    # Supprimer les doublons basés sur l'URL
    seen_urls = set()
    unique_results = []
    for video in all_results:
        video_url = video.get('video_url', '')
        if video_url and video_url not in seen_urls:
            seen_urls.add(video_url)
            unique_results.append(video)
    
    # Mélanger et limiter
    random.shuffle(unique_results)
    final_results = unique_results[:max_videos]
    
    return {
        "success": True,
        "niche": TARGET_NICHE,
        "niche_name": get_niche_name(TARGET_NICHE),
        "keywords_used": search_terms,
        "count": len(final_results),
        "videos": final_results,
        "search_attempts": attempts,
        "fallback_used": len([a for a in attempts if a["status"] == "success"]) > 1
    }

def scrape_niche_period(search_term, period_seconds):
    """Scrape une niche pour une période donnée"""
    topic_api = 'https://aweme-hl.snssdk.com/aweme/v1/hot/search/video/list/?hotword='
    
    try:
        response = requests.get(topic_api + search_term, timeout=15)
        soup = bs.BeautifulSoup(response.content, 'html.parser')
        data = json.loads(soup.text)
        videos = data['aweme_list']
    except Exception as e:
        raise Exception(f"Erreur API pour '{search_term}': {str(e)}")
    
    # Filtrer les vidéos de la période
    filtered_videos = [v for v in videos if is_within_period(v['create_time'], period_seconds)]
    
    # Extraire URLs et thumbnails
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
                    "author": video['author'].get('nickname', ''),
                    "search_term": search_term,
                    "age_hours": round((datetime.datetime.now().timestamp() - video['create_time']) / 3600, 1)
                })
        except:
            continue
    
    return results

@app.route('/api/scrape')
def api_scrape():
    """API endpoint pour scraper la niche configurée avec fallback"""
    result = scrape_with_fallback()
    return jsonify(result)

@app.route('/api/scrape/urls-only')
def api_urls_only():
    """API endpoint qui retourne seulement les URLs avec fallback"""
    result = scrape_with_fallback()
    
    if not result["success"]:
        return jsonify(result)
    
    # Extraire seulement les URLs
    urls_data = {
        "success": True,
        "niche": TARGET_NICHE,
        "niche_name": get_niche_name(TARGET_NICHE),
        "keywords_used": result.get("keywords_used", []),
        "count": result["count"],
        "video_urls": [v["video_url"] for v in result["videos"] if v["video_url"]],
        "thumbnail_urls": [v["thumbnail_url"] for v in result["videos"] if v["thumbnail_url"]],
        "fallback_used": result["fallback_used"]
    }
    
    return jsonify(urls_data)

@app.route('/api/scrape/fresh')
def api_fresh_only():
    """API endpoint pour les vidéos des dernières 24h uniquement"""
    try:
        result = scrape_niche_period(TARGET_NICHE, TIME_PERIODS["24h"])
        
        if not result:
            return jsonify({
                "success": False,
                "error": f"Aucune vidéo fraîche trouvée pour '{TARGET_NICHE}'"
            })
        
        return jsonify({
            "success": True,
            "niche": TARGET_NICHE,
            "count": len(result),
            "videos": result
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/')
def home():
    """Documentation de l'API et configuration actuelle"""
    current_keywords = get_niche_keywords(TARGET_NICHE)
    
    return jsonify({
        "message": "Douyin Scraper API - Niche Unique avec Mots-clés Multiples",
        "configuration": {
            "niche_actuelle": TARGET_NICHE,
            "nom_niche": get_niche_name(TARGET_NICHE),
            "mots_cles_utilises": current_keywords,
            "nombre_mots_cles": len(current_keywords)
        },
        "endpoints": {
            "/api/scrape": "Données complètes avec système de fallback (RECOMMANDÉ)",
            "/api/scrape/urls-only": "URLs uniquement avec fallback (RECOMMANDÉ)",
            "/api/scrape/fresh": "Vidéos des dernières 24h uniquement"
        },
        "fonctionnalites": {
            "niche_unique": f"Se concentre uniquement sur: {get_niche_name(TARGET_NICHE)}",
            "mots_cles_multiples": f"Utilise {len(current_keywords)} mots-clés pour cette niche",
            "fallback_intelligent": "Cherche sur plusieurs périodes (24h, 48h, 3j, 7j)",
            "deduplication": "Supprime les vidéos en double",
            "melange_aleatoire": "Mélange les résultats pour plus de diversité"
        },
        "comment_changer_niche": {
            "instruction": "Modifiez la variable TARGET_NICHE ligne 12 du code",
            "exemple": "TARGET_NICHE = '美妆'  # pour changer vers Beauté",
            "niches_disponibles": {
                "美食": "Cuisine (7 mots-clés)",
                "美妆": "Beauté (7 mots-clés)", 
                "旅行": "Voyage (7 mots-clés)",
                "时尚": "Mode (7 mots-clés)",
                "舞蹈": "Danse (7 mots-clés)",
                "音乐": "Musique (7 mots-clés)",
                "运动": "Sport (7 mots-clés)",
                "搞笑": "Humour (6 mots-clés)",
                "宠物": "Animaux (7 mots-clés)",
                "健身": "Fitness (7 mots-clés)",
                "游戏": "Gaming (7 mots-clés)",
                "科技": "Tech (7 mots-clés)"
            }
        }
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
