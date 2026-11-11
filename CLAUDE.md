# Data Nube: reels con avatar

Proyecto de videos cortos de la marca Data Nube (Lima, Perú). Responde siempre en español. Los guiones van en español limeño y la transcripción usa `--language es`.

Estas reglas vienen de las decisiones del usuario hasta el 10 de noviembre de 2026. Si una pide confirmar algo, pregunta antes de gastar dinero.

## Dónde va cada cosa

- Entregables de cada video: `outputs/avatar/<descripcion>-<YYYYMMDD-HHMMSS>/` (ver `CONTRACT.md`). Pruebas: `scratch/`.
- Identidad (avatar, voz, ajustes): `.claude/skills/avatar-reel/identity.json`.
- Keys: en local, `.env` (nunca se sube a git). En la nube, network secrets del entorno: ver `NUBE.md`.

## Avatar y voz

- **Avatar:** siempre el look 2 de HeyGen (`da8e547d52d6412eabd2589473c49ff6`), con Avatar V (`engine.type: avatar_v`), 16:9 y 720p. Mantener el fondo natural de la habitación: no enviar `background` ni `remove_background`.
- **Encuadre del look 2:** es horizontal y en vertical se ve suave. Para la franja de abajo, escalar a 1365x768 y recortar 1080x768 desde x=255 (o 1422x800 desde x=-285 para 1080x800).
- **Costo:** HeyGen cobra de una billetera en dólares sin recarga automática, unos 0.12 USD por segundo (34 s = 3.96, 41 s = 4.94, 47 s = 5.65). Pide confirmación antes de cada render. Si el usuario da un tope, ajusta el guion para cumplirlo.
- **Voz:** ElevenLabs `eleven_v4`, texto a voz directo con la voz clonada "Juanca de Data Nube" (`4URstKpRRZV6Dkdk2zMj`). No usar Gemini ni speech-to-speech. Ajustes aprobados: estabilidad 0.2, similitud 0.75. Tono de noticia: hook con `[surprised]` o `[excited]`, exclamaciones y énfasis. El CTA se escribe "¡Comenta: FONDO!" (con "Comenta... FONDO" se oía "a fondo").
- **Flujo:** guion → verificar datos → un solo audio para aprobar → imágenes → render. Entrega un solo audio, no varias opciones, salvo que lo pida.
- **Hacer cada render una sola vez:** si se corta la sesión, reanudar el `video_id` guardado en `video_create.raw.json`; nunca crear otro.

## Guiones sobre fondos y premios

- **Abrir con la cifra** ("Hasta 150 mil soles…"); el ángulo o el dolor va después.
- **Verificar cada dato** (montos, requisitos, fechas, si la convocatoria está abierta) en fuentes oficiales antes de grabar. Señala lo que no se pudo confirmar.
- **No prometer de más:** decir "hasta", que es un concurso y que el postulante aporta una parte cuando aplique. El usuario prefiere "El jurado elige al ganador. Nosotros preparamos tu postulación." a "no te prometemos que vas a ganar".
- **Afiliación:** si aparece el logo de una institución, incluir "Data Nube no es parte de <institución>".

## Edición vertical (1080x1920)

- **Formato que mejor funcionó:** el simple. Avatar abajo, panel plano arriba con una sola idea grande por pantalla y pocas fotos. El reel "Hasta 150 mil soles" tuvo 4,976 vistas y los más cargados 200 a 900. Proponlo como base y prueba variaciones.
- **Color:** el último aprobado es el morado Data Nube (`#7C3AED`, detalles `#C4A6FF`, texto blanco sobre morado). Antes se usaron amarillo `#FFD60A` y naranja `#EE5A0B`. Confirma la paleta al empezar cada video.
- **Llenar el cuadro:** nada de barras ni áreas vacías. Fotos de borde a borde; bloques de color en los paneles.
- **Zonas seguras de TikTok e Instagram:** texto y logos entre y=280 e y=1400, y fuera de los 140 px de la derecha.
- **Títulos sobre cajas sólidas**, nunca texto con contorno sobre una foto cargada.
- **Logos:** cuando se nombra una marca o institución, su logo real en pantalla, sin redibujarlo ni modificarlo.
- **Fotos:** reales, con licencia `cc0`, `pdm` o `by` (Openverse o Wikimedia). Nunca repetir una foto en el mismo video ni entre videos; revisa los `creditos.txt` de `outputs/`. Evita caras reconocibles cuando se pueda. Muestra las imágenes para aprobar antes de editar, salvo que el usuario pida el video directo.
- **Créditos:** guardar `creditos.txt` en el run y recordar pegarlos en la descripción del post.

## Sonido

- **Efectos en todos los reels**, sobre eventos visuales, nunca sobre palabras: sigue `.claude/skills/sfx-ugc/SKILL.md`. Fuentes: `sfx/`, Openverse (`.claude/skills/openverse/scripts/openverse_sound.py`) y Earshot (`scripts/earshot.sh` en Linux o `scripts\earshot.cmd` en Windows).
- **Música:** Suno vía Kie.ai (`/music-ugc`), instrumental, con ducking bajo la voz (`mix_avatar_reel_audio.py`).
- **Volumen final:** entre -17 y -13 LUFS. Comprobar que la voz se entiende transcribiendo el video final.

## Otros formatos

- **Videos para postular a fondos** (horizontales, para YouTube y evaluadores): sin avatar y sin la voz clonada para clientes. Revisar en las bases del fondo la duración máxima y los puntos obligatorios.
- **Material grabado por el usuario:** pide el original 4K del iPhone; las copias de WhatsApp llegan a 464x832.
