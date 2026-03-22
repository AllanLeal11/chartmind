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

        api_key = os.environ.get('ANTHROPIC_API_KEY', '')
        if not api_key:
            self._json(500, {'error': 'API key no configurada en Vercel Environment Variables'})
            return

        prompt = f"""Eres un experto trader que usa Smart Money Concepts (SMC).
Analiza este gráfico de {instrument} en timeframe {timeframe}.

Responde SOLO con un objeto JSON válido, sin texto extra, sin markdown, sin backticks.
Usa esta estructura exacta:

{{
  "bias": "BULLISH o BEARISH o NEUTRAL",
  "biasDescription": "frase corta de 1 línea explicando el sesgo",
  "structureTitle": "título corto de la estructura",
  "structureDesc": "2 líneas sobre la estructura de mercado visible",
  "entry": "precio o zona de entrada sugerida",
  "sl": "precio stop loss",
  "tp": "precio take profit",
  "rr": "ratio riesgo-beneficio (ej: 1:3.2)",
  "zones": [
    {{"name": "descripción", "type": "OB_BULL|OB_BEAR|FVG|SUPPORT|RESISTANCE|LIQUIDITY", "price": "nivel aproximado"}}
  ],
  "fullAnalysis": "Análisis completo de 250-350 palabras en español sobre estructura BOS/CHoCH, order blocks, FVGs, liquidez, confluencias, condiciones de entrada y gestión del trade."
}}"""

        payload = json.dumps({
            'model': 'claude-sonnet-4-20250514',
            'max_tokens': 1200,
            'messages': [{
                'role': 'user',
                'content': [
                    {'type': 'image', 'source': {'type': 'base64', 'media_type': media_type, 'data': image}},
                    {'type': 'text', 'text': prompt}
                ]
            }]
        }).encode('utf-8')

        req = urllib.request.Request(
            'https://api.anthropic.com/v1/messages',
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01'
            },
            method='POST'
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            err = json.loads(e.read()).get('error', {}).get('message', str(e))
            self._json(502, {'error': err})
            return
        except Exception as e:
            self._json(502, {'error': str(e)})
            return

        raw = data.get('content', [{}])[0].get('text', '')
        raw = raw.replace('```json', '').replace('```', '').strip()

        try:
            analysis = json.loads(raw)
        except Exception:
            self._json(500, {'error': 'Respuesta inesperada de la IA', 'raw': raw})
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
