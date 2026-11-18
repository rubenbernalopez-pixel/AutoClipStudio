#!/usr/bin/env python3
"""
Generate placeholder background videos for AutoClip Studio.
Run this script to create the bundled background assets.
Requires: opencv-python, numpy
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

def generate_balls_hoops():
    """Generate 'Pelotas escapando de aros' - balls bouncing and escaping hoops."""
    print("Generating balls_hoops.mp4...")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(OUTPUT_DIR / "balls_hoops.mp4"), fourcc, FPS, (WIDTH, HEIGHT))

    # Colors (BGR)
    BG_COLOR = (20, 20, 40)  # Dark navy
    BALL_COLORS = [
        (0, 215, 255),   # Gold
        (0, 255, 127),   # Spring green
        (255, 100, 100), # Coral
        (100, 200, 255), # Light blue
        (255, 255, 100), # Yellow
    ]
    HOOP_COLOR = (80, 80, 120)

    # Ball properties
    balls = []
    for i in range(5):
        balls.append({
            'x': np.random.randint(100, WIDTH - 100),
            'y': np.random.randint(100, HEIGHT - 100),
            'vx': np.random.uniform(-3, 3),
            'vy': np.random.uniform(-3, 3),
            'radius': np.random.randint(25, 45),
            'color': BALL_COLORS[i],
            'in_hoop': True,
            'hoop_x': WIDTH // 2,
            'hoop_y': HEIGHT // 2 + (i - 2) * 200,
            'escape_time': np.random.uniform(3, 10),  # seconds before escaping
            'escaped': False
        })

    for frame_num in range(TOTAL_FRAMES):
        # Create frame
        frame = np.full((HEIGHT, WIDTH, 3), BG_COLOR, dtype=np.uint8)
        t = frame_num / FPS

        # Draw hoops (static, fading as balls escape)
        for i, ball in enumerate(balls):
            if not ball['escaped'] or t < ball['escape_time'] + 2:
                alpha = 1.0
                if ball['escaped']:
                    alpha = max(0, 1.0 - (t - ball['escape_time']) / 2.0)
                hoop_color = tuple(int(c * alpha) for c in HOOP_COLOR)
                cv2.ellipse(frame,
                           (ball['hoop_x'], ball['hoop_y']),
                           (80, 80), 0, 0, 360, hoop_color, 4)

        # Update and draw balls
        for ball in balls:
            if not ball['escaped']:
                if t > ball['escape_time']:
                    ball['escaped'] = True
                    # Shoot out of hoop
                    angle = np.random.uniform(0, 2 * np.pi)
                    speed = np.random.uniform(5, 10)
                    ball['vx'] = np.cos(angle) * speed
                    ball['vy'] = np.sin(angle) * speed
                    ball['x'] = ball['hoop_x']
                    ball['y'] = ball['hoop_y']

            # Physics
            ball['x'] += ball['vx']
            ball['y'] += ball['vy']
            ball['vy'] += 0.2  # gravity

            # Bounce off walls
            if ball['x'] - ball['radius'] < 0:
                ball['x'] = ball['radius']
                ball['vx'] *= -0.8
            elif ball['x'] + ball['radius'] > WIDTH:
                ball['x'] = WIDTH - ball['radius']
                ball['vx'] *= -0.8

            if ball['y'] - ball['radius'] < 0:
                ball['y'] = ball['radius']
                ball['vy'] *= -0.8
            elif ball['y'] + ball['radius'] > HEIGHT:
                ball['y'] = HEIGHT - ball['radius']
                ball['vy'] *= -0.8

            # Draw ball with trail effect
            cv2.circle(frame, (int(ball['x']), int(ball['y'])),
                      ball['radius'], ball['color'], -1)
            # Highlight
            cv2.circle(frame, (int(ball['x']), int(ball['y'])),
                      ball['radius'] - 5, tuple(min(255, c + 50) for c in ball['color']), -1)

        out.write(frame)

    out.release()
    print("  Done!")

    # Generate thumbnail
    thumb_frame = np.full((HEIGHT, WIDTH, 3), BG_COLOR, dtype=np.uint8)
    for ball in balls:
        cv2.circle(thumb_frame, (int(ball['x']), int(ball['y'])),
                  ball['radius'], ball['color'], -1)
    cv2.imwrite(str(OUTPUT_DIR / "balls_hoops_thumb.jpg"), thumb_frame)


def generate_block_parkour():
    """Generate 'Parkour de bloques' - Minecraft-style block parkour."""
    print("Generating block_parkour.mp4...")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(OUTPUT_DIR / "block_parkour.mp4"), fourcc, FPS, (WIDTH, HEIGHT))

    BG_COLOR = (20, 30, 20)  # Dark green-ish
    BLOCK_COLORS = [
        (100, 180, 100),  # Grass block top
        (80, 140, 80),    # Grass block side
        (120, 120, 120),  # Stone
        (160, 120, 80),   # Dirt
        (200, 180, 140),  # Sand
    ]

    # Create parkour course
    blocks = []
    block_size = 60

    # Generate a course going upward
    x = WIDTH // 2
    y = HEIGHT - 100
    for i in range(25):
        # Random step
        step_type = np.random.choice(['straight', 'jump', 'gap', 'ladder'])

        if step_type == 'straight':
            x += np.random.randint(-80, 80)
            y -= block_size + 5
        elif step_type == 'jump':
            x += np.random.randint(-120, 120)
            y -= block_size * 2 + 10
        elif step_type == 'gap':
            x += np.random.randint(-150, 150)
            y -= block_size + 5
            # Gap - skip one block
        elif step_type == 'ladder':
            y -= block_size * 3

        x = np.clip(x, 50, WIDTH - 50)
        blocks.append({
            'x': x, 'y': y,
            'color': BLOCK_COLORS[np.random.randint(len(BLOCK_COLORS))],
            'type': step_type
        })

    # Player
    player_x = WIDTH // 2
    player_y = HEIGHT - 100
    player_vx = 0
    player_vy = 0
    player_on_ground = True
    current_block_idx = 0

    for frame_num in range(TOTAL_FRAMES):
        frame = np.full((HEIGHT, WIDTH, 3), BG_COLOR, dtype=np.uint8)
        t = frame_num / FPS

        # Camera follows player (vertical scroll)
        cam_y = player_y - HEIGHT * 0.3

        # Draw blocks
        for block in blocks:
            by = int(block['y'] - cam_y)
            if -block_size < by < HEIGHT + block_size:
                bx = int(block['x'])
                color = block['color']
                # 3D block effect
                cv2.rectangle(frame, (bx - block_size//2, by - block_size//2),
                             (bx + block_size//2, by + block_size//2), color, -1)
                # Top highlight
                cv2.rectangle(frame, (bx - block_size//2, by - block_size//2),
                             (bx + block_size//2, by - block_size//2 + 4),
                             tuple(min(255, c + 40) for c in color), -1)
                # Side shadow
                cv2.rectangle(frame, (bx + block_size//2 - 4, by - block_size//2),
                             (bx + block_size//2, by + block_size//2),
                             tuple(max(0, c - 40) for c in color), -1)

        # Simple player physics
        target_block = blocks[min(current_block_idx, len(blocks) - 1)]
        dx = target_block['x'] - player_x
        dy = target_block['y'] - player_y

        if abs(dx) > 20:
            player_vx = np.sign(dx) * 4
        else:
            player_vx *= 0.9

        if player_on_ground and dy < -50:
            player_vy = -15  # Jump
            player_on_ground = False

        player_vy += 0.6  # Gravity
        player_x += player_vx
        player_y += player_vy

        # Check landing
        for block in blocks:
            bx, by = block['x'], block['y']
            if (abs(player_x - bx) < block_size//2 and
                player_y + 30 > by - block_size//2 and
                player_y + 30 < by + block_size//2 and
                player_vy > 0):
                player_y = by - block_size//2 - 30
                player_vy = 0
                player_on_ground = True
                if blocks.index(block) > current_block_idx:
                    current_block_idx = blocks.index(block)
                break

        # Draw player (Steve-like)
        px, py = int(player_x - cam_y), int(player_y - cam_y)
        if 0 < px < WIDTH and 0 < py < HEIGHT:
            # Body
            cv2.rectangle(frame, (px - 15, py - 50), (px + 15, py), (100, 180, 220), -1)
            # Head
            cv2.rectangle(frame, (px - 20, py - 90), (px + 20, py - 50), (220, 180, 140), -1)
            # Eyes
            cv2.rectangle(frame, (px - 12, py - 75), (px - 8, py - 70), (0, 0, 0), -1)
            cv2.rectangle(frame, (px + 8, py - 75), (px + 12, py - 70), (0, 0, 0), -1)

        out.write(frame)

    out.release()
    print("  Done!")

    # Generate thumbnail
    thumb_frame = np.full((HEIGHT, WIDTH, 3), BG_COLOR, dtype=np.uint8)
    for block in blocks[:10]:
        cv2.rectangle(thumb_frame, (block['x'] - block_size//2, block['y'] - block_size//2),
                     (block['x'] + block_size//2, block['y'] + block_size//2), block['color'], -1)
    cv2.imwrite(str(OUTPUT_DIR / "block_parkour_thumb.jpg"), thumb_frame)


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    generate_balls_hoops()
    generate_block_parkour()
    print("\n✅ Background assets generated!")
    print(f"   Location: {OUTPUT_DIR.absolute()}")