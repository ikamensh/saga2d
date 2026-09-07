"""Shardbound's icon meanings and compact numeric readouts."""
from pathlib import Path

from saga2d import Image, Label, Row

from eador.style import TEXT


_IMAGES = Path(__file__).resolve().parent / 'assets' / 'images' / 'icons'
_NAMES = {
    'gold': 'Gold', 'crystals': 'Crystals', 'income': 'Income', 'upkeep': 'Upkeep',
    'level': 'Level', 'xp': 'Experience', 'actions': 'Campaign actions',
    'health': 'Health', 'mana': 'Mana', 'attack': 'Attack', 'defense': 'Defense',
    'move': 'Movement', 'fly': 'Flight', 'range': 'Attack range',
}


def icon_path(name):
    return str(_IMAGES / f'{name}.png')


def metric(name, value, *, width, size=14, color=TEXT, detail=None):
    """A readable value and a distinct symbol; hovering either explains its meaning."""
    size = round(size)
    icon_size = round(size * 1.4)
    tooltip = f'{_NAMES[name]}: {value}' + (f'. {detail}' if detail else '')
    return Row(Image(icon_path(name), width=icon_size, height=icon_size),
               Label(str(value), width=width - icon_size - 8, height=icon_size,
                     font='Verdana', font_size=size, text_color=color),
               width=width, spacing=8, tooltip=tooltip)
