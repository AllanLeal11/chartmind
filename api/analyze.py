import os
import json
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors()
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body   = json.loads(self.rfile.read(length))
        except Exception:
            self._json(400, {'error': 'Body JSON inválido'})
            return

        image      = body.get('image', '')
        media_type = body.get('mediaType', 'image/jpeg')
        timeframe  = body.get('timeframe', 'M1')
        instrument = body.get('instrument', 'XAU/USD')

        if not image:
            self._json(400, {'error': 'Falta el campo image'})
            return

        api_key = os.environ.get('GEMINI_API_KEY', '')
        if not api_key:
            self._json(500, {'error': 'API key no configurada. Agrega GEMINI_API_KEY en Vercel Environment Variables'})
            return

        prompt = f"""Eres un experto trader que usa Smart Money Concepts (SMC).
Analiza este grafico de {instrument} en timeframe {timeframe}.
Responde SOLO con JSON valido, sin texto extra, sin markdown, sin backticks.
Estructura exacta:
{{"bias":"BULLISH o BEARISH o NEUTRAL","biasDescription":"frase corta","structureTitle":"titulo corto","structureDesc":"2 lineas","entry":"precio entrada","sl":"stop loss","tp":"take profit","rr":"ej 1:3.2","zones":[{{"name":"desc","type":"OB_BULL|OB_BEAR|FVG|SUPPORT|RESISTANCE|LIQUIDITY","price":"nivel"}}],"fullAnalysis":"Analisis 250-350 palabras en espanol: BOS/CHoCH, order blocks, FVGs, liquidez, confluencias, entrada y gestion del trade."}}"""

        payload = json.dumps({
            "contents": [{"parts": [
                {"inline_data": {"mime_type": media_type, "data": image}},
                {"text": prompt}
            ]}],
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 1500}
        }).encode('utf-8')

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'}, method='POST')

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8', errors='ignore')
            try:
                err_msg = json.loads(err_body).get('error', {}).get('message', err_body)
            except Exception:
                err_msg = err_body
            self._json(502, {'error': err_msg})
            return
        except Exception as e:
            self._json(502, {'error': str(e)})
            return

        try:
            raw = data['candidates'][0]['content']['parts'][0]['text']
        except (KeyError, IndexError):
            self._json(500, {'error': 'Respuesta inesperada de Gemini', 'raw': str(data)})
            return

        raw = raw.replace('```json','').replace('```','').strip()

        try:
            analysis = json.loads(raw)
        except Exception:
            self._json(500, {'error': 'Formato inesperado', 'raw': raw})
            return

        self._json(200, {'success': True, 'analysis': analysis})

    def _json(self, code, obj):
        body = json.dumps(obj).encode('utf-8')
        self.send_response(code)
        self._send_cors()
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
