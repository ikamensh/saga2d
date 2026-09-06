"""Tribes' look: palette, theme and the component styles the scenes share.

Text is saga2d's bundled Nunito: regular for body copy, SemiBold for HUD
numbers and headings, ExtraBold for titles and the hero.  Panels are dark
translucent slabs with a hairline border and rounded corners; hotkeys
appear as keycaps.
"""

from __future__ import annotations

from dataclasses import replace

from saga2d import Style, TextStyle, Theme, fonts

Color = tuple[int, int, int, int]

REGULAR, SEMIBOLD, EXTRABOLD = fonts.REGULAR, fonts.SEMIBOLD, fonts.EXTRABOLD

GOLD: Color = (255, 224, 120, 255)
TEXT: Color = (240, 243, 250, 255)
BODY: Color = (224, 229, 240, 255)
MUTED: Color = (178, 186, 205, 255)
DIM: Color = (142, 150, 174, 255)
GOOD: Color = (130, 225, 140, 255)
BAD: Color = (240, 150, 130, 255)
PANEL_BG: Color = (16, 20, 32, 225)
HAIRLINE: Color = (255, 255, 255, 30)

PANEL_STYLE = Style(background_color=PANEL_BG, border_color=HAIRLINE, border_width=1, padding=14, radius=12)
OVERLAY_STYLE = Style(background_color=(16, 20, 32, 242), border_color=HAIRLINE, border_width=1, padding=22, radius=16)
RESULTS_STYLE = replace(OVERLAY_STYLE, background_color=(16, 20, 32, 255), padding=16)
GHOST_BUTTON = Style(font=SEMIBOLD, background_color=(255, 255, 255, 22), hover_color=(255, 255, 255, 48), press_color=(255, 255, 255, 84),
                     border_color=(255, 255, 255, 42), border_width=1, padding=8, radius=8)
ACTION_BUTTON = Style(font=SEMIBOLD, background_color=(58, 122, 224, 255), hover_color=(86, 148, 242, 255), press_color=(140, 190, 255, 255),
                      border_color=(150, 195, 255, 110), border_width=1, padding=8, radius=8)
DANGER_BUTTON = Style(font=SEMIBOLD, background_color=(198, 70, 62, 255), hover_color=(222, 94, 84, 255), press_color=(255, 140, 130, 255),
                      border_color=(255, 150, 140, 110), border_width=1, padding=8, radius=8)
MENU_BUTTON = Style(font=SEMIBOLD, background_color=(26, 32, 52, 235), hover_color=(44, 54, 84, 255), press_color=(70, 92, 144, 255),
                    border_color=(255, 255, 255, 50), border_width=1, padding=10, radius=10)


def build_theme() -> Theme:
    return Theme(
        font=REGULAR, font_size=16, text_color=TEXT,
        panel_background_color=PANEL_BG, panel_border_color=HAIRLINE, panel_border_width=1, panel_padding=14, panel_radius=12,
        button_background_color=(255, 255, 255, 22), button_hover_color=(255, 255, 255, 48), button_press_color=(255, 255, 255, 84),
        button_disabled_color=(255, 255, 255, 8), button_text_color=TEXT, button_disabled_text_color=(255, 255, 255, 84),
        button_padding=8, button_font_size=15, button_min_width=90, button_radius=8,
        keycap_color=(255, 255, 255, 40), keycap_text_color=TEXT, keycap_font=SEMIBOLD, keycap_font_size=11,
        progressbar_color=GOLD, progressbar_bg_color=(0, 0, 0, 120),
        text_styles={
            "title": TextStyle(22, GOLD, EXTRABOLD),
            "heading": TextStyle(18, TEXT, SEMIBOLD),
            "hud": TextStyle(17, TEXT, SEMIBOLD),
            "body": TextStyle(15, BODY, REGULAR),
            "sub": TextStyle(13, MUTED, REGULAR),
            "caption": TextStyle(12, DIM, REGULAR),
            "city": TextStyle(12, (255, 255, 255, 255), SEMIBOLD),
            "banner": TextStyle(40, (255, 255, 255, 255), EXTRABOLD),
            "banner_sub": TextStyle(17, (255, 255, 255, 255), SEMIBOLD),
            "hero": TextStyle(88, GOLD, EXTRABOLD),
            "hero_sub": TextStyle(19, (214, 220, 238, 255), REGULAR),
            "floating": TextStyle(18, (255, 255, 255, 255), EXTRABOLD),
        },
    )
