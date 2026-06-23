import base64
import os
import json
import requests
from urllib.parse import quote, unquote
from flask import Flask, jsonify, request
from werkzeug.routing import BaseConverter

class EverythingConverter(BaseConverter):
    regex = '.*'

app = Flask(__name__)
app.url_map.converters['everything'] = EverythingConverter

@app.after_request
def apply_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type, Accept, Range"
    return response

class ProxyGenerator:
    def __init__(self):
        self.miruro_key = bytes.fromhex("a54d389c18527d9fd3e7f0643e27edbe")

    def miruro(self, url, referer):
        def encode_param(text):
            b = text.encode('utf-8')
            c = bytes([b[i] ^ self.miruro_key[i % 16] for i in range(len(b))])
            return base64.urlsafe_b64encode(c).decode('utf-8').rstrip('=')
        return f"https://pru.ultracloud.cc/{encode_param(url)}~{encode_param(referer)}/master.m3u8"

    def anikuro(self, url, referer):
        # 🔥 FIX: Parse the URL to extract anime ID and episode
        # URL format: https://vault-10.uwucdn.top/stream/10/02/{hash}/uwu.m3u8
        # or https://megaplay.buzz/{animeId}/{episodeNumber}/dub
        
        # Try to extract anime ID and episode from the URL
        if 'megaplay.buzz' in url:
            parts = url.split('/')
            # https://megaplay.buzz/{animeId}/{episodeNumber}/dub
            if len(parts) >= 6:
                anime_id = parts[3]  # Get anime ID
                episode = parts[4]   # Get episode number
                return f"https://anikuro.ru/api/v1/sources/allanime/{anime_id}:{episode}"
        
        # Fallback: try to extract from vault URL
        # The vault URL might contain the anime info, but it's hashed
        # Try using the old base64 method as fallback
        b64 = base64.b64encode(f"{url}|{referer}".encode()).decode()
        return f"https://anikuro.ru/{b64}.m3u8"

    def lunaranime(self, url, referer):
        return f"https://cluster.lunaranime.ru/api/proxy/hls/custom?url={quote(url, safe=':/')}&referer={quote(referer, safe=':/')}"

    def animanga(self, url, referer):
        headers = json.dumps({"Referer": referer})
        return f"https://upcloud.animanga.fun/proxy?url={quote(url, safe=':/')}&headers={quote(headers, safe=':/')}"

generator = ProxyGenerator()

# 🔥 NEW: Add endpoint to fetch from Anikuro API
@app.route('/anikuro_source', methods=['GET'])
def get_anikuro_source():
    try:
        anime_id = request.args.get('anime_id')
        episode = request.args.get('episode')
        
        if not anime_id or not episode:
            return jsonify({"error": "Missing anime_id or episode"}), 400
        
        # Fetch from Anikuro API
        api_url = f"https://anikuro.ru/api/v1/sources/allanime/{anime_id}:{episode}"
        response = requests.get(api_url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://anikuro.ru/',
        })
        response.raise_for_status()
        
        data = response.json()
        
        # Extract the stream URL from the response
        # The response should contain a sources array or similar
        if 'sources' in data and len(data['sources']) > 0:
            stream_url = data['sources'][0].get('url') or data['sources'][0].get('file')
            return jsonify({
                "success": True,
                "stream_url": stream_url,
                "data": data
            })
        else:
            return jsonify({
                "success": False,
                "error": "No stream found",
                "data": data
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def docs():
    return jsonify({"status": "active", "message": "Proxy server matrix running smoothly"})

@app.route('/proxy/<everything:data>', methods=['GET', 'OPTIONS'])
@app.route('/proxy', methods=['GET', 'OPTIONS'])
def get_proxy(data=None):
    if request.method == 'OPTIONS':
        return '', 200
    try:
        if not data:
            data = request.args.get('data')
        if not data:
            return jsonify({"error": "No data provided"}), 400
        data = unquote(data)
        if "https:/" in data and "https://" not in data:
            data = data.replace("https:/", "https://")
        elif "http:/" in data and "http://" not in data:
            data = data.replace("http:/", "http://")
        if "|" not in data:
            return jsonify({"error": "Invalid format (expected url|referer)", "received": data}), 400
        url, referer = data.rsplit("|", 1)
        
        return jsonify({
            "proxifiedSource": {
                "miruro": generator.miruro(url, referer),
                "anikuro": generator.anikuro(url, referer),
                "lunaranime": generator.lunaranime(url, referer),
                "animanga": generator.animanga(url, referer)
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5555))
    app.run(host='0.0.0.0', port=port, debug=False)

# Required for Vercel
application = app
