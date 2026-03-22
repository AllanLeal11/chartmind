<?php
/**
 * ChartMind - Backend PHP
 * La API key se lee desde una variable de entorno de Vercel.
 * NUNCA pongas la key directamente en este archivo.
 *
 * En Vercel: Settings → Environment Variables → ANTHROPIC_API_KEY
 */

// Lee la key desde variable de entorno (configurada en Vercel)
$apiKey = getenv('ANTHROPIC_API_KEY');

if (!$apiKey) {
    http_response_code(500);
    echo json_encode(['error' => 'API key no configurada. Ve a Vercel → Settings → Environment Variables y agrega ANTHROPIC_API_KEY']);
    exit;
}

define('ANTHROPIC_API_KEY', $apiKey);

// Seguridad: solo acepta peticiones POST desde tu propio dominio
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *'); // Cambia * por tu dominio en producción
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Method not allowed']);
    exit;
}

// Leer el body JSON
$input = file_get_contents('php://input');
$body  = json_decode($input, true);

if (!$body || !isset($body['image'], $body['timeframe'], $body['instrument'])) {
    http_response_code(400);
    echo json_encode(['error' => 'Faltan datos: image, timeframe, instrument']);
    exit;
}

$imageBase64  = $body['image'];
$timeframe    = htmlspecialchars($body['timeframe']);
$instrument   = htmlspecialchars($body['instrument']);
$mediaType    = isset($body['mediaType']) ? $body['mediaType'] : 'image/jpeg';

// Validar que sea una imagen base64 razonable (máx ~8MB)
if (strlen($imageBase64) > 11000000) {
    http_response_code(413);
    echo json_encode(['error' => 'Imagen demasiado grande. Máximo 8MB.']);
    exit;
}

// Prompt SMC
$prompt = <<<PROMPT
Eres un experto trader que usa Smart Money Concepts (SMC) con años de experiencia en {$instrument}.
Analiza este gráfico de {$instrument} en timeframe {$timeframe}.

Responde SOLO con un objeto JSON válido, sin texto extra, sin markdown, sin backticks.
Usa esta estructura exacta:

{
  "bias": "BULLISH o BEARISH o NEUTRAL",
  "biasDescription": "frase corta de 1 línea explicando el sesgo",
  "structureTitle": "título corto de la estructura (ej: BOS alcista + CHoCH confirmado)",
  "structureDesc": "2 líneas sobre la estructura de mercado visible",
  "entry": "precio o zona de entrada sugerida",
  "sl": "precio stop loss",
  "tp": "precio take profit",
  "rr": "ratio riesgo-beneficio (ej: 1:3.2)",
  "zones": [
    {"name": "descripción", "type": "OB_BULL|OB_BEAR|FVG|SUPPORT|RESISTANCE|LIQUIDITY", "price": "nivel aproximado"}
  ],
  "fullAnalysis": "Análisis completo de 250-350 palabras en español. Describe: estructura (BOS/CHoCH), order blocks identificados, FVGs, barridos de liquidez, confluencias, condiciones exactas de entrada y gestión del trade."
}
PROMPT;

// Construir payload para Anthropic
$payload = [
    'model'      => 'claude-sonnet-4-20250514',
    'max_tokens' => 1200,
    'messages'   => [
        [
            'role'    => 'user',
            'content' => [
                [
                    'type'   => 'image',
                    'source' => [
                        'type'       => 'base64',
                        'media_type' => $mediaType,
                        'data'       => $imageBase64
                    ]
                ],
                [
                    'type' => 'text',
                    'text' => $prompt
                ]
            ]
        ]
    ]
];

// Llamada a la API de Anthropic con cURL
$ch = curl_init('https://api.anthropic.com/v1/messages');
curl_setopt_array($ch, [
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_POST           => true,
    CURLOPT_POSTFIELDS     => json_encode($payload),
    CURLOPT_TIMEOUT        => 60,
    CURLOPT_HTTPHEADER     => [
        'Content-Type: application/json',
        'x-api-key: ' . ANTHROPIC_API_KEY,
        'anthropic-version: 2023-06-01'
    ]
]);

$response   = curl_exec($ch);
$httpStatus = curl_getinfo($ch, CURLINFO_HTTP_CODE);
$curlError  = curl_error($ch);
curl_close($ch);

if ($curlError) {
    http_response_code(502);
    echo json_encode(['error' => 'No se pudo conectar con la IA: ' . $curlError]);
    exit;
}

$data = json_decode($response, true);

if ($httpStatus !== 200 || !isset($data['content'][0]['text'])) {
    http_response_code(502);
    $msg = isset($data['error']['message']) ? $data['error']['message'] : 'Error desconocido de la API';
    echo json_encode(['error' => $msg]);
    exit;
}

// Limpiar y parsear la respuesta JSON del modelo
$raw   = $data['content'][0]['text'];
$raw   = preg_replace('/```json|```/', '', $raw);
$raw   = trim($raw);
$parsed = json_decode($raw, true);

if (!$parsed) {
    http_response_code(500);
    echo json_encode(['error' => 'La IA devolvió un formato inesperado. Intenta de nuevo.', 'raw' => $raw]);
    exit;
}

// Éxito — devolver el análisis al frontend
echo json_encode(['success' => true, 'analysis' => $parsed]);
exit;
?>
