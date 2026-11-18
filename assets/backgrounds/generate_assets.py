#!/usr/bin/env python3
"""
AutoClip Studio - Generador de Assets de Fondo Procedurales
Genera: balls_hoops.mp4 (Pelotas escapando de aros) y block_parkour.mp4 (Parkour de bloques)
Requisitos: opencv-python, numpy
Uso: python generate_assets.py
"""

import cv2
import numpy as np
import os
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent
WIDTH, HEIGHT = 1080, 1920  # 9:16 vertical
FPS = 30
DURATION = 30  # seconds
TOTAL_FRAMES = FPS * DURATION

# Colores base (BGR para OpenCV)
BG_COLOR = (20, 20, 40)  # Azul marino muy oscuro
ACCENT_GOLD = (0, 215, 255)      # Dorado #FFD700
ACCENT_GREEN = (127, 255, 0)     # Verde primavera #00FF7F
ACCENT_CORAL = (100, 100, 255)   # Coral #FF6464
ACCENT_BLUE = (255, 200, 100)    # Azul claro
ACCENT_PURPLE = (200, 100, 255)  # Púrpura

def generate_balls_hoops():
    """Genera 'Pelotas escapando de aros' - animación fluida y satisfactoria."""
    print("Generando balls_hoops.mp4...")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(OUTPUT_DIR / "balls_hoops.mp4"), fourcc, FPS, (WIDTH, HEIGHT))

    # Configuración de pelotas
    balls = []
    colors = [ACCENT_GOLD, ACCENT_GREEN, ACCENT_CORAL, ACCENT_BLUE, ACCENT_PURPLE]

    # Aros iniciales (5 aros en columna central)
    hoops = []
    for i in range(5):
        hoops.append({
            'x': WIDTH // 2,
            'y': HEIGHT // 2 + (i - 2) * 280,
            'radius': 100,
            'thickness': 6,
            'color': (80, 80, 140),
            'active': True,
            'escape_time': 3.0 + i * 1.5,  # Escalonado
            'escaped': False,
            'particles': []
        })

    # Pelotas dentro de aros
    for i, hoop in enumerate(hoops):
        balls.append({
            'x': hoop['x'],
            'y': hoop['y'],
            'vx': 0,
            'vy': 0,
            'radius': 35,
            'color': colors[i],
            'in_hoop': True,
            'hoop_idx': i,
            'trail': []
        })

    # Partículas de fondo sutiles
    bg_particles = []
    for _ in range(30):
        bg_particles.append({
            'x': np.random.randint(0, WIDTH),
            'y': np.random.randint(0, HEIGHT),
            'vx': np.random.uniform(-0.3, 0.3),
            'vy': np.random.uniform(-0.5, -0.1),
            'size': np.random.randint(2, 6),
            'color': (60, 60, 100),
            'alpha': np.random.uniform(0.2, 0.6)
        })

    for frame_num in range(TOTAL_FRAMES):
        frame = np.full((HEIGHT, WIDTH, 3), BG_COLOR, dtype=np.uint8)
        t = frame_num / FPS

        # Fondo con gradiente sutil animado
        for y in range(0, HEIGHT, 4):
            alpha = 0.02 * np.sin(t * 0.5 + y * 0.01)
            color_val = int(10 + 15 * alpha)
            frame[y:y+4, :] = np.clip(frame[y:y+4, :] + color_val, 0, 255)

        # Partículas de fondo
        for p in bg_particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            if p['y'] < 0:
                p['y'] = HEIGHT
                p['x'] = np.random.randint(0, WIDTH)
            cv2.circle(frame, (int(p['x']), int(p['y'])), p['size'], p['color'], -1)

        # Actualizar y dibujar aros
        for hoop in hoops:
            if hoop['active'] and not hoop['escaped'] and t > hoop['escape_time']:
                hoop['escaped'] = True
                # Crear partículas de "explosión" del aro
                for _ in range(20):
                    angle = np.random.uniform(0, 2*np.pi)
                    speed = np.random.uniform(3, 8)
                    hoop['particles'].append({
                        'x': hoop['x'],
                        'y': hoop['y'],
                        'vx': np.cos(angle) * speed,
                        'vy': np.sin(angle) * speed,
                        'life': 1.0,
                        'color': hoop['color']
                    })

            if hoop['active']:
                # Aro principal
                alpha = 1.0 if not hoop['escaped'] else max(0, 1.0 - (t - hoop['escape_time']) / 2.0)
                color = tuple(int(c * alpha) for c in hoop['color'])
                cv2.ellipse(frame, (hoop['x'], hoop['y']), (hoop['radius'], hoop['radius']),
                           0, 0, 360, color, hoop['thickness'])
                # Brillo interno
                cv2.ellipse(frame, (hoop['x'], hoop['y']), (hoop['radius']-8, hoop['radius']-8),
                           0, 0, 360, tuple(min(255, c+30) for c in color), 2)

            # Partículas del aro
            for part in hoop['particles'][:]:
                part['x'] += part['vx']
                part['y'] += part['vy']
                part['vy'] += 0.15  # gravedad
                part['life'] -= 0.02
                if part['life'] > 0:
                    c = tuple(int(c * part['life']) for c in part['color'])
                    cv2.circle(frame, (int(part['x']), int(part['y'])), 4, c, -1)
                else:
                    hoop['particles'].remove(part)

        # Actualizar y dibujar pelotas
        for ball in balls:
            if ball['in_hoop']:
                hoop = hoops[ball['hoop_idx']]
                if t > hoop['escape_time']:
                    ball['in_hoop'] = False
                    # Disparar pelota fuera del aro
                    angle = np.random.uniform(-np.pi/3, -2*np.pi/3)  # Hacia arriba-fuera
                    speed = np.random.uniform(8, 14)
                    ball['vx'] = np.cos(angle) * speed
                    ball['vy'] = np.sin(angle) * speed
                    ball['x'] = hoop['x']
                    ball['y'] = hoop['y']

            # Física
            ball['x'] += ball['vx']
            ball['y'] += ball['vy']
            ball['vy'] += 0.25  # gravedad
            ball['vx'] *= 0.995  # fricción aire ligera

            # Trail
            ball['trail'].append((ball['x'], ball['y']))
            if len(ball['trail']) > 12:
                ball['trail'].pop(0)

            # Rebotes en paredes
            if ball['x'] - ball['radius'] < 0:
                ball['x'] = ball['radius']
                ball['vx'] *= -0.75
            elif ball['x'] + ball['radius'] > WIDTH:
                ball['x'] = WIDTH - ball['radius']
                ball['vx'] *= -0.75

            if ball['y'] - ball['radius'] < 0:
                ball['y'] = ball['radius']
                ball['vy'] *= -0.7
            elif ball['y'] + ball['radius'] > HEIGHT:
                ball['y'] = HEIGHT - ball['radius']
                ball['vy'] *= -0.7

            # Dibujar trail
            for i, (tx, ty) in enumerate(ball['trail']):
                alpha = (i + 1) / len(ball['trail']) * 0.4
                size = int(ball['radius'] * alpha)
                if size > 1:
                    c = tuple(int(c * alpha) for c in ball['color'])
                    cv2.circle(frame, (int(tx), int(ty)), size, c, -1)

            # Pelota principal con brillo 3D
            cv2.circle(frame, (int(ball['x']), int(ball['y'])), ball['radius'], ball['color'], -1)
            # Highlight superior
            cv2.circle(frame, (int(ball['x']-8), int(ball['y']-8)), ball['radius']//3,
                      tuple(min(255, c+60) for c in ball['color']), -1)
            # Sombra inferior
            cv2.circle(frame, (int(ball['x']+5), int(ball['y']+5)), ball['radius']//2,
                      tuple(max(0, c-60) for c in ball['color']), -1)

            # Si sale de pantalla, resetear (loop)
            if ball['y'] > HEIGHT + 100:
                ball['y'] = -50
                ball['x'] = np.random.randint(100, WIDTH-100)
                ball['vx'] = np.random.uniform(-2, 2)
                ball['vy'] = np.random.uniform(2, 5)
                ball['trail'] = []

        out.write(frame)

        if frame_num % 300 == 0:
            print(f"  Frame {frame_num}/{TOTAL_FRAMES}")

    out.release()
    print("  ¡Completado!")

    # Thumbnail
    thumb = np.full((HEIGHT, WIDTH, 3), BG_COLOR, dtype=np.uint8)
    for ball in balls[:3]:
        cv2.circle(thumb, (int(ball['x']), int(ball['y'])), ball['radius'], ball['color'], -1)
        cv2.circle(thumb, (int(ball['x']-8), int(ball['y']-8)), ball['radius']//3,
                  tuple(min(255, c+60) for c in ball['color']), -1)
    for hoop in hoops[:3]:
        cv2.ellipse(thumb, (hoop['x'], hoop['y']), (hoop['radius'], hoop['radius']),
                   0, 0, 360, hoop['color'], hoop['thickness'])
    cv2.imwrite(str(OUTPUT_DIR / "balls_hoops_thumb.jpg"), thumb)


def generate_block_parkour():
    """Genera 'Parkour de bloques' - estilo Minecraft procedural."""
    print("Generando block_parkour.mp4...")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(OUTPUT_DIR / "block_parkour.mp4"), fourcc, FPS, (WIDTH, HEIGHT))

    BG_COLOR = (25, 35, 25)  # Verde muy oscuro

    # Colores de bloques estilo Minecraft
    BLOCK_TYPES = [
        {'name': 'grass', 'top': (80, 180, 90), 'side': (60, 140, 70), 'bottom': (100, 90, 60)},
        {'name': 'stone', 'top': (130, 130, 130), 'side': (110, 110, 110), 'bottom': (90, 90, 90)},
        {'name': 'dirt', 'top': (100, 80, 50), 'side': (80, 65, 40), 'bottom': (70, 55, 35)},
        {'name': 'sand', 'top': (200, 190, 140), 'side': (180, 170, 120), 'bottom': (160, 150, 100)},
        {'name': 'wood', 'top': (140, 100, 60), 'side': (120, 85, 50), 'bottom': (100, 70, 40)},
    ]

    BLOCK_SIZE = 55
    ISO_ANGLE = 0.4636  # ~26.565° isométrico

    # Generar curso parkour ascendente
    course = []
    x = WIDTH // 2
    y = HEIGHT - 80

    for i in range(35):
        bt = np.random.choice(BLOCK_TYPES)
        step_type = np.random.choice(['straight', 'jump', 'gap', 'ladder', 'corner'], p=[0.4, 0.2, 0.15, 0.15, 0.1])

        if step_type == 'straight':
            x += np.random.randint(-70, 70)
            y -= BLOCK_SIZE + 8
        elif step_type == 'jump':
            x += np.random.randint(-110, 110)
            y -= BLOCK_SIZE * 2 + 15
        elif step_type == 'gap':
            x += np.random.randint(-140, 140)
            y -= BLOCK_SIZE + 8
        elif step_type == 'ladder':
            for _ in range(3):
                course.append({'x': x, 'y': y, 'type': bt, 'variant': 'ladder'})
                y -= BLOCK_SIZE + 2
            continue
        elif step_type == 'corner':
            x += np.random.choice([-1, 1]) * 120
            y -= BLOCK_SIZE + 8

        x = np.clip(x, 80, WIDTH - 80)
        course.append({'x': x, 'y': y, 'type': bt, 'variant': step_type})

    # Jugador (Steve-like)
    player = {
        'x': WIDTH // 2,
        'y': HEIGHT - 80,
        'vx': 0,
        'vy': 0,
        'on_ground': True,
        'anim_frame': 0,
        'facing': 1
    }

    # Partículas de ambiente
    dust_particles = []
    for _ in range(20):
        dust_particles.append({
            'x': np.random.randint(0, WIDTH),
            'y': np.random.randint(0, HEIGHT),
            'vx': np.random.uniform(-0.5, 0.5),
            'vy': np.random.uniform(-0.3, 0.1),
            'life': np.random.uniform(0, 1),
            'size': np.random.randint(2, 5),
            'color': (100, 90, 70)
        })

    for frame_num in range(TOTAL_FRAMES):
        frame = np.full((HEIGHT, WIDTH, 3), BG_COLOR, dtype=np.uint8)
        t = frame_num / FPS

        # Cámara sigue al jugador (suavizada)
        target_cam_y = player['y'] - HEIGHT * 0.25
        cam_y = getattr(generate_block_parkour, 'cam_y', target_cam_y)
        cam_y += (target_cam_y - cam_y) * 0.12
        generate_block_parkour.cam_y = cam_y

        # Dibujar bloques (ordenados por Y para profundidad)
        visible_blocks = [b for b in course if -BLOCK_SIZE*2 < b['y'] - cam_y < HEIGHT + BLOCK_SIZE*2]
        visible_blocks.sort(key=lambda b: b['y'], reverse=True)

        for block in visible_blocks:
            bx, by = block['x'], block['y']
            bt = block['type']
            by_screen = int(by - cam_y)

            if -BLOCK_SIZE < by_screen < HEIGHT + BLOCK_SIZE:
                draw_isometric_block(frame, bx, by_screen, BLOCK_SIZE, bt)

        # Lógica del jugador
        target_block = find_target_block(course, player['x'], player['y'])

        if target_block:
            dx = target_block['x'] - player['x']
            dy = target_block['y'] - player['y']

            # Movimiento horizontal
            if abs(dx) > 15:
                player['vx'] = np.sign(dx) * 3.5
                player['facing'] = np.sign(dx)
            else:
                player['vx'] *= 0.85

            # Salto
            if player['on_ground'] and dy < -30:
                player['vy'] = -14
                player['on_ground'] = False
                # Partículas de salto
                for _ in range(8):
                    dust_particles.append({
                        'x': player['x'] + np.random.uniform(-10, 10),
                        'y': player['y'] + 20,
                        'vx': np.random.uniform(-2, 2),
                        'vy': np.random.uniform(-3, -1),
                        'life': 1.0,
                        'size': np.random.randint(3, 6),
                        'color': (120, 110, 90)
                    })

        # Física jugador
        player['vy'] += 0.55  # gravedad
        player['x'] += player['vx']
        player['y'] += player['vy']

        # Colisión con bloques
        player['on_ground'] = False
        for block in course:
            bx, by = block['x'], block['y']
            if (abs(player['x'] - bx) < BLOCK_SIZE * 0.45 and
                player['y'] + 28 > by - BLOCK_SIZE//2 and
                player['y'] + 28 < by + BLOCK_SIZE//2 and
                player['vy'] > 0):
                player['y'] = by - BLOCK_SIZE//2 - 28
                player['vy'] = 0
                player['on_ground'] = True
                break

        # Límites pantalla
        player['x'] = np.clip(player['x'], 50, WIDTH - 50)

        # Partículas polvo
        for p in dust_particles[:]:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['vy'] += 0.05
            p['life'] -= 0.015
            if p['life'] > 0:
                alpha = p['life']
                c = tuple(int(c * alpha) for c in p['color'])
                cv2.circle(frame, (int(p['x']), int(p['y'] - cam_y)), p['size'], c, -1)
            else:
                dust_particles.remove(p)

        # Dibujar jugador
        px, py = int(player['x']), int(player['y'] - cam_y)
        if 0 < px < WIDTH and 0 < py < HEIGHT:
            draw_player(frame, px, py, player['facing'], player['anim_frame'])
            player['anim_frame'] = (player['anim_frame'] + 0.15) % 4

        out.write(frame)

        if frame_num % 300 == 0:
            print(f"  Frame {frame_num}/{TOTAL_FRAMES}")

    out.release()
    print("  ¡Completado!")

    # Thumbnail
    thumb = np.full((HEIGHT, WIDTH, 3), BG_COLOR, dtype=np.uint8)
    for block in course[:12]:
        bx, by = block['x'], block['y']
        draw_isometric_block(thumb, bx, by, BLOCK_SIZE, block['type'])
    cv2.imwrite(str(OUTPUT_DIR / "block_parkour_thumb.jpg"), thumb)


def draw_isometric_block(frame, cx, cy, size, block_type):
    """Dibuja un bloque isométrico 3D."""
    half = size // 2
    h = size // 2  # altura del bloque

    # Coordenadas isométricas
    iso_x = cx
    iso_y = cy - h

    # Cara superior (rombo)
    top_points = np.array([
        [iso_x, iso_y],           # arriba
        [iso_x + half, iso_y + half//2],  # derecha
        [iso_x, iso_y + h],       # abajo
        [iso_x - half, iso_y + half//2]   # izquierda
    ], np.int32)

    cv2.fillPoly(frame, [top_points], block_type['top'])
    cv2.polylines(frame, [top_points], True, tuple(min(255, c+25) for c in block_type['top']), 1)

    # Cara derecha (paralelogramo)
    right_points = np.array([
        [iso_x + half, iso_y + half//2],
        [iso_x, iso_y + h],
        [iso_x, iso_y + h + size],
        [iso_x + half, iso_y + half//2 + size]
    ], np.int32)
    cv2.fillPoly(frame, [right_points], block_type['side'])

    # Cara izquierda
    left_points = np.array([
        [iso_x - half, iso_y + half//2],
        [iso_x, iso_y + h],
        [iso_x, iso_y + h + size],
        [iso_x - half, iso_y + half//2 + size]
    ], np.int32)
    cv2.fillPoly(frame, [left_points], tuple(max(0, c-30) for c in block_type['side']))

    # Detalles en cara superior (textura sutil)
    for _ in range(2):
        tx = iso_x + np.random.randint(-half//2, half//2)
        ty = iso_y + np.random.randint(-half//2, half//2)
        cv2.circle(frame, (tx, ty), 2, tuple(max(0, c-15) for c in block_type['top']), -1)


def find_target_block(course, px, py):
    """Encuentra el bloque objetivo más cercano adelante."""
    candidates = [b for b in course if b['y'] < py - 20]
    if not candidates:
        return None
    return min(candidates, key=lambda b: abs(b['x'] - px) + (py - b['y']))


def draw_player(frame, cx, cy, facing, anim_frame):
    """Dibuja personaje estilo Steve isométrico."""
    frame_int = int(anim_frame)
    leg_offset = 4 if frame_int % 2 == 0 else -4
    arm_offset = -3 if frame_int % 2 == 0 else 3

    # Cuerpo (caja 3D simplificada)
    body_w, body_h = 20, 32
    head_size = 22

    # Sombra
    cv2.ellipse(frame, (cx, cy + 30), (22, 6), 0, 0, 360, (15, 15, 20), -1)

    # Piernas
    leg_color = (50, 90, 160)
    leg_w = 8
    cv2.rectangle(frame, (cx - 10, cy - body_h), (cx - 2, cy), leg_color, -1)
    cv2.rectangle(frame, (cx + 2, cy - body_h), (cx + 10, cy), leg_color, -1)

    # Movimiento piernas
    cv2.rectangle(frame, (cx - 10 + leg_offset, cy - body_h),
                 (cx - 2 + leg_offset, cy), leg_color, -1)

    # Torso
    torso_color = (70, 130, 200)
    cv2.rectangle(frame, (cx - 12, cy - body_h - 22), (cx + 12, cy - body_h), torso_color, -1)

    # Brazos
    arm_color = (200, 170, 130)  # piel
    cv2.rectangle(frame, (cx - 20 + arm_offset, cy - body_h - 20),
                 (cx - 12 + arm_offset, cy - body_h + 5), arm_color, -1)
    cv2.rectangle(frame, (cx + 12 - arm_offset, cy - body_h - 20),
                 (cx + 20 - arm_offset, cy - body_h + 5), arm_color, -1)

    # Cabeza
    head_color = (220, 180, 140)
    cv2.rectangle(frame, (cx - head_size//2, cy - body_h - 22 - head_size),
                 (cx + head_size//2, cy - body_h - 22), head_color, -1)

    # Ojos
    eye_y = cy - body_h - 22 - head_size + 6
    cv2.rectangle(frame, (cx - 7, eye_y), (cx - 4, eye_y + 5), (0, 0, 0), -1)
    cv2.rectangle(frame, (cx + 4, eye_y), (cx + 7, eye_y + 5), (0, 0, 0), -1)

    # Highlight cabeza
    cv2.rectangle(frame, (cx - head_size//2, cy - body_h - 22 - head_size),
                 (cx + head_size//2, cy - body_h - 22 - head_size + 3),
                 tuple(min(255, c+30) for c in head_color), -1)


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 50)
    print("GENERANDO ASSETS DE FONDO - AUTOCLIP STUDIO")
    print("=" * 50)
    generate_balls_hoops()
    print()
    generate_block_parkour()
    print()
    print("=" * 50)
    print("✅ ASSETS GENERADOS EXITOSAMENTE")
    print(f"   📁 {OUTPUT_DIR.absolute()}")
    print("   - balls_hoops.mp4 + thumb")
    print("   - block_parkour.mp4 + thumb")
    print("=" * 50)