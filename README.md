# OpenCode Go Compatibility Proxy for Nanobrowser

Un proxy local ligero, robusto y multiplataforma (Windows y Linux) diseñado para conectar la extensión de navegación **[Nanobrowser](https://github.com/nanobrowser/nanobrowser)** con tu suscripción de **[OpenCode Go](https://opencode.ai/docs/go/)**, permitiendo utilizar modelos como `deepseek-v4.1-flash` para tareas de navegación autónoma web.

---

## 1. Contexto: ¿Por qué fue necesario desarrollar esta solución?

Al intentar conectar Nanobrowser directamente a OpenCode Go como un proveedor OpenAI genérico, surgen tres problemas arquitectónicos que impiden el funcionamiento directo:

### A. Requisito obligatorio de `x-opencode-session` (Error 400)
OpenCode Go está optimizado para flujos de agentes y reutilización de caché de contexto (*prompt caching*). Por ello, exige obligatoriamente que cada petición incluya la cabecera HTTP:
```http
x-opencode-session: ses_<identificador_de_sesion>
```
Si esta cabecera no se envía, OpenCode Go rechaza la solicitud de inmediato antes de procesar el modelo o las herramientas:
```json
HTTP 400 Bad Request
{
  "type": "error",
  "error": {
    "type": "MissingSessionID",
    "message": "Request is missing x-opencode-session and cannot be routed efficiently. Please see https://opencode.ai/docs/go/#where-can-i-use-it"
  }
}
```
**Limitación en Nanobrowser:** La interfaz de configuración de proveedores OpenAI compatibles de Nanobrowser únicamente permite ingresar `Server address (Base URL)`, `API Key` y `Model Name`. No dispone de campos para configurar cabeceras HTTP personalizadas.

### B. Rutas divididas (*Endpoint Path Mismatch* y Error 404)
El SDK de OpenAI utilizado por Nanobrowser (`@ai-sdk/openai`) asume que todas las rutas cuelgan de un prefijo común:
* Chat Completions: `${baseURL}/chat/completions`
* Listado de modelos: `${baseURL}/models`
* Metadatos del modelo: `${baseURL}/models/${modelId}`

Sin embargo, en OpenCode Go los endpoints oficiales documentados están desacoplados:
* **Chat Completions:** `https://opencode.ai/inference/go/openai/v1/chat/completions`
* **Listado de Modelos:** `https://opencode.ai/inference/go/v1/models`

Un cliente estándar que apunte a una sola URL base terminará concatenando rutas inválidas y recibiendo errores `404 Not Found`.

### C. Bloqueo de WAF / User-Agent (Error Cloudflare 1010)
Cloudflare y OpenCode bloquean User-Agents genéricos o de librerías HTTP por defecto (código 1010). Se requiere un User-Agent que identifique adecuadamente al agente (por ejemplo, `opencode-agent/1.0`).

---

## 2. ¿Cómo soluciona esto el Proxy?

Este proxy actúa como un puente de compatibilidad transparente:
1. **Unificación de Endpoints:** Expone una única URL base compatible (`http://127.0.0.1:8080/v1`) y enruta:
   * `GET /v1/models` y `GET /v1/models/{model_id}` &rarr; `https://opencode.ai/inference/go/v1/models`
   * `POST /v1/chat/completions` &rarr; `https://opencode.ai/inference/go/openai/v1/chat/completions`
2. **Gestión Determinista de Sesiones:** Analiza el mensaje raíz de la tarea del usuario y deriva un ID de sesión estable (`ses_<sha256>`). Así, una tarea compleja de navegación de 20 pasos mantiene la misma sesión en OpenCode Go, optimizando el costo y la caché de tokens.
3. **Soporte Completo de Streaming (SSE) y Tool Calling:** Pasa íntegras las llamadas a herramientas estructuradas de Nanobrowser (`report_status`, clics, formularios) y retransmite eventos Server-Sent Events (`text/event-stream`) con baja latencia.
4. **Seguridad:** Escucha únicamente en `127.0.0.1:8080` y no filtra credenciales en logs ni respuestas.

---

## 3. Configuración en Nanobrowser

1. Abre el panel de **Nanobrowser** en tu navegador (Brave, Chrome o Edge).
2. Ve a **Settings > Models / Providers**.
3. Añade un nuevo proveedor con los siguientes datos:

| Parámetro | Valor exacto |
| :--- | :--- |
| **Provider Type** | `Custom (OpenAI-compatible)` |
| **Provider Name** | `OpenCode Go Proxy` |
| **Server address (Base URL)** | `http://127.0.0.1:8080/v1` |
| **API Key** | `local` *(el proxy inyectará tu clave real desde el `.env`)* |
| **Model Name** | `deepseek-v4.1-flash` |

4. Pulsa **Add** y luego **Test models** (o el botón de verificación junto a `deepseek-v4.1-flash`). Aparecerá en **verde**:
   `"Connected. The model called the test tool"`
5. En la sección de agentes, asigna `deepseek-v4.1-flash` tanto a **Planner** como a **Navigator**.

---

## 4. Despliegue y Autostart en Windows

### A. Ejecución manual
* **Primer plano:** Doble clic en `start_windows.bat`.
* **Segundo plano (sin ventana negra):** Doble clic en `start_windows_background.vbs`.

### B. Inicio automático con el encendido de Windows
El instalador coloca un script en tu carpeta de inicio de Windows:
`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\opencode_proxy_startup.vbs`

Para configurarlo o verificarlo:
```powershell
# Comprobar que el proxy responde
curl.exe http://127.0.0.1:8080/health
```

---

## 5. Despliegue y Autostart en Linux (Para entornos de trabajo / servidores)

### A. Requisitos previos
Python 3.10+ y `uv` (o `python3-venv` / `pip`).

```bash
# Clonar el repositorio
git clone https://github.com/laar19/opencode-nanobrowser-proxy.git
cd opencode-nanobrowser-proxy

# Configurar variables de entorno (.env)
cp .env.example .env
nano .env  # Añadir tu OPENCODE_API_KEY
```

> **Alternativa sin archivo .env:** Puedes exportar la variable en tu entorno global (`~/.bashrc`):
> ```bash
> export OPENCODE_API_KEY="oc_sk_tu_clave_aqui"
> ```

### B. Ejecución manual
```bash
chmod +x start_linux.sh
./start_linux.sh
```

### C. Inicio automático al encender el sistema (systemd user service)
El proyecto incluye un instalador automático para `systemd`:
```bash
chmod +x install_linux_service.sh start_linux.sh
./install_linux_service.sh
```

Comandos útiles de gestión en Linux:
```bash
# Ver estado del servicio
systemctl --user status opencode-proxy.service

# Ver logs en vivo
journalctl --user -u opencode-proxy.service -f

# Detener o reiniciar
systemctl --user restart opencode-proxy.service
systemctl --user stop opencode-proxy.service
```

---

## 6. Pruebas Automatizadas

Para validar que el proxy funciona correctamente de extremo a extremo:
```bash
uv run --with fastapi --with uvicorn --with httpx --with pytest --with pytest-asyncio --with python-dotenv python -m pytest test_proxy.py
```

---

## 7. Contribución a la Comunidad Upstream (Nanobrowser)

Hemos abierto el **Issue oficial [#367](https://github.com/nanobrowser/nanobrowser/issues/367)** en el repositorio oficial de Nanobrowser exponiendo la limitación actual del proveedor `openai-compatible` (ausencia de soporte para cabeceras HTTP arbitrarias como `x-opencode-session`), proponiendo los cambios exactos en `src/llm/providers.ts` (`ModelSpec.headers` y paso de cabeceras a `@ai-sdk/openai`) y ofreciendo este proxy como solución funcional inmediata para la comunidad.
