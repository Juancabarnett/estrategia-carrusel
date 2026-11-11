# Cómo usar este proyecto en Claude Code en la nube

Guía paso a paso para configurar el entorno en claude.ai/code. Solo se hace una vez.

## 1. Abre el entorno

En claude.ai/code, elige este repositorio y entra a la configuración del entorno (el selector de entorno, luego editar).

## 2. Carga tus keys como "network secrets"

No uses "Environment variables" para las keys: cualquiera con acceso al entorno las puede leer. Usa **network secrets**, que inyectan la key en cada llamada sin que entre a la máquina.

| Servicio | Dominio | Encabezado | Prefijo |
|---|---|---|---|
| HeyGen | `api.heygen.com` y `upload.heygen.com` | `x-api-key` | ninguno |
| ElevenLabs | `api.elevenlabs.io` | `xi-api-key` | ninguno |
| Kie.ai (música) | `api.kie.ai` | `Authorization` | `Bearer` |

`AVATAR_GROUP_ID` y `AVATAR_LOOK_ID` no son secretos: pueden ir en "Environment variables".

**Prueba:** en la primera sesión pide a Claude que haga una consulta de saldo a cada servicio. Si alguna falla, los scripts quizás necesiten un ajuste para no mandar el encabezado vacío.

## 3. Permite los dominios

En "Network access" elige **Limited** y agrega en "Allowed domains":

```text
api.heygen.com
upload.heygen.com
resource2.heygen.ai
*.heygen.ai
api.elevenlabs.io
api.kie.ai
*.kie.ai
api.openverse.org
*.freesound.org
commons.wikimedia.org
upload.wikimedia.org
live.staticflickr.com
cdn.jsdelivr.net
```

GitHub, npm, PyPI y `*.googleapis.com` ya vienen permitidos. Los resultados de Suno se descargan de dominios que pueden cambiar: si una descarga falla, agrega el dominio que aparezca en el error.

## 4. Pega el script de arranque

Copia el contenido de `cloud/setup.sh` en el campo "Setup script". Instala FFmpeg y las librerías de Python, y prepara HyperFrames.

## 5. Cómo obtener tus videos

En la nube no hay botón de descarga. Pide a Claude que suba el `final.mp4` a una rama y luego lo bajas desde GitHub. Los archivos `.mp4` y `.wav` están en `.gitignore` para no inflar el repositorio, así que esa subida se pide de forma explícita.

## Diferencias con tu PC

- La máquina es Linux, no Windows: usa `scripts/earshot.sh` en lugar de `scripts\earshot.cmd`.
- Tus notas y reglas viajan en `CLAUDE.md`; lo que guardes en otra sesión local no llega solo.
- Recursos: 4 CPU, 16 GB de RAM, sin GPU. Los renders tardan más que en tu PC.
- El modelo local de transcripción (Parakeet) se descarga la primera vez que se usa.
