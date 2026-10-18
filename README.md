# OpenCode Go Compatibility Proxy for Nanobrowser

A lightweight, cross-platform compatibility proxy bridging [Nanobrowser](https://github.com/nanobrowser) with [OpenCode Go](https://opencode.ai/docs/go/).

---

## 1. Características

- **Enrutamiento Inteligente**:
  - `GET /v1/models` y `GET /v1/models/{model_id}` &rarr; `https://opencode.ai/inference/go/v1/models`
  - `POST /v1/chat/completions` &rarr; `https://opencode.ai/inference/go/openai/v1/chat/completions`
- **Gestión Determinista de Sesiones**:
  - Inyecta automáticamente `x-opencode-session: ses_<hash>` derivado del mensaje raíz del usuario para optimizar el *prompt caching* de OpenCode Go y mantener sesiones estables entre pasos del agente.
- **Soporte Completo de Streaming (SSE)**:
  - Manejo de flujo en tiempo real (`text/event-stream`) requerido por Nanobrowser.
- **Multiplataforma (Windows y Linux)**:
  - Scripts de inicio en segundo plano para Windows y servicio `systemd` para Linux.
- **Seguridad**:
  - Escucha exclusivamente en `127.0.0.1:8080`.
  - Sin SSRF ni exposición de claves en logs o respuestas.

---

## 2. Configuración (`.env`)

Crea un archivo `.env` en la raíz del proyecto (basado en `.env.example`):

```ini
OPENCODE_API_KEY=oc_sk_your_key_here
PROXY_HOST=127.0.0.1
PROXY_PORT=8080
OPENCODE_CHAT_ENDPOINT=https://opencode.ai/inference/go/openai/v1/chat/completions
OPENCODE_MODELS_ENDPOINT=https://opencode.ai/inference/go/v1/models
DEFAULT_MODEL=deepseek-v4.1-flash
LOG_LEVEL=INFO
```

> **Nota:** Puedes configurar `OPENCODE_API_KEY` directamente como variable de entorno del sistema o en este archivo `.env`.

---

## 3. Uso en Linux (Trabajo / Servidor)

### Opción A: Iniciar manualmente
```bash
chmod +x start_linux.sh
./start_linux.sh
```

### Opción B: Iniciar automáticamente al encender el equipo (systemd)
Para que el proxy se ejecute como servicio de usuario al iniciar sesión:
```bash
chmod +x install_linux_service.sh
./install_linux_service.sh
```
Comandos útiles de systemd:
```bash
# Ver estado del servicio
systemctl --user status opencode-proxy.service

# Ver logs en tiempo real
journalctl --user -u opencode-proxy.service -f

# Detener o reiniciar
systemctl --user stop opencode-proxy.service
systemctl --user restart opencode-proxy.service
```

---

## 4. Uso en Windows

### Iniciar en primer plano:
Doble clic en `start_windows.bat`.

### Iniciar en segundo plano (sin ventana de consola):
Doble clic en `start_windows_background.vbs`.

### Inicio automático con Windows:
El archivo `opencode_proxy_startup.vbs` ya se encuentra configurado en tu carpeta de inicio:
`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`

---

## 5. Configuración en Nanobrowser

1. Abre Nanobrowser en tu navegador y ve a **Settings > Models / Providers**.
2. Añade un nuevo proveedor con:
   - **Provider Type**: `Custom (OpenAI-compatible)`
   - **Provider Name**: `OpenCode Go Proxy`
   - **Server address (Base URL)**: `http://127.0.0.1:8080/v1`
   - **API key**: `local` (o tu clave `oc_sk_...`)
   - **Model Name**: `deepseek-v4.1-flash`
3. Haz clic en **Add** y luego en **Test models**.
4. Configura tanto el rol **Planner** como **Navigator** con `deepseek-v4.1-flash`.

---

## 6. Pruebas Automatizadas

```bash
uv run --with fastapi --with uvicorn --with httpx --with pytest --with pytest-asyncio --with python-dotenv python -m pytest test_proxy.py
```
