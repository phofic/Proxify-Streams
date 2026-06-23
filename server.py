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
# Attach the greedy path evaluator converter to handle inline slash arguments
app.url_map.converters['everything'] = EverythingConverter

@app.after_request
def apply_cors_headers(response):
    """
    Injects global Cross-Origin Resource Sharing (CORS) markers.
    Ensures your Next.js application frontend can fetch pipeline array payloads cleanly.
    """
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type, Accept, Range, Authorization"
    return response

class ProxyGenerator:
    def __init__(self):
        # Cryptographic XOR matrix structural key
        self.miruro_key = bytes.fromhex("a54d389c18527d9fd3e7f0643e27edbe")

    def miruro(self, url, referer):
        """
        Generates fully aligned Miruro pipeline parameters.
        🟢 CHANGED: Replaced obsolete /master.m3u8 with active /pl.m3u8 endpoint targets.
        """
        def encode_param(text):
            b = text.encode('utf-8')
            c = bytes([b[i] ^ self.miruro_key[i % 16] for i in range(len(b))])
            return base64.urlsafe_b64encode(c).decode('utf-8').rstrip('=')
        
        return f"https://pru.ultracloud.cc/{encode_param(url)}~{encode_param(referer)}/pl.m3u8"

    def anikuro(self, url, referer):
        """
        Parses inbound payload addresses to derive targeted source mapping structures.
        """
        if 'megaplay.buzz' in url:
            parts = url.split('/')
            # Expected Structure: https://megaplay.buzz/{animeId}/{episodeNumber}/dub
            if len(parts) >= 5:
                anime_id = parts[3]
                episode = parts[4]
                return f"https://anikuro.ru/api/v1/sources/allanime/{anime_id}:{episode}"
        
        # Safe structural fallback sequence
        b64 = base64.b64encode(f"{url}|{referer}".encode('utf-8')).decode('utf-8')
        return f"https://anikuro.ru/{b64}.m3u8"

    def lunaranime(self, url, referer):
        return f"https://cluster.lunaranime.ru/api/proxy/hls/custom?url={quote(url, safe=':/')}&referer={quote(referer, safe=':/')}"

    def animanga(self, url, referer):
        headers = json.dumps({"Referer": referer})
        return f"https://upcloud.animanga.fun/proxy?url={quote(url, safe=':/')}&headers={quote(headers, safe=':/')}"

generator = ProxyGenerator()

@app.route('/anikuro_source', methods=['GET'])
def get_anikuro_source():
    """
    Executes deep API downstream queries to isolate track endpoints directly from source matrices.
    """
    try:
        anime_id = request.args.get('anime_id')
        episode = request.args.get('episode')
        
        if not anime_id or not episode:
            return jsonify({"error": "Missing parameters anime_id or episode"}), 400
        
        api_url = f"https://anikuro.ru/api/v1/sources/allanime/{anime_id}:{episode}"
        response = requests.get(api_url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://anikuro.ru/',
        }, timeout=10) # Prevent Vercel execution lock timeouts by pinning limits
        
        response.raise_for_status()
        data = response.json()
        
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
                "error": "No viable video stream trace located in payload data container matrix.",
                "data": data
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def docs():
    return jsonify({
        "status": "active", 
        "message": "Proxy server matrix running smoothly", 
        "engine": "Flask Advanced HLS Agnostic Proxy"
    })

@app.route('/proxy/<everything:data>', methods=['GET', 'OPTIONS'])
@app.route('/proxy', methods=['GET', 'OPTIONS'])
def get_proxy(data=None):
    """
    Core pipeline endpoint routing wrapper.
    Accepts both path parameter and fallback query-string input patterns smoothly.
    """
    if request.method == 'OPTIONS':
        return '', 200
    try:
        if not data:
            data = request.args.get('data')
        if not data:
            return jsonify({"error": "No data cluster payload provided to decryption proxy pipeline"}), 400
            
        data = unquote(data)
        
        # Resolve common slash duplication layout bugs induced by client routing layers
        if "https:/" in data and "https://" not in data:
            data = data.replace("https:/", "https://")
        elif "http:/" in data and "http://" not in data:
            data = data.replace("http:/", "http://")
            
        if "|" not in data:
            return jsonify({"error": "Invalid format boundary configuration. Expected format: url|referer", "received": data}), 400
            
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
    # Production ready configuration switches
    app.run(host='0.0.0.0', port=port, debug=False)

# Essential production wrapper interface binding parameter tracking hook required for Vercel deploy deployment pipelines
application = app
