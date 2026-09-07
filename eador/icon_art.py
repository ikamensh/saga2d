"""Original Shardbound ink-and-brass icons, composed offline without fonts.

The game loads the prebuilt 96px PNGs. Broad strokes and a quiet ink keyline
keep these silhouettes legible at 24px against both panels and terrain.
"""
from __future__ import annotations

import math

from PIL import Image, ImageDraw


GENERATOR_VERSION = 1
SIZE = 96
SCALE = 4
INK = (17, 27, 32, 255)
BRASS = (224, 188, 112, 255)
CREAM = (237, 230, 207, 255)
TEAL = (105, 205, 177, 255)
RED = (228, 130, 112, 255)
SHADE = (147, 121, 76, 255)

ICONS = {
    'guide': 'Help: a hand-drawn question mark within a ring.',
    'hero': 'Hero: a crested helmet.',
    'codex': 'Codex: an open book.',
    'text_size': 'Reading size: hand-drawn uppercase A and lowercase a; no font.',
    'save': 'Save: downward arrow into a tray.',
    'load': 'Load: upward arrow out of a tray.',
    'settings': 'Settings: an eight-tooth gear.',
    'gold': 'Gold: an engraved brass coin.',
    'crystals': 'Crystals: a faceted teal crystal.',
    'health': 'Health: a teal heart.',
    'mana': 'Mana: an arcane droplet with a brass spark.',
    'attack': 'Attack: an upright sword.',
    'defense': 'Defense: a quartered shield.',
    'move': 'Ground movement: a boot.',
    'fly': 'Flying movement: a swept, feathered wing.',
    'range': 'Range: an arrow crossing a target.',
    'actions': 'Remaining actions: an hourglass.',
    'income': 'Income: a coin with an upward teal arrow.',
    'upkeep': 'Upkeep: a coin with a downward red arrow.',
    'level': 'Level: two ascending chevrons.',
    'xp': 'Experience: a five-pointed star.',
    'build': 'Build: a hammer.',
    'recruit': 'Recruit: a helmet with a plus sign.',
    'explore': 'Explore: a compass rose.',
    'travel': 'Travel: a boot with a route arrow.',
    'end_turn': 'End turn: a sun and the continuing turn arrow.',
    'bolt': 'Arcane Bolt: a sharp lightning stroke.',
    'heal': 'Heal: a teal medical cross.',
    'guard': 'Guard: a shield above a firm defensive bar.',
    'retreat': 'Retreat: a leftward arrow leaving a doorway.',
    'auto_play': 'Auto-play: two advancing triangles.',
    'log': 'Battle log: an unfurled scroll.',
    'campaign': 'Campaign: a folded map and destination.',
    'rival': 'Rival: a red war banner.',
}


class Pen:
    """Small drawing vocabulary, in the final icon's 96px coordinate space."""

    def __init__(self):
        self.image = Image.new('RGBA', (SIZE * SCALE, SIZE * SCALE))
        self.draw = ImageDraw.Draw(self.image)

    @staticmethod
    def _points(points):
        return [(round(x * SCALE), round(y * SCALE)) for x, y in points]

    def line(self, points, color=BRASS, width=7, *, keyline=True):
        points = self._points(points)
        for paint, thickness in ((INK, width + 4), (color, width)) if keyline else ((color, width),):
            self.draw.line(points, fill=paint, width=round(thickness * SCALE), joint='curve')
            radius = thickness * SCALE / 2
            for x, y in (points[0], points[-1]):
                self.draw.ellipse((round(x-radius), round(y-radius), round(x+radius), round(y+radius)), fill=paint)

    def polygon(self, points, color=BRASS, *, keyline=True):
        points = self._points(points)
        self.draw.polygon(points, fill=color)
        if keyline:
            self.draw.line(points + points[:1], fill=INK, width=4 * SCALE, joint='curve')

    def circle(self, x, y, radius, color=None, *, stroke=BRASS, width=6):
        if color is not None:
            self.draw.ellipse(tuple(round(v * SCALE) for v in
                                    (x-radius, y-radius, x+radius, y+radius)),
                              fill=color, outline=INK, width=3 * SCALE)
        else:
            self.arc(x, y, radius, 0, 360, stroke, width)

    def arc(self, x, y, radius, start, stop, color=BRASS, width=6):
        points = [(x + math.cos(math.radians(start + (stop-start)*i/48))*radius,
                   y + math.sin(math.radians(start + (stop-start)*i/48))*radius) for i in range(49)]
        self.line(points, color, width)


def _star(pen, x=48, y=48, radius=35, color=BRASS):
    pen.polygon([(x + math.sin(i*math.pi/5)*(radius if i%2 == 0 else radius*.44),
                  y - math.cos(i*math.pi/5)*(radius if i%2 == 0 else radius*.44))
                 for i in range(10)], color)


def _coin(pen, x=48, y=48, radius=34):
    pen.circle(x, y, radius, BRASS)
    pen.circle(x, y, radius*.68, stroke=SHADE, width=3)
    pen.polygon([(x,y-radius*.43),(x+radius*.28,y),(x,y+radius*.43),(x-radius*.28,y)], INK, keyline=False)
    pen.arc(x, y, radius*.84, 205, 286, CREAM, 3)


def _helmet(pen, *, small=False):
    scale, dx, dy = (.78, -5, 3) if small else (1, 0, 0)
    def points(values):
        return [(48+(x-48)*scale+dx, 48+(y-48)*scale+dy) for x,y in values]
    pen.polygon(points([(24,74),(22,41),(28,25),(43,18),(60,20),(74,32),
                        (77,57),(64,64),(61,80),(47,76),(45,58),(33,59),(34,78)]))
    pen.polygon(points([(47,20),(60,20),(74,32),(77,57),(64,64),(61,80),
                        (47,76),(45,58)]), SHADE, keyline=False)
    pen.line(points([(31,44),(47,47),(67,42)]), INK, 7*scale, keyline=False)
    pen.line(points([(48,48),(48,62)]), CREAM, 5*scale)
    pen.line(points([(37,22),(38,13),(55,12),(65,20)]), TEAL, 7*scale)


def _shield(pen, *, raised=False):
    dy = -6 if raised else 0
    pen.polygon([(18,22+dy),(48,14+dy),(78,22+dy),(75,54+dy),
                 (63,71+dy),(48,82+dy),(33,71+dy),(21,54+dy)])
    pen.polygon([(48,22+dy),(69,28+dy),(67,52+dy),(57,67+dy),(48,74+dy)], TEAL, keyline=False)
    pen.line([(48,22+dy),(48,72+dy)], INK, 4, keyline=False)


def _boot(pen, *, small=False):
    dx, dy, scale = (-8, 5, .80) if small else (0, 0, 1)
    def points(values):
        return [(48+(x-48)*scale+dx, 48+(y-48)*scale+dy) for x,y in values]
    pen.polygon(points([(30,15),(61,15),(58,51),(76,59),(82,73),(77,81),
                        (22,81),(20,62),(30,52)]))
    pen.polygon(points([(22,71),(79,71),(77,81),(22,81)]), SHADE, keyline=False)
    pen.line(points([(34,28),(56,28)]), INK, 5*scale, keyline=False)
    pen.line(points([(32,40),(53,40)]), TEAL, 5*scale)
    pen.line(points([(30,59),(38,65)]), CREAM, 4*scale)


def _plus(pen, x, y, size=12, color=TEAL):
    pen.line([(x-size,y),(x+size,y)], color, 9)
    pen.line([(x,y-size),(x,y+size)], color, 9)


def _draw(name, pen):
    if name == 'guide':
        pen.circle(48,48,34)
        pen.line([(36,36),(37,29),(46,25),(56,28),(60,35),(57,43),(48,49),(48,54)], CREAM, 7)
        pen.circle(48,68,5,TEAL)
    elif name in ('hero','recruit'):
        _helmet(pen,small=name == 'recruit')
        if name == 'recruit':
            _plus(pen,74,67,11)
    elif name == 'codex':
        pen.polygon([(12,23),(29,19),(48,26),(67,19),(84,23),(84,76),
                     (65,72),(48,79),(30,72),(12,76)])
        pen.polygon([(48,29),(67,24),(79,27),(79,69),(64,66),(48,72)], TEAL, keyline=False)
        pen.line([(48,28),(48,74)], INK, 5, keyline=False)
        for y in (38,51,64):
            pen.line([(21,y),(34,y-1)], INK, 3, keyline=False)
            pen.line([(60,y-1),(73,y)], INK, 3, keyline=False)
    elif name == 'text_size':
        pen.line([(12,76),(29,20),(46,76)], CREAM, 7)
        pen.line([(19,57),(39,57)], CREAM, 6)
        pen.arc(66,61,13,0,360,TEAL,6)
        pen.line([(79,48),(79,76),(85,76)],TEAL,6)
    elif name in ('save','load'):
        pen.line([(19,64),(19,81),(77,81),(77,64)],BRASS,8)
        if name == 'save':
            pen.line([(48,15),(48,61)],TEAL,9)
            pen.line([(31,44),(48,61),(65,44)],TEAL,9)
        else:
            pen.line([(48,62),(48,16)],CREAM,9)
            pen.line([(31,33),(48,16),(65,33)],CREAM,9)
    elif name == 'settings':
        points=[]
        for tooth in range(8):
            for offset,radius in ((-.46,29),(-.24,39),(.24,39),(.46,29)):
                angle=(tooth+offset)*math.tau/8
                points.append((48+math.cos(angle)*radius,48+math.sin(angle)*radius))
        pen.polygon(points)
        pen.circle(48,48,17,INK)
        pen.circle(48,48,9,TEAL)
    elif name in ('gold','income','upkeep'):
        if name == 'gold':
            _coin(pen)
        else:
            _coin(pen,35,49,27)
            color = TEAL if name == 'income' else RED
            start,end = (76,24) if name == 'income' else (24,76)
            pen.line([(73,start),(73,end)],color,8)
            tip_y = end + (15 if end == 24 else -15)
            pen.line([(63,tip_y),(73,end),(84,tip_y)],color,8)
    elif name == 'crystals':
        pen.polygon([(48,9),(73,29),(78,64),(48,88),(18,64),(23,29)],TEAL)
        pen.polygon([(48,9),(73,29),(52,35),(23,29)],CREAM,keyline=False)
        pen.polygon([(52,35),(73,29),(78,64),(48,88)],(51,123,115,255),keyline=False)
        pen.line([(48,12),(52,35),(48,84)],BRASS,3)
        pen.line([(25,30),(34,62),(48,84)],CREAM,3)
    elif name == 'health':
        pen.polygon([(48,83),(16,53),(12,40),(16,27),(27,19),(40,21),(48,31),
                     (56,21),(69,19),(80,27),(84,40),(80,53)],TEAL)
        pen.line([(23,39),(26,32),(34,31)],CREAM,5)
    elif name == 'mana':
        pen.polygon([(48,10),(66,35),(78,55),(76,70),(63,83),(48,87),
                     (33,83),(20,70),(18,55),(30,35)],TEAL)
        pen.polygon([(48,36),(53,52),(66,58),(53,63),(48,78),(42,63),(29,58),(42,52)],BRASS)
    elif name == 'attack':
        pen.polygon([(48,8),(60,25),(55,59),(41,59),(36,25)],CREAM)
        pen.polygon([(48,12),(60,25),(55,59),(48,59)],SHADE,keyline=False)
        pen.line([(28,61),(68,61)],BRASS,8)
        pen.line([(48,65),(48,80)],TEAL,9)
        pen.circle(48,84,6,BRASS)
    elif name in ('defense','guard'):
        _shield(pen,raised=name == 'guard')
        if name == 'guard':
            pen.line([(21,83),(75,83)],CREAM,7)
    elif name in ('move','travel'):
        _boot(pen,small=name == 'travel')
        if name == 'travel':
            pen.line([(59,27),(83,27)],TEAL,7)
            pen.line([(74,17),(84,27),(74,37)],TEAL,7)
    elif name == 'fly':
        pen.polygon([(14,74),(23,44),(40,26),(82,14),(75,30),(53,43),
                     (77,35),(69,50),(46,58),(68,54),(56,69),(34,72),(23,83)],CREAM)
        pen.line([(23,74),(35,48),(62,28)],BRASS,5)
        pen.line([(34,65),(55,58)],TEAL,4)
    elif name == 'range':
        pen.circle(60,48,26,stroke=BRASS,width=6)
        pen.circle(60,48,12,stroke=TEAL,width=4)
        pen.line([(13,48),(62,48)],CREAM,7)
        pen.line([(48,36),(62,48),(48,60)],CREAM,6)
        pen.line([(13,48),(18,37)],BRASS,5)
        pen.line([(13,48),(18,59)],BRASS,5)
    elif name == 'actions':
        pen.line([(24,14),(72,14)],BRASS,8)
        pen.line([(24,82),(72,82)],BRASS,8)
        pen.line([(29,20),(30,32),(48,48),(66,32),(67,20)],CREAM,6)
        pen.line([(29,76),(30,64),(48,48),(66,64),(67,76)],CREAM,6)
        pen.polygon([(33,29),(63,29),(48,43)],TEAL,keyline=False)
        pen.polygon([(48,57),(63,73),(33,73)],BRASS,keyline=False)
    elif name == 'level':
        pen.line([(21,46),(48,20),(75,46)],BRASS,10)
        pen.line([(21,73),(48,47),(75,73)],TEAL,10)
    elif name == 'xp':
        _star(pen)
        pen.line([(48,30),(48,49),(61,57)],CREAM,4)
    elif name == 'build':
        pen.line([(27,79),(60,38)],SHADE,13)
        pen.line([(25,78),(57,39)],BRASS,6)
        pen.polygon([(29,29),(44,12),(77,40),(62,57)],CREAM)
        pen.polygon([(54,21),(77,40),(62,57),(49,46)],TEAL,keyline=False)
    elif name == 'explore':
        pen.circle(48,48,33)
        pen.polygon([(65,24),(56,56),(31,72),(40,40)],TEAL)
        pen.polygon([(65,24),(48,48),(40,40)],CREAM,keyline=False)
        pen.circle(48,48,5,BRASS)
    elif name == 'end_turn':
        pen.circle(46,43,18,BRASS)
        for angle in (-90,-45,0,45,90,135,180,225):
            radians=math.radians(angle)
            pen.line([(46+math.cos(radians)*25,43+math.sin(radians)*25),
                      (46+math.cos(radians)*31,43+math.sin(radians)*31)],BRASS,5)
        pen.arc(47,44,39,42,145,TEAL,7)
        pen.line([(70,72),(78,67),(79,79)],TEAL,6)
    elif name == 'bolt':
        pen.polygon([(52,9),(23,53),(44,53),(36,87),(77,37),(55,37),(65,9)],BRASS)
        pen.line([(54,17),(35,46),(52,46)],CREAM,4)
    elif name == 'heal':
        pen.polygon([(35,14),(61,14),(61,35),(82,35),(82,61),(61,61),
                     (61,82),(35,82),(35,61),(14,61),(14,35),(35,35)],TEAL)
        pen.line([(43,23),(52,23)],CREAM,4)
    elif name == 'retreat':
        pen.line([(56,17),(79,17),(79,80),(56,80)],BRASS,7)
        pen.line([(65,48),(15,48)],TEAL,9)
        pen.line([(30,32),(14,48),(30,64)],TEAL,9)
    elif name == 'auto_play':
        pen.polygon([(14,23),(45,48),(14,73)],BRASS)
        pen.polygon([(47,23),(80,48),(47,73)],TEAL)
    elif name == 'log':
        pen.polygon([(25,17),(70,17),(77,24),(76,72),(70,81),(26,81),
                     (19,72),(23,64),(25,64)],CREAM)
        pen.line([(27,18),(20,18),(16,25),(16,34),(25,34)],BRASS,7)
        pen.line([(68,79),(60,75),(61,67),(76,67)],BRASS,6)
        for y in (34,47,60):
            pen.line([(36,y),(62,y)],INK,4,keyline=False)
    elif name == 'campaign':
        pen.polygon([(12,25),(36,16),(60,25),(84,16),(84,73),(60,82),(36,73),(12,82)],BRASS)
        pen.polygon([(36,16),(60,25),(60,82),(36,73)],TEAL,keyline=False)
        pen.line([(36,22),(36,67)],INK,4,keyline=False)
        pen.line([(60,30),(60,76)],INK,4,keyline=False)
        pen.line([(24,62),(46,46),(66,54)],CREAM,5)
        pen.circle(68,49,7,RED)
    elif name == 'rival':
        pen.line([(22,13),(22,84)],BRASS,7)
        pen.polygon([(26,19),(80,19),(70,40),(80,63),(26,63)],RED)
        pen.polygon([(48,29),(57,41),(48,53),(39,41)],INK,keyline=False)


def render_icon(name: str) -> Image.Image:
    """Return one deterministic antialiased RGBA icon, with no font or runtime state."""
    if name not in ICONS:
        raise ValueError(f'Unknown Shardbound icon: {name}')
    pen = Pen()
    _draw(name, pen)
    return pen.image.resize((SIZE,SIZE),Image.Resampling.LANCZOS)
