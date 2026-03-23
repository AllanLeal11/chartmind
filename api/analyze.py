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
            body = json.loads(self.rfile.read(length))
        except Exception:
            self._json(400, {'error': 'Body JSON invalido'})
            return

        image = body.get('image', '')
        media_type = body.get('mediaType', 'image/jpeg')
        timeframe = body.get('timeframe', 'M1')
        instrument = body.get('instrument', 'XAU/USD')

        if not image:
            self._json(400, {'error': 'Falta imagen'})
            return

        api_key = os.environ.get('GROQ_API_KEY', '')
        if not api_key:
            self._json(500, {'error': 'Agrega GROQ_API_KEY en Vercel Environment Variables'})
            return

        prompt = f"""Eres experto trader SMC. Analiza el grafico de {instrument} timeframe {timeframe}.
Responde SOLO JSON sin texto extra ni backticks:
{{"bias":"BULLISH o BEARISH o NEUTRAL","biasDescription":"frase corta","structureTitle":"titulo","structureDesc":"2 lineas","entry":"precio","sl":"stop loss","tp":"take profit","rr":"1:3.0","zones":[{{"name":"desc","type":"OB_BULL","price":"nivel"}}],"fullAnalysis":"250 palabras en espanol sobre BOS CHoCH OB FVG liquidez entrada y gestion"}}"""

        payload = json.dumps({
            "model": "llama-3.2-11b-vision-preview",
            "max_tokens": 1500,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{image}"}},
                    {"type": "text", "text": prompt}
                ]
            }]
        }).encode('utf-8')

        req = urllib.request.Request(
            'https://api.groq.com/openai/v1/chat/completions',
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            },
            method='POST'
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            err = e.read().decode('utf-8', errors='ignore')
            try:
                err = json.loads(err).get('error', {}).get('message', err)
            except Exception:
                pass
            self._json(502, {'error': err})
            return
        except Exception as e:
            self._json(502, {'error': str(e)})
            return

        try:
            raw = data['choices'][0]['message']['content']
        except (KeyError, IndexError):
            self._json(500, {'error': 'Respuesta inesperada', 'raw': str(data)})
            return

        raw = raw.replace('json','').replace('','').strip()

        try:
            analysis = json.loads(raw)
        except Exception:
            self._json(500, {'error': 'Formato invalido', 'raw': raw})
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
