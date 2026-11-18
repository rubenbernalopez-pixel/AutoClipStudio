# AutoClip Studio

**Generador de clips de pódcast para Instagram Reels, TikTok y YouTube Shorts**

Versión 1.0.0 | Windows 11 (64 bits) | Español (España)

---

## 🎯 ¿Qué hace AutoClip Studio?

AutoClip Studio automatiza la creación de clips verticales a partir de episodios de pódcast:

1. **Pegas una URL** de YouTube (pública o compartida)
2. **La app descarga** el vídeo y extrae el audio
3. **Whisper transcribe** con timestamps por palabra (precisión ~95% en español)
4. **IA selecciona** los mejores momentos (preguntas+respuestas, confesiones, anécdotas, decisiones)
5. **Renderiza clips** verticales 9:16 con layout elegido
6. **Genera subtítulos karaoke** (amarillo→verde) sincronizados palabra por palabra
7. **Tú revisas, corriges y exportas** MP4 listos para publicar

---

## 🎨 Layouts disponibles

| Layout | Vista | Uso recomendado |
|--------|-------|-----------------|
| **Solo pódcast** | Pantalla completa | Entrevistas, monólogos, máxima fidelidad |
| **Pelotas y aros** | 55% pódcast / 45% animación | Contenido entretenido, retención visual |
| **Parkour de bloques** | 55% pódcast / 45% animación | Audiencia gaming/tech, estilo Minecraft |
| **Mi gameplay** | 55% pódcast / 45% tu vídeo | Creators con grabaciones propias de Minecraft |

---

## 📦 Qué incluye el ZIP

```
AutoClipStudio_v1.0.0_win-x64.zip
├── AutoClipStudio.exe              # Aplicación principal
├── AutoClipStudio.Core.dll         # Núcleo compartido
├── *.dll                           # Dependencias .NET
├── appsettings.json                # Configuración
├── Python/
│   └── auto_clip_studio/           # Backend Python completo
│       ├── main.py                 # Entry point JSON-RPC
│       ├── models/                 # Modelos de datos
│       ├── services/               # Servicios (download, transcribe, select, render, subtitles)
│       └── utils/                  # Config, logging
├── Assets/
│   ├── backgrounds/                # Vídeos de fondo incluidos
│   │   ├── balls_hoops.mp4         # Pelotas escapando de aros (30s, loop)
│   │   ├── balls_hoops_thumb.jpg
│   │   ├── block_parkour.mp4       # Parkour de bloques (30s, loop)
│   │   └── block_parkour_thumb.jpg
│   ├── fonts/                      # Tipografías
│   │   ├── Inter-VariableFont.ttf
│   │   └── JetBrainsMono-VariableFont.ttf
│   └── icons/                      # Iconos de la app
└── docs/
    └── USER_GUIDE.md               # Guía completa de usuario
```

---

## 🚀 Instalación rápida

### Opción A: Instalador (recomendado)
1. Descarga `AutoClipStudio_Setup.exe` (incluye .NET 8, VC++, Python, FFmpeg)
2. Ejecuta como administrador
3. Sigue el asistente
4. ¡Listo!

### Opción B: Portable (ZIP)
1. Descomprime `AutoClipStudio_v1.0.0_win-x64.zip` en una carpeta
2. **Requisitos previos** (instálalos tú si no los tienes):
   - [.NET 8 Desktop Runtime](https://dotnet.microsoft.com/download/dotnet/8.0)
   - [Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)
   - [Python 3.11+](https://python.org/downloads) (opcional, hay uno embebido)
   - [FFmpeg](https://ffmpeg.org/download.html) en PATH
3. Ejecuta `AutoClipStudio.exe`

### Primer uso
- Al abrir por primera vez, se descarga **Whisper large-v3 (~1.5 GB)**
- Espacio necesario: **~3-5 GB** total tras primera transcripción
- Carpetas creadas:
  - `Documentos\AutoClipStudio\Clips\` → tus MP4 finales
  - `%TEMP%\AutoClipStudio\` → archivos temporales
  - `%LOCALAPPDATA%\AutoClipStudio\` → config y logs

---

## 🎬 Crear tu primer clip (30 segundos)

1. **Abre la app** → verás "Pega la URL del episodio"
2. **Pega URL** de YouTube: `https://youtube.com/watch?v=...` o `https://youtu.be/...`
3. **Opcional**: Escribe un tema: *"cuando cuenta por qué cerró la tienda"*
4. **Pulsa "Generar clips"**
5. **Espera** (2-5 min según duración): verás progreso en tiempo real
6. **Revisa resultados**: tarjetas con vídeo, puntuación, gancho, texto para redes
7. **Pulsa "Revisar subtítulos"** si quieres corregir palabras
8. **Pulsa "Copiar publicación"** → pega en Instagram/TikTok/YouTube
9. **Pulsa "Exportar"** → MP4 con subtítulos quemados en `Documentos\AutoClipStudio\Clips\`

---

## ✏️ Editor de subtítulos (clave)

El editor muestra **karaoke real** sincronizado con el audio:

- 🟡 **Amarillo** = palabra sonando AHORA
- 🟢 **Verde** = ya pronunciada
- ⚪ **Blanco** = pendiente
- 🔴 **Coral** = corregida por ti
- ⚠ **Ámbar** = baja confianza (revisar)

**Para corregir**: Click en palabra → escribe lo correcto → ajusta desfase (± seg) → Aplicar
**Para verificar**: "▶ Desde aquí" reproduce el vídeo desde esa palabra exacta

---

## ⚙️ Ajustes importantes

| Ajuste | Recomendación |
|--------|---------------|
| **Modelo Whisper** | `large-v3` (mejor precisión) / `medium` (más rápido, buena precisión) |
| **Máx. clips** | 3 (calidad > cantidad) |
| **Máx. duración** | 75s (ideal para Reels/Shorts) |
| **Layout** | Solo pódcast para entrevistas; Pelotas/Parkour para engagement |
| **Dispositivo Whisper** | Auto (usa GPU NVIDIA si hay) / CPU si falla |
| **Precisión** | float16 (GPU) / int8 (CPU) |

---

## 🐛 Problemas comunes

| Problema | Solución |
|----------|----------|
| "Python no encontrado" | Usa el instalador completo o instala Python 3.11+ |
| "FFmpeg no encontrado" | Instala FFmpeg y añade a PATH, o usa instalador |
| Descarga YouTube falla | URL debe ser pública. Prueba en navegador primero |
| Transcripción lenta | Usa modelo `medium` o `small`; GPU acelera 10x |
| Subtítulos desincronizados | Editor: corrige palabra + ajusta "desfase temporal" |
| Incluye promo final | Editor: marca rango a excluir o recorta timecode final |
| Error CUDA / poca VRAM | Ajustes → Dispositivo: `cpu`, Precisión: `int8` |

---

## 📄 Licencia

**AutoClip Studio** - Copyright © 2024 AutoClip Studio Team

### Tecnologías
- WPF / .NET 8 - UI nativa Windows
- faster-whisper (CTranslate2) - Transcripción ultrarrápida
- yt-dlp - Descarga robusta de YouTube
- FFmpeg - Procesamiento vídeo/audio profesional
- MaterialDesign / Wpf.Ui - Controles modernos
- Inter Font / JetBrains Mono - Tipografías

### Assets incluidos
- Animaciones procedurales generadas: "Pelotas escapando de aros" y "Parkour de bloques"
- Funcionan offline, sin atribuciones requeridas

---

## 📞 Soporte

- **Guía completa**: `docs/USER_GUIDE.md` (en el ZIP)
- **Issues**: GitHub Issues
- **Email**: soporte@autoclipstudio.com

---

## 🔧 Para desarrolladores

### Compilar desde fuente
```powershell
# Requisitos: .NET 8 SDK, WiX Toolset v4, Python 3.11+
.\build.ps1 -Configuration Release -CreateInstaller
```

### Estructura del proyecto
```
AutoClipStudio.sln
├── src/
│   ├── AutoClipStudio.WPF/     # Frontend WPF (C#)
│   ├── AutoClipStudio.Core/    # Modelos compartidos
│   └── AutoClipStudio.Python/  # Backend (Python)
├── installer/
│   └── AutoClipStudio.Setup/   # WiX Installer
├── assets/                     # Backgrounds, fonts, icons
├── docs/                       # Documentación
└── build.ps1                   # Script de build completo
```

### Arquitectura
- **WPF** ↔ **Python** via JSON-RPC sobre stdin/stdout
- Proceso Python hijo, comunicación asíncrona
- Todo empaquetado: sin dependencias externas en runtime

---

*AutoClip Studio v1.0.0 - Noviembre 2024*
*Hecho con ❤️ para creadores de pódcast en español*