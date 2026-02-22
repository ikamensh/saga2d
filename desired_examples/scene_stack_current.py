"""
Scene management: title screen → game world → inventory overlay → back.
This is what you write TODAY with pygame. There is no scene stack.
"""
import pygame
import sys

pygame.init()
screen = pygame.display.set_mode((1024, 768))
clock = pygame.time.Clock()

# === The core problem: pygame has no scene concept at all ===
# You track "which screen am I on" with a variable and branch everywhere.

current_scene = "title"
scene_history = []  # if you want "back", you build this yourself


# === Each "scene" is a pair of functions, or a class you invented ===

# --- Title screen ---
title_font = pygame.font.SysFont("serif", 48)
menu_font = pygame.font.SysFont("serif", 24)


def draw_title():
    screen.fill((20, 20, 40))
    text = title_font.render("My Game", True, (255, 255, 255))
    screen.blit(text, text.get_rect(center=(512, 200)))

    hint = menu_font.render("Press ENTER to start, ESC to quit", True, (180, 180, 180))
    screen.blit(hint, hint.get_rect(center=(512, 400)))


def handle_title(event):
    global current_scene
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_RETURN:
            current_scene = "game"
            # No on_enter/on_exit hooks — you manually init state here
            init_game_world()
        elif event.key == pygame.K_ESCAPE:
            pygame.quit()
            sys.exit()


# --- Game world ---
player_x, player_y = 400, 300
world_items = []


def init_game_world():
    global player_x, player_y, world_items
    player_x, player_y = 400, 300
    world_items = [{"name": "Sword", "x": 200, "y": 200},
                   {"name": "Shield", "x": 600, "y": 400}]


def draw_game():
    screen.fill((30, 60, 30))
    # Draw player
    pygame.draw.circle(screen, (200, 200, 50), (player_x, player_y), 20)
    # Draw items
    for item in world_items:
        pygame.draw.rect(screen, (150, 150, 255),
                         (item["x"] - 10, item["y"] - 10, 20, 20))
    # HUD
    hud_text = menu_font.render("I=Inventory  ESC=Menu", True, (200, 200, 200))
    screen.blit(hud_text, (10, 10))


def handle_game(event):
    global current_scene, player_x, player_y
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            # "Push" pause menu — but there's no push. You set a flag.
            scene_history.append("game")
            current_scene = "pause_menu"
        elif event.key == pygame.K_i:
            # "Push" inventory — same problem
            scene_history.append("game")
            current_scene = "inventory"
        elif event.key == pygame.K_LEFT:
            player_x -= 20
        elif event.key == pygame.K_RIGHT:
            player_x += 20


# --- Pause menu (overlays the game) ---
def draw_pause():
    # Want to draw game underneath? You have to call draw_game() first.
    # But draw_game() doesn't know it's "underneath" — no transparency concept.
    draw_game()
    # Manual overlay
    overlay = pygame.Surface((1024, 768), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 128))
    screen.blit(overlay, (0, 0))
    text = title_font.render("PAUSED", True, (255, 255, 255))
    screen.blit(text, text.get_rect(center=(512, 300)))
    hint = menu_font.render("ESC to resume, Q to quit", True, (180, 180, 180))
    screen.blit(hint, hint.get_rect(center=(512, 380)))


def handle_pause(event):
    global current_scene
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            # "Pop" — go back
            current_scene = scene_history.pop() if scene_history else "title"
        elif event.key == pygame.K_q:
            current_scene = "title"
            scene_history.clear()


# --- Inventory (also overlays the game) ---
inventory = ["Health Potion", "Mana Potion", "Key"]
selected_item = 0


def draw_inventory():
    draw_game()  # draw game underneath — again, manually
    # Manual overlay
    overlay = pygame.Surface((1024, 768), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    screen.blit(overlay, (0, 0))
    # Manual panel
    panel_rect = pygame.Rect(262, 134, 500, 500)
    pygame.draw.rect(screen, (60, 40, 20), panel_rect)
    pygame.draw.rect(screen, (150, 120, 80), panel_rect, width=3)
    # Title
    title = menu_font.render("Inventory", True, (220, 200, 160))
    screen.blit(title, (panel_rect.x + 20, panel_rect.y + 20))
    # Items — manual list rendering with selection highlight
    for i, item_name in enumerate(inventory):
        y = panel_rect.y + 70 + i * 30
        color = (255, 255, 100) if i == selected_item else (200, 200, 200)
        text = menu_font.render(item_name, True, color)
        screen.blit(text, (panel_rect.x + 30, y))


def handle_inventory(event):
    global current_scene, selected_item
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE or event.key == pygame.K_i:
            current_scene = scene_history.pop() if scene_history else "game"
        elif event.key == pygame.K_UP:
            selected_item = max(0, selected_item - 1)
        elif event.key == pygame.K_DOWN:
            selected_item = min(len(inventory) - 1, selected_item + 1)


# === The main loop: one giant dispatcher ===
# Every new scene adds two more branches here. This doesn't scale.

SCENES = {
    "title": (draw_title, handle_title),
    "game": (draw_game, handle_game),
    "pause_menu": (draw_pause, handle_pause),
    "inventory": (draw_inventory, handle_inventory),
}

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        else:
            draw_fn, handle_fn = SCENES[current_scene]
            handle_fn(event)

    draw_fn, _ = SCENES[current_scene]
    draw_fn()
    pygame.display.flip()
    clock.tick(30)

pygame.quit()

# Problems demonstrated:
# 1. No scene lifecycle (on_enter, on_exit, on_reveal) — state init is ad hoc
# 2. No scene stack — "push" is append-to-list + set-string
# 3. Transparent overlays require manually drawing the scene below
# 4. No "pause_below" concept — game world keeps/doesn't keep updating? You decide per-frame.
# 5. Every scene's state is global variables
# 6. The main loop is a dispatcher that grows with every screen
# 7. ~150 lines for 4 trivial screens with no real content
