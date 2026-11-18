# AutoClip Studio - Guía de Usuario

**Versión 1.0.0** | Windows 11 (64 bits) | Español (España)

---

## 📋 Índice

1. [Instalación y primer uso](#instalación-y-primer-uso)
2. [Crear tu primer clip](#crear-tu-primer-clip)
3. [Interfaz principal](#interfaz-principal)
4. [Revisar y editar clips](#revisar-y-editar-clips)
5. [Editor de subtítulos](#editor-de-subtítulos)
6. [Exportar y publicar](#exportar-y-publicar)
7. [Configuración](#configuración)
8. [Solución de problemas](#solución-de-problemas)
9. [Especificaciones técnicas](#especificaciones-técnicas)

---

## 🚀 Instalación y primer uso

### Requisitos del sistema
- **Windows 11** (64 bits) o Windows 10 (versión 1909+)
- **4 GB RAM** mínimo (8 GB recomendados)
- **5 GB espacio libre** en disco (para modelos, assets y archivos temporales)
- Conexión a Internet (para descargar el modelo de Whisper en el primer uso)

### Instalación
1. Ejecuta `AutoClipStudio_Setup.exe`
2. El instalador comprobará e instalará automáticamente:
   - **.NET 8 Desktop Runtime** (si no está presente)
   - **Visual C++ Redistributable** (si no está presente)
3. Sigue el asistente de instalación
4. Al finalizar, marca "Ejecutar AutoClip Studio" y pulsa Finalizar

### Primer inicio
Al abrir la aplicación por primera vez:
1. Se descargará el **modelo Whisper large-v3** (~1.5 GB) - solo ocurre una vez
2. Se crearán las carpetas de trabajo en:
   - **Clips generados**: `Documentos\AutoClipStudio\Clips\`
   - **Archivos temporales**: `%TEMP%\AutoClipStudio\`
   - **Configuración**: `%LOCALAPPDATA%\AutoClipStudio\`

---

## 🎬 Crear tu primer clip

### Paso 1: Pegar la URL
1. Abre AutoClip Studio
2. En la pantalla principal, verás un campo grande: **"Pega la URL del episodio"**
3. Copia y pega una URL de YouTube:
   - ✅ `https://www.youtube.com/watch?v=abc123`
   - ✅ `https://youtu.be/abc123`
   - ✅ URLs de YouTube Shorts
   - ✅ Páginas de episodios con reproductor compatible
4. Opcional: Escribe un **tema** para guiar la selección (ej: *"cuando cuenta por qué cerró la tienda"*)

### Paso 2: Ajustes (opcional)
Pulsa **"Ajustes avanzados"** para modificar:
- **Máx. clips**: 1-5 (por defecto: 3)
- **Máx. duración**: 30-90 segundos (por defecto: 75s)
- **Modelo Whisper**: tiny/base/small/medium/large-v3 (por defecto: large-v3)
- **Layout**: Solo pódcast / Pelotas y aros / Parkour de bloques / Mi gameplay
- **Fondo animado**: Para layouts de pantalla dividida

### Paso 3: Generar
Pulsa **"Generar clips"**. Verás el progreso en tiempo real:
1. 📥 **Descargando** - Descarga vídeo y extrae audio (16 kHz mono)
2. 🎙️ **Transcribiendo** - Whisper transcribe con timestamps por palabra
3. 🧠 **Seleccionando** - IA analiza conversación y elige mejores momentos
4. 🎨 **Renderizando** - Aplica layout, encuadre, nivelación de voz
5. 📝 **Subtítulos** - Genera karaoke (amarillo→verde) sincronizado

### Paso 4: Resultados
Se abrirá la ventana de **Resultados** con una tarjeta por clip generado.

---

## 🖥️ Interfaz principal

### Pantalla de inicio
```
┌─────────────────────────────────────────────────────────────┐
│  AutoClip Studio    [⚙]                                     │
│  Clips de pódcast para Reels, Shorts y TikTok              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────────────────────────────────────────────┐  │
│   │  Pega la URL del episodio                           │  │
│   │  https://youtube.com/watch?v=...              [✓]  │  │
│   │                              [Validar] [Generar]    │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
│   ▼ Ajustes avanzados                                       │
│   ┌─────────────────────────────────────────────────────┐  │
│   │  Máx. clips: [3 ▼]   Máx. duración: [75s ▼]        │  │
│   │  Modelo: [large-v3 ▼]  Layout: [Solo pódcast ▼]    │  │
│   │  Tema opcional: [cuando cuenta por qué cerró...]   │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  Listo                                    AutoClip Studio  │
└─────────────────────────────────────────────────────────────┘
```

### Durante el procesamiento
```
┌─────────────────────────────────────────────────────────────┐
│  Descargando                                    ████░░ 45%  │
│  Descargando vídeo y extrayendo audio...                   │
│  Elemento 1 de 1                                            │
│  ┌─────┐ ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌─────┐  │
│  │ ▓▓▓ │ │ ▓▓▓▓▓▓▓▓ │ │ ░░░░░░░░░░ │ │ ░░░░░░░░ │ │ ░░░ │  │
│  └─────┘ └──────────┘ └───────────┘ └──────────┘ └─────┘  │
│  Desc.  Transcrib.  Selecc.    Render.    Subtít.          │
│                                                             │
│  [Cancelar]                                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 Revisar y editar clips

### Ventana de resultados
Cada clip se muestra en una **tarjeta** con:

| Elemento | Descripción |
|----------|-------------|
| **Vídeo vertical** | Previsualización 9:16 (1080×1920) |
| **Puntuación** | % de "Potencial editorial" (ver desglose al pasar ratón) |
| **Gancho** | Primera frase que atrapa al espectador |
| **Desarrollo** | Explicación/anécdota/respuesta |
| **Cierre** | Remate o conclusión |
| **Timecode** | Origen en el episodio (ej: 12:34 - 13:45) |
| **Layout** | Solo pódcast / Pelotas y aros / etc. |
| **Duración** | Ej: 1:23 |

### Acciones por clip
- **▶ Reproducir** - Abre el MP4 en el reproductor por defecto
- **📋 Copiar publicación** - Copia texto + hashtags al portapapeles
- **✏️ Revisar subtítulos** - Abre el editor de subtítulos
- **💾 Exportar** - Guarda MP4 final con subtítulos quemados

### Si no te convencen los clips
- Pulsa **"Nuevo proyecto"** para volver al inicio
- Cambia el **tema** o **ajustes** y vuelve a generar
- El sistema prioriza **calidad sobre cantidad**: 2 clips publicables > 10 para re-editar

---

## ✏️ Editor de subtítulos

### Qué verás
```
┌─────────────────────────┬─────────────────────────────────────┐
│   VÍDEO (9:16)          │  SUBTÍTULOS (estilo karaoke)        │
│   ┌─────────────────┐   │  ┌─────────────────────────────┐   │
│   │                 │   │  │ ▶ Reproducir desde aquí       │   │
│   │   [REPRODUCTOR] │   │  ├─────────────────────────────┤   │
│   │                 │   │  │ 00:12  🟡 "cerré"  🟢 "la"   │   │
│   │  [████████░░]   │   │  │  🟢 "tienda" 🟡 "cuando"     │   │
│   │  00:12 / 01:30  │   │  │  ⚪ "empezó" ⚪ "a" ⚪ "ser"   │   │
│   └─────────────────┘   │  ├─────────────────────────────┤   │
│   [⏪5s] [⏸] [5s⏩]     │  │  🟢 "rentable" 🟡 "?"         │   │
└─────────────────────────┴─────────────────────────────────────┘
  Leyenda: 🟡 Activa (amarillo)  🟢 Pronunciada (verde)  ⚪ Pendiente (blanco)
           🔴 Corregida (coral)  ⚠ Baja confianza (ámbar)
```

### Funciones del editor
1. **Reproducir vídeo** - Controles estándar (play/pausa, ±5s, barra de progreso)
2. **Palabra por palabra** - Cada palabra tiene su timestamp real
3. **Colores karaoke**:
   - 🟡 **Amarillo dorado**: Palabra que se está pronunciando AHORA
   - 🟢 **Verde primavera**: Palabra ya pronunciada
   - ⚪ **Blanco translúcido**: Palabras futuras
4. **Marcadores de confianza** - Palabras con ⚠ (ámbar) = baja confianza, revisar
5. **Corregir palabra**:
   - Haz clic en una palabra → se abre diálogo
   - Escribe el texto correcto
   - Ajusta **desfase temporal** (± segundos) si la palabra aparece adelantada/retrasada
   - Pulsa "Aplicar"
6. **▶ Desde aquí** - Reproduce el vídeo desde la palabra seleccionada para verificar
7. **Deshacer** - Revierte la última corrección
8. **Aplicar correcciones** - Regenera subtítulos con cambios

### Exportar subtítulos
- **Exportar .srt** - Formato estándar para subir a YouTube/TikTok/Instagram por separado
- Los subtítulos **quemados en el MP4** se generan al exportar el clip final

---

## 💾 Exportar y publicar

### Exportar clip individual
1. En la tarjeta del clip, pulsa **Exportar**
2. Elige carpeta y nombre (sugerido: `clip_fecha_id.mp4`)
3. El sistema quema los subtítulos en el vídeo (ASS → MP4)
4. Verás confirmación: *"Clip exportado a: ruta/archivo.mp4"*

### Exportar todos
- En la barra inferior: **"Exportar todos"** → genera todos los clips de golpe

### Publicación en redes
El texto copiado con **"Copiar publicación"** incluye:
```
[Gancho del clip]

🎙️ Del episodio: [fragmento original]...

#PodcastEnClips #Shorts #Reels #TikTok #Emprendimiento #Dinero
```
- Los **hashtags** son específicos del contenido del clip
- **No se inventan citas**: solo se entrecomilla texto que SÍ está en el clip
- **No se usan** muletillas ("inaudible", "eh", "este") como hashtags

### Dónde están tus archivos
- **Clips finales**: `Documentos\AutoClipStudio\Clips\`
- **Subtítulos .ass/.srt**: `Documentos\AutoClipStudio\Clips\subtitles\`
- **Archivos temporales**: `%TEMP%\AutoClipStudio\` (se limpian al cerrar, salvo que cambies la opción)

---

## ⚙️ Configuración

Accede desde el icono **⚙** en la cabecera.

### General
- **Idioma**: Español (España) / English (US)
- **Tema**: Oscuro / Claro / Sistema
- **Actualizaciones**: Comprobar automáticamente
- **Inicio**: Minimizado

### Rutas
- **Carpeta de salida**: Donde se guardan los MP4 finales
- **Carpeta temporal**: Donde se descargan y procesan vídeos (requiere espacio)

### Vídeo por defecto
- **Resolución**: 1080×1920 (9:16 vertical)
- **FPS**: 30
- **Máx. clips**: 3
- **Máx. duración**: 75s
- **Layout**: Solo pódcast

### Transcripción (Whisper)
- **Modelo**: large-v3 (mejor precisión, ~1.5 GB)
- **Idioma**: es (español) - detección automática si "auto"
- **Dispositivo**: Auto (GPU si hay NVIDIA CUDA)
- **Precisión**: float16 (rápido en GPU) / int8 (CPU)

### Subtítulos
- **Fuente**: Inter (variable, legible en móvil)
- **Tamaño**: 48pt (base para 1080p)
- **Duración línea**: 0.45s (ajustable)
- **Máx. palabras/línea**: 8
- **Máx. líneas**: 2

### Avanzado
- **GPU**: Aceleración por hardware (FFmpeg + PyTorch)
- **Trabajos concurrentes**: 1 (secuencial para estabilidad)
- **Mantener temporales**: Para depuración
- **Log level**: INFO / DEBUG / WARNING / ERROR

---

## 🔧 Solución de problemas

| Problema | Solución |
|----------|----------|
| **"Python no encontrado"** | Instala Python 3.11+ o usa el instalador completo (incluye Python embebido) |
| **"FFmpeg no encontrado"** | El instalador lo incluye. Si falla, instala FFmpeg en PATH |
| **Descarga de YouTube falla** | Verifica URL pública (no privada/eliminada). Prueba en navegador primero |
| **Transcripción muy lenta** | Usa modelo "small" o "medium" en ajustes; requiere GPU para large-v3 rápido |
| **Subtítulos desincronizados** | Usa el editor: corrige palabra y ajusta "desfase temporal" |
| **Clip incluye promo final** | En editor de subtítulos, marca rango a excluir; o edita timecode final |
| **Poca memoria / error CUDA** | Cambia "Dispositivo" a "cpu" y "Precisión" a "int8" en ajustes |
| **Vídeo no se reproduce** | Instala codecs HEVC (Microsoft Store) o usa VLC |
| **Instalador pide reinicio** | Reinicia Windows y vuelve a ejecutar el instalador |

### Logs
- Ver en `%LOCALAPPDATA%\AutoClipStudio\logs\`
- Nivel configurable en Ajustes → Avanzado

---

## 📐 Especificaciones técnicas

### Formatos de salida
- **Vídeo**: MP4 (H.264 / AAC), 1080×1920, 30 FPS, 9:16
- **Subtítulos**: ASS (karaoke) quemados en vídeo + SRT opcional
- **Audio**: 48 kHz estéreo, 128 kbps AAC

### Layouts disponibles
| Layout | Tipo | Descripción |
|--------|------|-------------|
| **Solo pódcast** | Full-screen | Vídeo vertical recortado con encuadre inteligente |
| **Pelotas y aros** | Split 55/45 | Pódcast arriba, animación de pelotas rebotando abajo |
| **Parkour de bloques** | Split 55/45 | Pódcast arriba, parkour estilo Minecraft abajo |
| **Mi gameplay** | Split 55/45 | Pódcast arriba, TU vídeo de Minecraft abajo (silenciado) |

### Modelo de transcripción
- **Whisper large-v3** (OpenAI) via faster-whisper (CTranslate2)
- **Timestamps por palabra** (word-level)
- **Idiomas**: 99+ (optimizado para español)
- **Diarización**: No incluida (single speaker assumed)

### Selección de clips (Potencial Editorial)
La puntuación **no es probabilidad de viralidad** (no hay datos de tu canal), sino **calidad editorial** basada en:
- **Gancho (30%)**: Pregunta concreta, confesión, contradicción, dato sorprendente
- **Desarrollo (30%)**: Explicación con detalles, cifras, nombres, anécdota completa
- **Cierre (20%)**: Remate, consecuencia, moraleja, conclusión clara
- **Claridad (20%)**: Confianza transcripción, pocos hablantes, sin solapamientos

> **Nota**: Si ves muchas palabras con ⚠ (baja confianza), la puntuación baja. Revisa en el editor.

### Descargas en primer uso
| Componente | Tamaño | Cuándo |
|------------|--------|--------|
| Whisper large-v3 | ~1.5 GB | Primera transcripción |
| Python embebido | ~50 MB | Instalación (si no hay Python en sistema) |
| FFmpeg | ~80 MB | Instalación |
| yt-dlp | ~5 MB | Primera descarga |
| Backgrounds (2) | ~30 MB | Instalación |

**Total estimado**: ~3-5 GB en disco tras primer uso completo.

---

## 📄 Licencia y créditos

**AutoClip Studio** - Copyright © 2024 AutoClip Studio Team

### Tecnologías usadas
- **WPF / .NET 8** - Interfaz nativa Windows
- **faster-whisper** (Guillaume Klein) - Transcripción rápida
- **yt-dlp** - Descarga de vídeo
- **FFmpeg** - Procesamiento de vídeo/audio
- **MaterialDesign / Wpf.Ui** - Controles UI modernos
- **Inter Font** (Rasmus Andersson) - Tipografía
- **JetBrains Mono** - Tipografía monoespaciada

### Assets incluidos
- **Pelotas escapando de aros** - Animación procedural generada
- **Parkour de bloques** - Animación procedural generada

---

## 📞 Soporte

- **Documentación**: https://autoclipstudio.com/docs
- **Issues**: https://github.com/autoclipstudio/issues
- **Email**: soporte@autoclipstudio.com

---

*Última actualización: Noviembre 2024 | Versión 1.0.0*