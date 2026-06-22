import base64
import os
import json
from urllib.parse import quote, unquote, urljoin, urlencode
import urllib.request
import ssl
from flask import Flask, jsonify, request, send_from_directory, Response, make_response
from werkzeug.routing import BaseConverter

class EverythingConverter(BaseConverter):
    regex = '.*'

app = Flask(__name__)
app.url_map.converters['everything'] = EverythingConverter

# 🟢 CORS HOOK: Forces Vercel to attach wide access headers globally
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
        return f"https://ultracloud.cc{encode_param(url)}&r={encode_param(referer)}"

    def anikuro(self, url, referer):
        b64 = base64.b64encode(f"{url}|{referer}".encode()).decode()
        ext = ".m3u8" if ".m3u8" in url.lower() else ".mp4"
        return f"https://anikuro.to{b64}{ext}"

    def lunaranime(self, url, referer):
        return f"https://lunaranime.ru{quote(url, safe=':/')}&referer={quote(referer, safe=':/')}"

    def animanga(self, url, referer):
        headers = json.dumps({"Referer": referer})
        return f"https://animanga.fun{quote(url, safe=':/')}&headers={quote(headers, safe=':/')}"

generator = ProxyGenerator()

class SmartRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new_req = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new_req:
            for key, val in req.headers.items():
                new_req.add_header(key, val)
        return new_req

ssl_context = ssl._create_unverified_context()
opener = urllib.request.build_opener(SmartRedirectHandler(), urllib.request.HTTPSHandler(context=ssl_context))

@app.route('/')
def docs():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'index.html')


@app.route('/proxy_m3u8')
def proxy_m3u8():
    url = request.args.get('url')
    referer = request.args.get('referer')
    if not url or not referer:
        return jsonify({"error": "Missing parameters"}), 400

    spoof_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": referer,
        "Origin": referer.rstrip('/')
    }

    try:
        req = urllib.request.Request(url, headers=spoof_headers)
        with opener.open(req, timeout=15) as response:
            html_content = response.read().decode('utf-8')

        # 🟢 FIXED: Safe parent path text cutting method that prevents TypeError array list crashes
        if '/' in url:
            base_url = url[:url.rfind('/') + 1]
        else:
            base_url = url + '/'

        rewritten_lines = []

        for line in html_content.splitlines():
            clean_line = line.strip()
            if clean_line and not clean_line.startswith("#"):
                abs_url = urljoin(base_url, clean_line) if not clean_line.startswith("http") else clean_line
                params = {"url": abs_url, "referer": referer}

                if '.m3u8' in clean_line:
                    rewritten_lines.append(f"/proxy_m3u8?{urlencode(params)}")
                else:
                    rewritten_lines.append(f"/proxy_segment?{urlencode(params)}")
            elif 'URI="' in line:
                try:
                    # Clean inline key rebuilder mapping loops
                    before_uri, rest = line.split('URI="', 1)
                    key_url, after_uri = rest.split('"', 1)

                    abs_key_url = urljoin(base_url, key_url) if not key_url.startswith("http") else key_url
                    proxied_key = f"/proxy_segment?{urlencode({'url': abs_key_url, 'referer': referer})}"

                    rewritten_lines.append(f'{before_uri}URI="{proxied_key}"{after_uri}')
                except Exception:
                    rewritten_lines.append(line)
            else:
                rewritten_lines.append(line)

        return Response("\n".join(rewritten_lines), mimetype="application/vnd.apple.mpegurl")
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/proxy_segment')
def proxy_segment():
    url = request.args.get('url')
    referer = request.args.get('referer')
    if not url or not referer:
        return jsonify({"error": "Missing parameters"}), 400

    spoof_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": referer,
        "Origin": referer.rstrip('/')
    }

    try:
        req = urllib.request.Request(url, headers=spoof_headers)
        with opener.open(req, timeout=30) as response:
            binary_content = response.read()

        content_type = "video/mp2t"
        if ".key" in url or "mon.key" in url:
            content_type = "application/pgp-keys"
        elif url.endswith(".jpg") or ".jpg" in url:
            content_type = "video/mp2t"

        return Response(binary_content, mimetype=content_type, status=200)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/proxy/<everything:data>', methods=['GET', 'OPTIONS'])
@app.route('/proxy', methods=['GET', 'OPTIONS'])
def get_proxy(data=None):
    if request.method == 'OPTIONS':
        return make_response('', 200)

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
        
        # 🟢 FIXED: Hardcoded request context ensures parameter encodings do not fail inside Vercel Edge cdn layers
        native_rewrite_m3u8 = f"https://proxify-streams-theta.vercel.app/proxy_m3u8?{urlencode({'url': url, 'referer': referer})}"

        return jsonify({
            "proxifiedSource": {
                "miruro": native_rewrite_m3u8,
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
