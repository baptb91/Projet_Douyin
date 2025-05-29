from flask import Flask, jsonify, request
import json
import datetime
import requests
import bs4 as bs
import os
import random
import time

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
    }
    
    return keywords_map.get(niche, [niche])

def get_niche_name(niche):
    """Retourne le nom français de la niche"""
    names = {
        "美食": "Cuisine/Nourriture",
        "美妆": "Beauté", 
        "旅行": "Voyage",
        "时尚": "Mode",
        "舞蹈": "Danse",
    }
    return names.get(niche, "Inconnu")

def is_within_period(timestamp, period_seconds):
    """Vérifie si le timestamp est dans la période donnée"""
    now = datetime.datetime.now().timestamp()
    return (now - timestamp) <= period_seconds

def scrape_with_multiple_apis(search_term, period_seconds):
    """Essaie plusieurs APIs de Douyin"""
    
    # Liste d'APIs à essayer
    api_endpoints = [
        f'https://aweme-hl.snssdk.com/aweme/v1/hot/search/video/list/?hotword={search_term}',
        f'https://www.douyin.com/aweme/v1/web/hot/search/video/list/?hotword={search_term}',
        f'https://aweme.snssdk.com/aweme/v1/hot/search/video/list/?hotword={search_term}'
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://www.douyin.com/'
    }
    
    for i, api_url in enumerate(api_endpoints):
        try:
            print(f"🔄 Tentative API {i+1}: {api_url[:50]}...")
            
            response = requests.get(api_url, headers=headers, timeout=20)
            print(f"📊 Status Code: {response.status_code}")
            print(f"📝 Response length: {len(response.text)}")
            
            if response.status_code == 200:
                # Essayer de parser en JSON directement
                try:
                    data = response.json()
                    if 'aweme_list' in data and data['aweme_list']:
                        return process_video_data(data['aweme_list'], period_seconds, search_term)
                except:
                    pass
                
                # Essayer avec BeautifulSoup
                try:
                    soup = bs.BeautifulSoup(response.content, 'html.parser')
                    data = json.loads(soup.text)
                    if 'aweme_list' in data and data['aweme_list']:
                        return process_video_data(data['aweme_list'], period_seconds, search_term)
                except:
                    pass
                    
            time.sleep(1)  # Pause entre les tentatives
            
        except Exception as e:
            print(f"❌ Erreur API {i+1}: {str(e)}")
            continue
    
    return {"error": f"Toutes les APIs ont échoué pour '{search_term}'"}

def process_video_data(videos, period_seconds, search_term):
    """Traite les données vidéo récupérées"""
    results = []
    
    for video in videos:
        try:
            # Vérifier la période
            if not is_within_period(video.get('create_time', 0), period_seconds):
                continue
                
            # Récupérer l'URL de la vidéo
            video_url = None
            try:
                if 'video' in video and 'download_addr' in video['video']:
                    video_urls = video['video']['download_addr']['url_list']
                    video_url = video_urls[0] if video_urls else None
                elif 'video' in video and 'play_addr' in video['video']:
                    video_urls = video['video']['play_addr']['url_list'] 
                    video_url = video_urls[0] if video_urls else None
            except:
                pass
            
            # Récupérer le thumbnail
            thumbnail_url = None
            try:
                if 'video' in video and 'cover' in video['video']:
                    thumbnail_url = video['video']['cover']['url_list'][0]
                elif 'video' in video and 'origin_cover' in video['video']:
                    thumbnail_url = video['video']['origin_cover']['url_list'][0]
            except:
                pass
            
            # Créer des URLs de test si les vraies ne fonctionnent pas
            if not video_url:
                video_url = f"https://test-video-{random.randint(1000,9999)}.mp4"
            if not thumbnail_url:
                thumbnail_url = f"https://test-thumb-{random.randint(1000,9999)}.jpg"
            
            results.append({
                "video_url": video_url,
                "thumbnail_url": thumbnail_url,
                "timestamp": video.get('create_time', int(time.time())),
                "desc": video.get('desc', f'Vidéo {search_term}'),
                "author": video.get('author', {}).get('nickname', 'Auteur inconnu'),
                "search_term": search_term,
                "age_hours": round((datetime.datetime.now().timestamp() - video.get('create_time', time.time())) / 3600, 1)
            })
            
        except Exception as e:
            print(f"⚠️ Erreur traitement vidéo: {str(e)}")
            continue
    
    return results

def generate_fallback_data():
    """Génère des données de fallback pour tester"""
    search_terms = get_niche_keywords(TARGET_NICHE)
    results = []
    
    for i in range(15):  # Générer 15 vidéos de test
        search_term = random.choice(search_terms)
        results.append({
            "video_url": f"https://douyin-video-{random.randint(10000,99999)}.mp4",
            "thumbnail_url": f"https://douyin-thumb-{random.randint(10000,99999)}.jpg", 
            "timestamp": int(time.time()) - random.randint(3600, 86400),
            "desc": f"Vidéo test {search_term} #{i+1}",
            "author": f"Auteur{random.randint(1,100)}",
            "search_term": search_term,
            "age_hours": random.randint(1, 24)
        })
    
    return results

def scrape_with_fallback(max_videos=50, min_videos=10):
    """Scrape avec système de fallback intelligent"""
    
    search_terms = get_niche_keywords(TARGET_NICHE)
    periods = ["24h", "48h", "3days", "7days"]
    
    all_results = []
    attempts = []
    
    print(f"🎯 Recherche pour: {TARGET_NICHE} ({get_niche_name(TARGET_NICHE)})")
    print(f"📝 Mots-clés: {search_terms}")
    
    # Essayer les vraies APIs
    for period in periods:
        for search_term in search_terms:
            try:
                result = scrape_with_multiple_apis(search_term, TIME_PERIODS[period])
                
                if isinstance(result, list) and result:
                    attempts.append({
                        "term": search_term,
                        "period": period,
                        "count": len(result),
                        "status": "success"
                    })
                    all_results.extend(result)
                    
                    if len(all_results) >= min_videos:
                        break
                else:
                    attempts.append({
                        "term": search_term, 
                        "period": period,
                        "count": 0,
                        "status": "no_data"
                    })
                    
            except Exception as e:
                attempts.append({
                    "term": search_term,
                    "period": period, 
                    "count": 0,
                    "status": f"error: {str(e)}"
                })
        
        if len(all_results) >= min_videos:
            break
    
    # Si pas assez de résultats, utiliser les données de fallback
    if len(all_results) < min_videos:
        print("🔄 Utilisation des données de fallback...")
        fallback_data = generate_fallback_data()
        all_results.extend(fallback_data)
        attempts.append({
            "term": "fallback",
            "period": "test",
            "count": len(fallback_data),
            "status": "fallback_used"
        })
    
    # Supprimer les doublons
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
        "fallback_used": any(a["status"] == "fallback_used" for a in attempts)
    }

@app.route('/api/scrape')
def api_scrape():
    """API endpoint pour scraper la niche configurée"""
    result = scrape_with_fallback()
    return jsonify(result)

@app.route('/api/scrape/urls-only')
def api_urls_only():
    """API endpoint qui retourne seulement les URLs"""
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

@app.route('/debug')
def debug_info():
    """Endpoint de debug pour voir ce qui se passe"""
    test_term = get_niche_keywords(TARGET_NICHE)[0]
    
    debug_info = {
        "timestamp": datetime.datetime.now().isoformat(),
        "target_niche": TARGET_NICHE,
        "niche_name": get_niche_name(TARGET_NICHE),
        "keywords": get_niche_keywords(TARGET_NICHE),
        "test_api_call": f"Test avec le mot-clé: {test_term}",
        "server_time": int(time.time())
    }
    
    # Test rapide d'une API
    try:
        test_result = scrape_with_multiple_apis(test_term, TIME_PERIODS["7days"])
        debug_info["api_test"] = {
            "status": "success" if isinstance(test_result, list) else "error",
            "result_type": type(test_result).__name__,
            "result_count": len(test_result) if isinstance(test_result, list) else 0
        }
    except Exception as e:
        debug_info["api_test"] = {
            "status": "error",
            "error": str(e)
        }
    
    return jsonify(debug_info)

@app.route('/')
def home():
    """Documentation de l'API et configuration actuelle"""
    current_keywords = get_niche_keywords(TARGET_NICHE)
    
    return jsonify({
        "message": "Douyin Scraper API - Debug Version",
        "configuration": {
            "niche_actuelle": TARGET_NICHE,
            "nom_niche": get_niche_name(TARGET_NICHE),
            "mots_cles_utilises": current_keywords,
        },
        "endpoints": {
            "/api/scrape/urls-only": "URLs avec fallback (RECOMMANDÉ)",
            "/debug": "Informations de debug",
            "/": "Cette documentation"
        },
        "status": "✅ API Active"
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
    app.run(host='0.0.0.0', port=port, debug=True)
