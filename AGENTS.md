# AGENTS.md

Proxy local OpenAI-compatible (FastAPI + httpx) que conecta la extensión Nanobrowser con
OpenCode Go. No hay frontend, base de datos ni CI.

## Comandos

- `uv run python main.py` — inicia el proxy en `127.0.0.1:8080`. Es lo que hace
  `./start_linux.sh`, que prefiere `uv`, luego `.venv`, luego `python3`.
- `uv run --extra test pytest` — suite completa. Los tests mockean httpx: no necesitan red
  ni `OPENCODE_API_KEY`. `pytest-asyncio` está en modo `strict`, así que los tests async
  deben llevar `@pytest.mark.asyncio`.
- `uv run --extra test pytest test_proxy.py::test_session_manager_stability` — un solo test.
- `curl -s http://127.0.0.1:8080/health` — comprobación rápida.
- `docker compose up -d` — requiere `.env`; publica únicamente en `127.0.0.1:8080`.
- `./install_linux_service.sh` — instala el servicio systemd de usuario. Logs:
  `journalctl --user -u opencode-proxy.service -f`.
- No hay lint, formatter, typecheck ni workflows de CI: no inventes comandos para ellos.

## Arquitectura y trampas

- `main.py` contiene la app y todas las rutas; `config.py` carga `.env` con python-dotenv
  (sin sobrescribir variables ya exportadas); `session_manager.py` deriva las sesiones.
  Son módulos top-level, sin layout `src/`; los imports dependen de que el root esté en
  `sys.path`.
- Los endpoints upstream están separados: chat en
  `.../openai/v1/chat/completions` y modelos en `.../go/v1/models`. No los unifiques bajo
  una sola base URL.
- Cada ruta se registra dos veces (`/v1/...` y sin prefijo). Mantén ambas.
- Toda petición a OpenCode Go debe llevar `x-opencode-session: ses_...` y
  `User-Agent: opencode-agent/1.0`; sin ellas el upstream responde 400
  `MissingSessionID` o Cloudflare 1010.
- La sesión debe ser estable entre turnos de una misma tarea (prompt caching): manda el
  header `x-opencode-session`/`x-session-id`; si no existe, se deriva
  `ses_<sha256[:24]>` del primer mensaje `user`. Hay tests que lo verifican.
- Solo se reenvía la API key del cliente si empieza por `oc_sk_`; cualquier otra
  (p. ej. `local`, la que se configura en Nanobrowser) se sustituye por
  `OPENCODE_API_KEY` del `.env`. No simplifiques esta lógica.
- `GET /v1/models/{id}` devuelve un stub estático sin consultar upstream; es intencional
  para el botón "Test models" de Nanobrowser.
- `http_client` es un `httpx.AsyncClient` global en `main`, cerrado en el `lifespan`; los
  tests lo parchean como `main.http_client`. No crees un cliente por petición.
- El CORS abierto es necesario para la extensión; no restrinjas orígenes sin probar
  Nanobrowser.
- Las dependencias runtime están duplicadas en `pyproject.toml` (fuente de `uv`/`uv.lock`)
  y `requirements.txt` (usado por el Dockerfile). Al añadir una, actualiza ambos y
  `uv.lock`.
- El código debe funcionar en Python 3.9+ (evita `X | Y`, `match`, etc.).
- Mantén el bind en loopback: el proxy reenvía credenciales a OpenCode Go.
- `opencode-proxy.service` usa el placeholder `%h/opencode-proxy`; el instalador lo
  sustituye por la ruta real. No hardcodees la ruta en la unit.
- `stop_windows.bat` localiza el proceso por el puerto 8080 hardcodeado; si cambias
  `PROXY_PORT`, actualízalo.
