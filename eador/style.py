"""Shardbound's ink, brass and verdigris palette."""

from saga2d import Style, TextStyle, Theme

INK = (17, 27, 32, 255)
PANEL = (23, 36, 41, 255)
LINE = (67, 81, 79, 255)
TEXT = (237, 230, 207, 255)
MUTED = (158, 177, 173, 255)
GOLD = (224, 188, 112, 255)
TEAL = (105, 205, 177, 255)
RED = (228, 130, 112, 255)
BLUE = (135, 174, 221, 255)

PRIMARY = Style(background_color=(46, 94, 81, 255), hover_color=(61, 117, 100, 255),
                border_color=TEAL, border_width=1)
DANGER = Style(background_color=(82, 49, 45, 255), hover_color=(113, 64, 54, 255),
               border_color=RED, border_width=1)


def build_theme() -> Theme:
    return Theme(
        font="Verdana", font_size=14, text_color=TEXT,
        panel_background_color=PANEL, panel_border_color=LINE, panel_border_width=1,
        button_background_color=(34, 50, 54, 255), button_hover_color=(51, 70, 72, 255),
        button_press_color=(68, 92, 88, 255), button_text_color=TEXT,
        button_font_size=13, button_radius=3, button_min_width=70,
        button_disabled_text_color=(104, 123, 124, 255),
        keycap_color=(255, 255, 255, 14), keycap_text_color=MUTED, keycap_font_size=10,
        text_styles={"title": TextStyle(36, TEXT, "Georgia"),
                     "heading": TextStyle(22, TEXT, "Georgia"),
                     "caption": TextStyle(11, MUTED), "body": TextStyle(14, TEXT)},
    )
