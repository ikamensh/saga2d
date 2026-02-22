"""
Animated unit: walks to a target, plays attack animation, then idles.
This is what you write TODAY with pygame.
"""
import pygame
from pygame.math import Vector2

pygame.init()
screen = pygame.display.set_mode((1024, 768))
clock = pygame.time.Clock()


# === Sprite sheet loading — you write this every time ===

def load_spritesheet(path, frame_width, frame_height):
    """Cut a sprite sheet into frames. No standard way to do this."""
    sheet = pygame.image.load(path).convert_alpha()
    frames = []
    cols = sheet.get_width() // frame_width
    rows = sheet.get_height() // frame_height
    for row in range(rows):
        for col in range(cols):
            rect = pygame.Rect(col * frame_width, row * frame_height,
                               frame_width, frame_height)
            frame = sheet.subsurface(rect).copy()
            frames.append(frame)
    return frames


# Load all animation frames manually
walk_frames = load_spritesheet("assets/images/sprites/knight_walk.png", 64, 64)
attack_frames = load_spritesheet("assets/images/sprites/knight_attack.png", 64, 64)
idle_frames = load_spritesheet("assets/images/sprites/knight_idle.png", 64, 64)
death_frames = load_spritesheet("assets/images/sprites/knight_death.png", 64, 64)


# === Animation state machine — you build this from scratch ===

class AnimatedUnit:
    def __init__(self, x, y):
        self.pos = Vector2(x, y)
        self.frames = idle_frames
        self.frame_index = 0
        self.frame_timer = 0
        self.frame_duration = 0.15
        self.loop = True
        self.on_animation_complete = None

        # Movement
        self.target = None
        self.move_speed = 200  # pixels per second
        self.on_arrive = None

    def play(self, frames, duration=0.15, loop=True, on_complete=None):
        self.frames = frames
        self.frame_index = 0
        self.frame_timer = 0
        self.frame_duration = duration
        self.loop = loop
        self.on_animation_complete = on_complete

    def move_to(self, tx, ty, on_arrive=None):
        self.target = Vector2(tx, ty)
        self.on_arrive = on_arrive
        self.play(walk_frames, loop=True)

    def update(self, dt):
        # Animation frame advance — manual timer logic
        self.frame_timer += dt
        if self.frame_timer >= self.frame_duration:
            self.frame_timer -= self.frame_duration
            self.frame_index += 1
            if self.frame_index >= len(self.frames):
                if self.loop:
                    self.frame_index = 0
                else:
                    self.frame_index = len(self.frames) - 1
                    if self.on_animation_complete:
                        callback = self.on_animation_complete
                        self.on_animation_complete = None
                        callback()

        # Movement — Vector2 helps with the math, but you still manage it yourself
        if self.target is not None:
            diff = self.target - self.pos
            dist = diff.length()
            if dist < self.move_speed * dt:
                self.pos = Vector2(self.target)
                self.target = None
                if self.on_arrive:
                    callback = self.on_arrive
                    self.on_arrive = None
                    callback()
            else:
                self.pos += diff.normalize() * self.move_speed * dt

    def draw(self, surface):
        frame = self.frames[self.frame_index]
        # Bottom-center anchor — manual offset
        rect = frame.get_rect(midbottom=(int(self.pos.x), int(self.pos.y)))
        surface.blit(frame, rect)


# Create a unit and make it walk, attack, then idle
knight = AnimatedUnit(100, 400)


def do_attack():
    """After arriving, play attack, then idle."""
    knight.play(attack_frames, duration=0.1, loop=False, on_complete=go_idle)


def go_idle():
    knight.play(idle_frames, loop=True)


# Start the sequence — walk, then attack, then idle via callbacks
knight.move_to(500, 400, on_arrive=do_attack)

# === Game loop ===
running = True
while running:
    dt = clock.tick(30) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    knight.update(dt)

    screen.fill((30, 30, 30))
    knight.draw(screen)
    pygame.display.flip()

pygame.quit()

# You wrote: sprite sheet loader, animation player with timers, movement with
# Vector2, callback chaining, anchored drawing.
# ~90 lines of plumbing for one knight walking and attacking.
# Every game reimplements this — sprite sheets, frame timers, move-toward logic,
# callback sequencing. pygame.math.Vector2 helps with the math but not the structure.
