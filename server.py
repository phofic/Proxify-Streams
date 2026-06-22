import base64, os, json
from urllib.parse import quote, unquote
from flask import Flask, jsonify, request, send_from_directory
from werkzeug.routing import BaseConverter

class EverythingConverter(BaseConverter):
    regex = '.*'

app = Flask(__name__)
app.url_map.converters['everything'] = EverythingConverter

# ✅ CORS only — nothing else changed
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
    # ✅ pru not pro, path format not query params, ~ separator
    return f"https://pru.ultracloud.cc/{encode_param(url)}~{encode_param(referer)}/seg.jpg"

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
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'index.html')

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

app = app
