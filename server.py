import base64
import os
import json
import re
from urllib.parse import quote, unquote
from flask import Flask, jsonify, request, send_from_directory, Response
from werkzeug.routing import BaseConverter
import requests

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

    def miruro_transcoded(self, url, referer):
        """Returns a transcoded stream URL via our proxy"""
        original_url = self.miruro(url, referer)
        return f"/transcode_miruro?url={quote(original_url, safe=':/')}"

    def anikuro(self, url, referer):
        b64 = base64.b64encode(f"{url}|{referer}".encode()).decode()
        ext = ".m3u8" if ".m3u8" in url.lower() else ".mp4"
        return f"https://proxy.anikuro.to/{b64}{ext}"

    def lunaranime(self, url, referer):
        return f"https://cluster.lunaranime.ru/api/proxy/hls/custom?url={quote(url, safe=':/')}&referer={quote(referer, safe=':/')}"

    def animanga(self, url, referer):
        headers = json.dumps({"Referer": referer})
        return f"https://upcloud.animanga.fun/proxy?url={quote(url, safe=':/')}&headers={quote(headers, safe=':/')}"

generator = ProxyGenerator()

@app.route('/')
def docs():
    try:
        return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'index.html')
    except:
        return jsonify({"message": "Proxy server is running"})

@app.route('/transcode_miruro', methods=['GET'])
def transcode_miruro():
    """Fetches the Miruro manifest and filters problematic audio codecs"""
    try:
        url = request.args.get('url')
        if not url:
            return jsonify({"error": "No URL provided"}), 400
        
        # Fetch the manifest
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://kwik.cx/'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        manifest = response.text
        
        # If it's a master manifest with multiple variants
        if '#EXT-X-STREAM-INF' in manifest:
            lines = manifest.split('\n')
            new_lines = []
            i = 0
            
            while i < len(lines):
                line = lines[i].strip()
                if '#EXT-X-STREAM-INF' in line:
                    # Check if this is a video variant (has RESOLUTION or avc codec)
                    has_video = 'RESOLUTION' in line or ('CODECS' in line and 'avc' in line.lower())
                    if has_video:
                        # Keep this variant
                        new_lines.append(line)
                        # Get the URL (next line)
                        if i + 1 < len(lines):
                            url_line = lines[i + 1].strip()
                            if url_line and not url_line.startswith('#'):
                                # Make full URL if relative
                                if not url_line.startswith('http'):
                                    base_url = url.rsplit('/', 1)[0]
                                    url_line = f"{base_url}/{url_line}"
                                new_lines.append(url_line)
                    i += 2
                else:
                    new_lines.append(line)
                    i += 1
            
            # If we found video variants, serve the filtered manifest
            if new_lines:
                # Keep only EXT-X-STREAM-INF lines and their URLs
                filtered_lines = []
                for line in new_lines:
                    if '#EXT-X-STREAM-INF' in line or (not line.startswith('#') and line):
                        filtered_lines.append(line)
                
                if filtered_lines:
                    modified_manifest = '#EXTM3U\n' + '\n'.join(filtered_lines)
                    return Response(modified_manifest, mimetype='application/vnd.apple.mpegurl')
        
        # If no video variants found or direct manifest, just pass through
        return Response(manifest, mimetype='application/vnd.apple.mpegurl')
    
    except Exception as e:
        return jsonify({"error": f"Transcoding error: {str(e)}"}), 500

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
        
        # Return both the original Miruro URL and the transcoded URL
        return jsonify({
            "proxifiedSource": {
                "miruro": generator.miruro(url, referer),
                "miruro_transcoded": generator.miruro_transcoded(url, referer),
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
