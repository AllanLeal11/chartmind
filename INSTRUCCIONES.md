# ChartMind — Instrucciones de Instalación

## ¿Qué incluye este paquete?
```
chartmind/
├── index.html        ← Frontend (la app que ve el usuario)
└── api/
    └── analyze.php   ← Backend (conecta con la IA, oculta tu API key)
```

---

## PASO 1 — Obtén tu API Key de Anthropic
1. Ve a https://console.anthropic.com
2. Crea una cuenta o inicia sesión
3. Ve a "API Keys" → "Create Key"
4. Copia la key (empieza con `sk-ant-...`)

---

## PASO 2 — Configura el backend
Abre el archivo `api/analyze.php` con cualquier editor de texto (Notepad, VS Code, etc.)

Busca esta línea:
```
define('ANTHROPIC_API_KEY', 'sk-ant-XXXXXXXXXXXXXXXXXXXXXXXX');
```

Reemplaza `sk-ant-XXXXXXXXXXXXXXXXXXXXXXXX` con tu API key real. Guarda el archivo.

---

## PASO 3 — Sube los archivos al hosting

### Opción A — GoDaddy (cPanel Hosting)
1. Entra a tu cuenta GoDaddy → "My Products" → "Web Hosting" → "Manage"
2. Busca **cPanel** y entra
3. Ve a **File Manager** → carpeta `public_html`
4. Sube la carpeta completa `chartmind/` (o su contenido directamente en `public_html`)
5. Asegúrate de que la estructura sea:
   ```
   public_html/
   ├── index.html
   └── api/
       └── analyze.php
   ```
6. Tu app estará en: `https://tudominio.com`

### Opción B — Hostinger
1. Entra a hPanel → "File Manager" → `public_html`
2. Sube igual que GoDaddy
3. Funciona con PHP 7.4+ (todos los planes lo soportan)

### Opción C — SiteGround / Bluehost / NameCheap
- Mismo proceso: File Manager → public_html → subir archivos
- Todos soportan PHP con cURL habilitado (requerido)

### Opción D — FTP (cualquier hosting)
Usa FileZilla (gratis):
1. Host: `ftp.tudominio.com`
2. Usuario y contraseña: los del hosting
3. Sube a `/public_html/`

---

## PASO 4 — Verificar que funciona
1. Abre `https://tudominio.com` en el navegador
2. Sube una captura de chart
3. Selecciona timeframe e instrumento
4. Haz click en "Analizar con IA"

---

## Requisitos del hosting (todos los hostings comunes los cumplen)
- PHP 7.4 o superior ✅
- cURL habilitado ✅ (viene por defecto en casi todos)
- HTTPS recomendado (GoDaddy/Hostinger lo incluyen gratis con SSL)

---

## Costos estimados de la API
- Claude Sonnet: ~$0.003 por análisis (menos de medio centavo)
- Con 500 análisis/mes = ~$1.50 en costos de API
- Con 5,000 análisis/mes = ~$15 en costos de API

---

## Próximos pasos sugeridos
- Agregar sistema de login + créditos (Stripe)
- Limitar uso por IP para evitar abuso
- Agregar dominio personalizado

---

**Soporte:** Si algo no funciona, verifica que el archivo `.php` tiene tu API key correcta y que el hosting tiene cURL habilitado.
