"""Shardbound's portrait frames, icon meanings and compact numeric readouts."""
from pathlib import Path

from saga2d import Column, Image, Label, Row, Style

from eador.style import INK, LINE, TEXT


_IMAGES = Path(__file__).resolve().parent / 'assets' / 'images' / 'icons'
_NAMES = {
    'gold': 'Gold', 'crystals': 'Crystals', 'income': 'Income', 'upkeep': 'Upkeep',
    'level': 'Level', 'xp': 'Experience', 'actions': 'Campaign actions',
    'health': 'Health', 'mana': 'Mana', 'attack': 'Attack', 'defense': 'Defense',
    'move': 'Movement', 'fly': 'Flight', 'range': 'Attack range',
}


def icon_path(name):
    return str(_IMAGES / f'{name}.png')


def hero_portrait_path(hero_class):
    return str(_IMAGES.parent / 'heroes' / f'{hero_class.lower()}.png')


def hero_portrait(hero_class, size):
    """A framed original portrait participating in the ordinary measured layout."""
    return Column(Image(hero_portrait_path(hero_class), width=size - 6, height=size - 6,
                        tooltip=hero_class),
                  style=Style(padding=3, border_color=LINE, border_width=1, background_color=INK))


def metric(name, value, *, width, size=14, color=TEXT, detail=None):
    """A readable value and a distinct symbol; hovering either explains its meaning."""
    size = round(size)
    icon_size = round(size * 1.4)
    tooltip = f'{_NAMES[name]}: {value}' + (f'. {detail}' if detail else '')
    return Row(Image(icon_path(name), width=icon_size, height=icon_size),
               Label(str(value), width=width - icon_size - 8, height=icon_size,
                     font='Verdana', font_size=size, text_color=color),
               width=width, spacing=8, tooltip=tooltip)
