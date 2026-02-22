"""
A styled dialog box with a character portrait, text, and choice buttons.
Think: Baldur's Gate dialogue, or Heroes 2 event popup.
This is what you write TODAY with pygame.
"""
import pygame

pygame.init()
screen = pygame.display.set_mode((1024, 768))
clock = pygame.time.Clock()
font = pygame.font.SysFont("serif", 20)
font_large = pygame.font.SysFont("serif", 28)


# === No UI component system — you draw rectangles ===

class DialogBox:
    def __init__(self, speaker, portrait_path, text, choices):
        self.speaker = speaker
        self.portrait = pygame.image.load(portrait_path).convert_alpha()
        self.portrait = pygame.transform.scale(self.portrait, (96, 96))
        self.text = text
        self.choices = choices
        self.selected = 0
        self.on_choice = None

        # Layout — all manual math
        self.width = 600
        self.height = 300
        self.x = (1024 - self.width) // 2
        self.y = (768 - self.height) // 2

        # Word wrap — pygame has no built-in word wrap for fonts
        self.wrapped_lines = self._wrap_text(text, self.width - 140)

        # Typewriter effect — manual character reveal
        self.revealed_chars = 0
        self.chars_per_second = 30
        self.char_timer = 0
        self.total_chars = sum(len(line) for line in self.wrapped_lines)
        self.fully_revealed = False

    def _wrap_text(self, text, max_width):
        """Word wrap. Pygame doesn't do this. You write it every time."""
        words = text.split()
        lines = []
        current_line = ""
        for word in words:
            test_line = current_line + " " + word if current_line else word
            test_surface = font.render(test_line, True, (0, 0, 0))
            if test_surface.get_width() > max_width:
                if current_line:
                    lines.append(current_line)
                current_line = word
            else:
                current_line = test_line
        if current_line:
            lines.append(current_line)
        return lines

    def update(self, dt):
        if not self.fully_revealed:
            self.char_timer += dt
            self.revealed_chars = int(self.char_timer * self.chars_per_second)
            if self.revealed_chars >= self.total_chars:
                self.revealed_chars = self.total_chars
                self.fully_revealed = True

    def draw(self, surface):
        # Panel background — manual
        panel_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        pygame.draw.rect(surface, (40, 30, 20), panel_rect)
        pygame.draw.rect(surface, (120, 100, 60), panel_rect, width=3)

        # Portrait — manual positioning
        portrait_x = self.x + 15
        portrait_y = self.y + 15
        # Portrait border
        pygame.draw.rect(surface, (120, 100, 60),
                         (portrait_x - 2, portrait_y - 2, 100, 100), width=2)
        surface.blit(self.portrait, (portrait_x, portrait_y))

        # Speaker name — manual positioning
        name_surf = font_large.render(self.speaker, True, (220, 200, 140))
        surface.blit(name_surf, (portrait_x + 110, portrait_y))

        # Text with typewriter — manual character counting across lines
        text_x = portrait_x + 110
        text_y = portrait_y + 35
        chars_shown = 0
        for line in self.wrapped_lines:
            if chars_shown >= self.revealed_chars:
                break
            remaining = self.revealed_chars - chars_shown
            visible_text = line[:remaining]
            text_surf = font.render(visible_text, True, (200, 200, 180))
            surface.blit(text_surf, (text_x, text_y))
            text_y += 24
            chars_shown += len(line)

        # Choice buttons — only show when text is fully revealed
        if self.fully_revealed and self.choices:
            choice_y = self.y + self.height - 30 * len(self.choices) - 15
            for i, choice in enumerate(self.choices):
                color = (255, 255, 100) if i == self.selected else (180, 180, 180)
                prefix = "> " if i == self.selected else "  "
                choice_surf = font.render(prefix + choice, True, color)
                surface.blit(choice_surf, (text_x, choice_y + i * 30))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if not self.fully_revealed:
                # Skip to end on any key
                self.fully_revealed = True
                self.revealed_chars = self.total_chars
                return True
            if event.key == pygame.K_UP:
                self.selected = max(0, self.selected - 1)
            elif event.key == pygame.K_DOWN:
                self.selected = min(len(self.choices) - 1, self.selected + 1)
            elif event.key == pygame.K_RETURN:
                if self.on_choice:
                    self.on_choice(self.selected)
                return True
        return False


# Usage
dialog = DialogBox(
    speaker="Elder Sage",
    portrait_path="assets/images/sprites/sage_portrait.png",
    text="The ancient prophecy speaks of a hero who will rise from the ashes. "
         "The three kingdoms have fallen to darkness. Only you can restore the light. "
         "But first, you must choose your path wisely.",
    choices=["I will fight for honor.", "Tell me more about the prophecy.", "I'm not interested."],
)
dialog.on_choice = lambda i: print(f"Chose: {i}")

running = True
while running:
    dt = clock.tick(30) / 1000.0
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        else:
            dialog.handle_event(event)
    dialog.update(dt)
    screen.fill((0, 0, 0))
    dialog.draw(screen)
    pygame.display.flip()

pygame.quit()

# 130 lines for ONE dialog box. And it has:
# - Manual word wrapping (every project writes this differently)
# - Manual typewriter character counting across wrapped lines
# - Manual layout arithmetic for every element
# - Manual keyboard navigation with selection tracking
# - No theming (colors hardcoded)
# - No transitions (no fade in/out)
# - No reuse (copy-paste this class to every project)
