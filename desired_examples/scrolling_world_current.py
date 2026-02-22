"""
Scrolling world: camera follows player, edge scrolling, 50 units with y-sorting.
This is what you write TODAY with pygame.
"""
import pygame
import random

pygame.init()
SCREEN_W, SCREEN_H = 1024, 768
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
clock = pygame.time.Clock()


# === Camera — you build from scratch ===

class Camera:
    def __init__(self, world_w, world_h):
        self.x = 0
        self.y = 0
        self.world_w = world_w
        self.world_h = world_h

    def center_on(self, x, y):
        self.x = x - SCREEN_W // 2
        self.y = y - SCREEN_H // 2
        # Clamp — easy to forget, causes black edges
        self.x = max(0, min(self.x, self.world_w - SCREEN_W))
        self.y = max(0, min(self.y, self.world_h - SCREEN_H))

    def apply(self, world_x, world_y):
        return world_x - self.x, world_y - self.y

    def screen_to_world(self, screen_x, screen_y):
        return screen_x + self.x, screen_y + self.y

    def edge_scroll(self, mouse_x, mouse_y, speed):
        margin = 20
        if mouse_x < margin:
            self.x -= speed
        elif mouse_x > SCREEN_W - margin:
            self.x += speed
        if mouse_y < margin:
            self.y -= speed
        elif mouse_y > SCREEN_H - margin:
            self.y += speed
        # Clamp again
        self.x = max(0, min(self.x, self.world_w - SCREEN_W))
        self.y = max(0, min(self.y, self.world_h - SCREEN_H))


camera = Camera(4096, 4096)


# === Sprite with y-sorting — no built-in support ===

class GameSprite:
    def __init__(self, image_path, x, y):
        self.image = pygame.image.load(image_path).convert_alpha()
        self.x = x
        self.y = y
        self.alive = True

    def draw(self, surface, cam):
        screen_x, screen_y = cam.apply(self.x, self.y)
        # Frustum culling — manual. Without it, you draw 1000 sprites offscreen.
        if (-64 < screen_x < SCREEN_W + 64 and -64 < screen_y < SCREEN_H + 64):
            # Bottom-center anchor — manual offset
            rect = self.image.get_rect(midbottom=(screen_x, screen_y))
            surface.blit(self.image, rect)


# === Layer management — manual sort every frame ===

# Create a bunch of units
units = []
trees = []

for i in range(50):
    x = random.randint(100, 3900)
    y = random.randint(100, 3900)
    units.append(GameSprite("assets/images/sprites/knight.png", x, y))

for i in range(200):
    x = random.randint(0, 4096)
    y = random.randint(0, 4096)
    trees.append(GameSprite("assets/images/sprites/tree.png", x, y))

# Background tiles — manual grid rendering
bg_tile = pygame.image.load("assets/images/backgrounds/grass.png").convert()
TILE_SIZE = 64


def draw_background(cam):
    """Draw only visible tiles — manual calculation."""
    start_col = cam.x // TILE_SIZE
    start_row = cam.y // TILE_SIZE
    end_col = (cam.x + SCREEN_W) // TILE_SIZE + 1
    end_row = (cam.y + SCREEN_H) // TILE_SIZE + 1

    for row in range(start_row, end_row):
        for col in range(start_col, end_col):
            world_x = col * TILE_SIZE
            world_y = row * TILE_SIZE
            sx, sy = cam.apply(world_x, world_y)
            screen.blit(bg_tile, (sx, sy))


# Player
player = GameSprite("assets/images/sprites/player.png", 2048, 2048)

# === Main loop ===
running = True
while running:
    dt = clock.tick(30) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            # Click to move — convert screen pos to world pos
            wx, wy = camera.screen_to_world(*event.pos)
            player.x = wx  # instant move (no tween system)
            player.y = wy

    # Edge scroll
    mx, my = pygame.mouse.get_pos()
    camera.edge_scroll(mx, my, 8)

    # Camera follows player
    camera.center_on(player.x, player.y)

    # Draw
    screen.fill((0, 0, 0))
    draw_background(camera)

    # Y-sort: combine all drawable objects, sort by y, draw in order.
    # This is O(n log n) every frame. With layers it's worse —
    # trees and units need to interleave based on y, not draw in fixed order.
    all_sprites = [s for s in trees + units + [player] if s.alive]
    all_sprites.sort(key=lambda s: s.y)
    for sprite in all_sprites:
        sprite.draw(screen, camera)

    pygame.display.flip()

pygame.quit()

# What you built manually:
# - Camera with scroll, clamp, coordinate conversion, edge scroll
# - Sprite class with manual anchoring and frustum culling
# - Y-sort across all sprites every frame (no layer system)
# - Background tile rendering with visibility optimization
# - Click-to-world coordinate conversion
# ~130 lines, and this has: no animation, no layer interleaving,
# no smooth camera, no zoom, no sprite batching (200 trees = 200 blit calls).
