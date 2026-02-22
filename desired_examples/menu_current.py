"""
Main menu with 4 buttons, background image, custom font, hover effects.
This is what you write TODAY with pygame.
"""
import pygame
import sys

pygame.init()
pygame.mixer.init()

# Window setup — pygame.SCALED handles DPI scaling since 2.0
screen = pygame.display.set_mode((1920, 1080), pygame.FULLSCREEN | pygame.SCALED)
pygame.display.set_caption("Chronicles of the Realm")
clock = pygame.time.Clock()

# Load assets manually, handle errors yourself
try:
    background = pygame.image.load("assets/images/backgrounds/parchment.png").convert()
    background = pygame.transform.scale(background, (1920, 1080))
except pygame.error as e:
    print(f"Could not load background: {e}")
    sys.exit(1)

try:
    font_large = pygame.font.Font("assets/fonts/medieval.ttf", 64)
    font_button = pygame.font.Font("assets/fonts/medieval.ttf", 32)
except pygame.error:
    font_large = pygame.font.SysFont("serif", 64)
    font_button = pygame.font.SysFont("serif", 32)

# Button "system" — you build this from scratch every time
BUTTON_COLOR = (120, 80, 40)
BUTTON_HOVER = (160, 110, 60)
BUTTON_TEXT = (220, 200, 160)
BUTTON_WIDTH = 300
BUTTON_HEIGHT = 50
BUTTON_SPACING = 20

buttons = [
    {"text": "New Game", "action": "new_game"},
    {"text": "Load Game", "action": "load_game"},
    {"text": "Settings", "action": "settings"},
    {"text": "Quit", "action": "quit"},
]

# Calculate button positions manually
total_height = len(buttons) * BUTTON_HEIGHT + (len(buttons) - 1) * BUTTON_SPACING
start_y = (1080 - total_height) // 2 + 60  # offset for title

button_rects = []
for i, btn in enumerate(buttons):
    x = (1920 - BUTTON_WIDTH) // 2
    y = start_y + i * (BUTTON_HEIGHT + BUTTON_SPACING)
    button_rects.append(pygame.Rect(x, y, BUTTON_WIDTH, BUTTON_HEIGHT))

# Render title — pygame renders text to a surface, then you blit it
title_surface = font_large.render("Chronicles of the Realm", True, BUTTON_TEXT)
title_rect = title_surface.get_rect(center=(1920 // 2, start_y - 80))

# Play menu music — manual player management
try:
    pygame.mixer.music.load("assets/music/menu_theme.ogg")
    pygame.mixer.music.set_volume(0.5)
    pygame.mixer.music.play(-1)  # loop
except pygame.error:
    pass  # silently fail, no channel system

# Hover sound — load manually
try:
    hover_sound = pygame.mixer.Sound("assets/sounds/ui_hover.wav")
    hover_sound.set_volume(0.3)
except pygame.error:
    hover_sound = None

# State tracking — you manage this yourself
hovered_button = -1
previous_hovered = -1
current_screen = "menu"  # no scene stack — you track state with strings/flags


def draw_menu():
    screen.blit(background, (0, 0))
    screen.blit(title_surface, title_rect)

    mouse_pos = pygame.mouse.get_pos()

    for i, (btn, rect) in enumerate(zip(buttons, button_rects)):
        # Hover detection — manual rect check
        is_hovered = rect.collidepoint(mouse_pos)
        color = BUTTON_HOVER if is_hovered else BUTTON_COLOR

        # Draw button background — no 9-slice, no image, just a rect
        pygame.draw.rect(screen, color, rect, border_radius=8)
        pygame.draw.rect(screen, BUTTON_TEXT, rect, width=2, border_radius=8)

        # Render button text — centered manually
        text_surf = font_button.render(btn["text"], True, BUTTON_TEXT)
        text_rect = text_surf.get_rect(center=rect.center)
        screen.blit(text_surf, text_rect)


def handle_click(pos):
    for i, rect in enumerate(button_rects):
        if rect.collidepoint(pos):
            action = buttons[i]["action"]
            if action == "quit":
                pygame.quit()
                sys.exit()
            elif action == "new_game":
                # Now you need an entirely separate draw/event loop for the game...
                # There's no scene stack. You either:
                # 1. Set a flag and branch in the main loop (spaghetti)
                # 2. Call a function that has its own event loop (can't go back easily)
                # 3. Build your own scene manager from scratch
                pass
            elif action == "settings":
                # Same problem — how do you "push" a settings screen?
                # In pygame: you don't. You write another loop.
                pass


# Main loop — you write this every time
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                handle_click(event.pos)
        elif event.type == pygame.MOUSEMOTION:
            # Hover sound — manual tracking of hover state changes
            new_hovered = -1
            for i, rect in enumerate(button_rects):
                if rect.collidepoint(event.pos):
                    new_hovered = i
                    break
            if new_hovered != hovered_button and new_hovered >= 0:
                if hover_sound:
                    hover_sound.play()
            hovered_button = new_hovered

    draw_menu()
    pygame.display.flip()
    clock.tick(30)

pygame.quit()

# Lines of actual game logic: ~5 (the button actions)
# Lines of engine plumbing: ~100
# And this doesn't even have: transitions, themed buttons, scene management,
# or a way to go to other screens without building your own scene system.
