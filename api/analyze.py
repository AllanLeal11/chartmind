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

        timeframe  = body.get('timeframe', 'M5')
        instrument = body.get('instrument', 'XAU/USD')

        groq_key    = os.environ.get('GROQ_API_KEY', '')
        td_key      = os.environ.get('TWELVEDATA_API_KEY', '')

        if not groq_key:
            self._json(500, {'error': 'Falta GROQ_API_KEY en Vercel Environment Variables'})
            return
        if not td_key:
            self._json(500, {'error': 'Falta TWELVEDATA_API_KEY en Vercel Environment Variables'})
            return

        # Map timeframe labels to Twelve Data intervals
        tf_map = {
            'M1': '1min', 'M5': '5min', 'M15': '15min',
            'H1': '1h', 'H4': '4h', 'D1': '1day'
        }
        interval = tf_map.get(timeframe, '5min')

        # Map instrument to Twelve Data symbol
        sym_map = {
            'XAU/USD': 'XAU/USD',
            'EUR/USD': 'EUR/USD',
            'BTC/USD': 'BTC/USD',
            'NAS100':  'NDX'
        }
        symbol = sym_map.get(instrument, 'XAU/USD')

        # Fetch candles from Twelve Data
        td_url = (
            f"https://api.twelvedata.com/time_series"
            f"?symbol={symbol}&interval={interval}&outputsize=60"
            f"&apikey={td_key}&format=JSON"
        )

        try:
            with urllib.request.urlopen(td_url, timeout=15) as resp:
                td_data = json.loads(resp.read())
        except Exception as e:
            self._json(502, {'error': f'Error obteniendo datos de mercado: {str(e)}'})
            return

        if 'values' not in td_data:
            msg = td_data.get('message', 'Sin datos de mercado disponibles')
            self._json(502, {'error': msg})
            return

        candles = td_data['values'][:40]  # last 40 candles
        candles.reverse()  # oldest first

        # Format candles as text for the AI
        candle_text = "DateTime | Open | High | Low | Close\n"
        for c in candles:
            candle_text += f"{c['datetime']} | {c['open']} | {c['high']} | {c['low']} | {c['close']}\n"

        current_price = candles[-1]['close']

        prompt = f"""Eres un experto trader que usa Smart Money Concepts (SMC) con amplia experiencia en {instrument}.

Aqui tienes las ultimas 40 velas de {instrument} en timeframe {timeframe}:

{candle_text}

Precio actual: {current_price}

Analiza esta data y responde SOLO con JSON valido, sin texto extra, sin markdown, sin backticks:
{{"bias":"BULLISH o BEARISH o NEUTRAL","biasDescription":"frase corta explicando sesgo","structureTitle":"titulo corto de la estructura (ej: BOS alcista confirmado)","structureDesc":"2 lineas sobre la estructura de mercado","entry":"{current_price}","sl":"precio stop loss sugerido","tp":"precio take profit sugerido","rr":"ratio riesgo-beneficio ej 1:3.0","zones":[{{"name":"descripcion de zona","type":"OB_BULL|OB_BEAR|FVG|SUPPORT|RESISTANCE|LIQUIDITY","price":"nivel de precio"}}],"fullAnalysis":"Analisis completo de 250-300 palabras en espanol: identifica BOS y CHoCH, order blocks validos, FVGs, barridos de liquidez, confluencias, condiciones exactas de entrada, SL y TP con razon del nivel elegido."}}"""

        # Call Groq
        groq_payload = json.dumps({
            "model": "llama-3.3-70b-versatile",
            "max_tokens": 1500,
            "temperature": 0.3,
            "messages": [{"role": "user", "content": prompt}]
        }).encode('utf-8')

        groq_req = urllib.request.Request(
            'https://api.groq.com/openai/v1/chat/completions',
            data=groq_payload,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {groq_key}'
            },
            method='POST'
        )

        try:
            with urllib.request.urlopen(groq_req, timeout=30) as resp:
                groq_data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            err = e.read().decode('utf-8', errors='ignore')
            try:
                err = json.loads(err).get('error', {}).get('message', err)
            except Exception:
                pass
            self._json(502, {'error': f'Error de IA: {err}'})
            return
        except Exception as e:
            self._json(502, {'error': str(e)})
            return

        try:
            raw = groq_data['choices'][0]['message']['content']
        except (KeyError, IndexError):
            self._json(500, {'error': 'Respuesta inesperada de IA', 'raw': str(groq_data)})
            return

        raw = raw.replace('```json', '').replace('```', '').strip()

        try:
            analysis = json.loads(raw)
        except Exception:
            self._json(500, {'error': 'Formato invalido de IA', 'raw': raw})
            return

        analysis['currentPrice'] = current_price
        analysis['symbol'] = symbol
        analysis['interval'] = interval
        analysis['candlesAnalyzed'] = len(candles)

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
