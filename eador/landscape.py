"""Offline, original painted terrain for Shardbound's atlas and battle board.

The game loads the finished PNGs; none of this composition runs during play.
Coordinates describe a pointy hex centered at (160, 160), radius 150, with a
20-pixel earth relief below it. Props stay above the quiet lower label area.
"""
from __future__ import annotations

import hashlib
import math
import random

import numpy as np
from PIL import Image, ImageDraw


GENERATOR_VERSION = 1
TERRAINS = ('plains', 'forest', 'hills', 'marsh', 'water', 'mountains')
MODES = ('province', 'ground')
VARIANTS = (0, 1, 2, 3)
SIZE = (320, 352)
SCALE = 2
HEX = tuple((160 + 150 * math.cos(math.radians(a)),
             160 + 150 * math.sin(math.radians(a)))
            for a in (-90, -30, 30, 90, 150, 210))
PALETTES = {
    'plains': (112, 119, 70), 'forest': (60, 87, 65),
    'hills': (120, 105, 76), 'marsh': (64, 90, 81),
    'water': (47, 78, 96), 'mountains': (101, 111, 111),
}


class Brush:
    """Draw in tile coordinates while keeping small brushwork antialiased."""

    def __init__(self, image):
        self.draw = ImageDraw.Draw(image, 'RGBA')

    def polygon(self, points, color):
        self.draw.polygon([(round(x * SCALE), round(y * SCALE)) for x, y in points], fill=color)

    def ellipse(self, box, color):
        self.draw.ellipse(tuple(round(v * SCALE) for v in box), fill=color)

    def line(self, points, color, width=1):
        self.draw.line([(round(x * SCALE), round(y * SCALE)) for x, y in points],
                       fill=color, width=max(1, round(width * SCALE)), joint='curve')


def _seed(terrain, variant, mode):
    return int.from_bytes(hashlib.sha256(
        f'shardbound-landscape:{GENERATOR_VERSION}:{terrain}:{variant}:{mode}'.encode()
    ).digest()[:8], 'big')


def _material(terrain, seed):
    """Layer broad pigment variation, diagonal brush grain, and fine paper tooth."""
    rng = np.random.default_rng(seed)
    width, height = SIZE[0] * SCALE, SIZE[1] * SCALE
    coarse = Image.fromarray(rng.integers(0, 256, (22, 20), dtype=np.uint8))
    broad = np.asarray(coarse.resize((width, height), Image.Resampling.BICUBIC), dtype=float) - 128
    medium = Image.fromarray(rng.integers(0, 256, (88, 80), dtype=np.uint8))
    grain = np.asarray(medium.resize((width, height), Image.Resampling.BILINEAR), dtype=float) - 128
    yy, xx = np.mgrid[:height, :width]
    illumination = 10 - xx / width * 9 - yy / height * 8
    strokes = np.sin(xx * .20 + yy * .47 + broad * .07) * 1.25
    pigment = broad * .14 + grain * .035 + rng.normal(0, 1.6, (height, width)) + strokes
    pixels = np.empty((height, width, 3), dtype=np.uint8)
    for channel, base in enumerate(PALETTES[terrain]):
        light = illumination * (1.10, 1.0, .68)[channel]
        pixels[:, :, channel] = np.clip(base + pigment + light, 0, 255).astype(np.uint8)
    # RGB drawing blends translucent brush colors into pigment; the hex alpha
    # mask is applied only after all surface illustration is complete.
    return Image.fromarray(pixels)


def _curve(x, y, width, height, phase=0):
    return [(x + t * width, y + math.sin(t * math.pi + phase) * height)
            for t in (i / 24 for i in range(25))]


def _pool(brush, x, y, rx, ry, rng):
    points = [(x + math.cos(a) * rx * rng.uniform(.88, 1.08),
               y + math.sin(a) * ry * rng.uniform(.85, 1.12))
              for a in (i * math.tau / 24 for i in range(24))]
    brush.polygon([(px, py + 3) for px, py in points], (35, 48, 40, 160))
    brush.polygon(points, (87, 107, 79, 160))
    inner = [(x + (px - x) * .90, y + (py - y) * .81) for px, py in points]
    brush.polygon(inner, (43, 71, 74, 235))
    brush.ellipse((x - rx * .55, y - ry * .35, x + rx * .6, y + ry * .34), (64, 93, 88, 85))
    brush.line(_curve(x - rx * .58, y - ry * .36, rx * .98, -ry * .18), (136, 155, 122, 85), 1)
    for _ in range(5):
        px, py = x + rng.uniform(-.55, .55) * rx, y + rng.uniform(-.35, .4) * ry
        brush.line([(px, py), (px + rng.uniform(3, 9), py)], (136, 157, 139, 45), .7)


def _stone(brush, x, y, radius, rng, *, moss=True):
    w, h = radius, radius * rng.uniform(.55, .8)
    brush.ellipse((x - w, y - h * .1, x + w * 1.3, y + h * .7), (22, 36, 36, 65))
    brush.polygon([(x-w, y), (x-w*.45, y-h), (x+w*.55, y-h*.75),
                   (x+w, y+h*.15), (x+w*.2, y+h*.5)], (82, 87, 79, 230))
    brush.polygon([(x-w, y), (x-w*.45, y-h), (x+w*.1, y-h*.4), (x-w*.15, y+h*.2)],
                  (151, 150, 125, 200))
    brush.polygon([(x+w*.1, y-h*.4), (x+w*.55, y-h*.75), (x+w, y+h*.15), (x+w*.2, y+h*.5)],
                  (60, 72, 71, 160))
    brush.line([(x-w*.4, y-h*.78), (x+w*.03, y-h*.43)], (199, 188, 147, 105), .75)
    if moss:
        brush.ellipse((x-w*.6, y-h*.16, x-w*.05, y+h*.16), (102, 123, 65, 120))


def _grass(brush, rng, count, *, reeds=False, limit=274):
    for _ in range(count):
        x, y = rng.uniform(35, 285), rng.uniform(40, limit)
        length = rng.uniform(3, 7) if reeds else rng.uniform(1, 4)
        color = rng.choice(((172, 161, 98, 100), (42, 69, 45, 120),
                            (127, 145, 83, 130), (168, 163, 115, 90)))
        brush.line([(x - 1.5, y), (x - 2.2, y - length), (x, y - length*.3)], color, .65)
        brush.line([(x, y + 1), (x + 1.5, y - length * .8)], color, .65)
        if reeds:
            brush.line([(x + 1.5, y - length * .8), (x + 1.7, y - length - 2)], (93, 78, 47, 150), 1)


def _canopy(brush, x, y, radius, rng):
    """Overlapping, lit leaf masses with a low crown and a planted shadow."""
    brush.ellipse((x-radius*.8+7, y+radius*.22, x+radius*1.35, y+radius*.95), (19, 35, 32, 125))
    brush.line([(x, y+radius*.3), (x+1, y+radius*.9)], (73, 68, 45, 240), 3)
    brush.line([(x-.8, y+radius*.3), (x, y+radius*.83)], (165, 140, 82, 165), 1)
    brush.ellipse((x-radius, y-radius*.6, x+radius, y+radius*.58), (28, 53, 41, 240))
    for i in range(8):
        angle = i * math.tau / 8 + rng.uniform(-.2, .2)
        cx = x + math.cos(angle) * radius * .52
        cy = y + math.sin(angle) * radius * .30
        r = radius * rng.uniform(.35, .50)
        lift = (1 - (math.cos(angle) + math.sin(angle)) * .30)
        color = (int(64*lift), int(92*lift), int(51*lift), 245)
        brush.ellipse((cx-r, cy-r*.72, cx+r, cy+r*.6), color)
    brush.ellipse((x-radius*.49, y-radius*.57, x+radius*.29, y+radius*.08), (94, 120, 62, 235))
    for _ in range(40):
        angle, length = rng.uniform(0, math.tau), math.sqrt(rng.random())
        px, py = x + math.cos(angle)*radius*.86*length, y + math.sin(angle)*radius*.5*length
        lit = px < x + radius*.1 and py < y + radius*.05
        brush.ellipse((px, py, px+rng.uniform(1, 2.5), py+rng.uniform(.6, 1.5)),
                      (151, 158, 80, 95) if lit else (25, 55, 42, 110))


def _hill(brush, x, y, w, h, rng):
    foot = [(x-w, y+4), (x-w*.78, y-h*.2), (x-w*.25, y-h),
            (x+w*.25, y-h*.85), (x+w*.7, y-h*.2), (x+w, y+10), (x, y+h*.27)]
    brush.polygon([(px+5, py+7) for px, py in foot], (51, 56, 44, 80))
    brush.polygon(foot, (112, 104, 65, 230))
    brush.polygon([(x-w, y+4), (x-w*.25, y-h), (x+w*.1, y-h*.7),
                   (x-w*.15, y+4), (x-w*.6, y+9)], (160, 137, 85, 180))
    brush.polygon([(x+w*.1, y-h*.7), (x+w*.25, y-h*.85), (x+w*.7, y-h*.2),
                   (x+w, y+10), (x, y+h*.27), (x-w*.15, y+4)], (83, 85, 67, 170))
    for i in range(4):
        brush.line(_curve(x-w*.66+i*2, y-h*.2+i*6, w*1.4-i*5, -h*(.65-i*.10)),
                   (186, 159, 100, 55), 1.2)
    for _ in range(9):
        px, py = x+rng.uniform(-w*.6, w*.6), y+rng.uniform(-h*.2, 8)
        brush.line([(px, py), (px+rng.uniform(3, 9), py-1)], (155, 147, 92, 90), 1)


def _mountain(brush, x, y, w, h, rng):
    peak = (x - w*.18, y-h)
    left, right = (x-w, y+4), (x+w, y+7)
    ridge = (x+w*.06, y-h*.37)
    brush.polygon([(left[0]+8, left[1]+5), (peak[0]+13, peak[1]+15),
                   (right[0]+12, right[1]+7), (x+8, y+19)], (28, 45, 49, 100))
    brush.polygon([left, peak, ridge, (x-w*.15, y+10)], (144, 145, 130, 255))
    brush.polygon([peak, right, (x+w*.2, y+15), ridge], (69, 88, 94, 255))
    brush.polygon([peak, (x-w*.58, y-h*.36), (x-w*.37, y-h*.17), ridge], (188, 181, 149, 175))
    brush.polygon([(x-w*.58, y-h*.36), left, (x-w*.4, y+9), (x-w*.37, y-h*.17)], (107, 115, 108, 235))
    brush.polygon([peak, (x-w*.41, y-h*.67), (x-w*.2, y-h*.74),
                   (x-w*.09, y-h*.57), (x+w*.02, y-h*.65), (x+w*.18, y-h*.49)],
                  (222, 219, 186, 240))
    brush.line([peak, ridge, (x+w*.23, y+7)], (204, 196, 161, 135), 1)
    for _ in range(11):
        t = rng.uniform(.22, .85)
        px, py = x-w*.18 + w*t*rng.uniform(-.7, .85), y-h+h*t
        brush.line([(px, py), (px+rng.uniform(-6, 7), py+rng.uniform(5, 13))], (41, 65, 73, 75), .8)


def _paint_ground(brush, terrain, rng):
    """Broad terrain identity, with no tall silhouette or occupied-looking token."""
    if terrain in ('plains', 'forest', 'hills'):
        _grass(brush, rng, 200 if terrain == 'plains' else 115)
    if terrain == 'forest':
        for _ in range(65):
            x, y = rng.uniform(25, 295), rng.uniform(40, 278)
            brush.ellipse((x, y, x+rng.uniform(1, 4), y+1.4), rng.choice(
                ((110, 122, 64, 95), (135, 114, 64, 85), (30, 57, 44, 90))))
        for x, y in ((72, 99), (233, 188), (106, 217)):
            brush.line([(x-14,y+7), (x-4,y), (x+11,y-3), (x+19,y-12)], (139, 128, 89, 65), 1.3)
        for x,y,r in ((97,78,18),(125,85,16),(232,108,18)):
            _canopy(brush,x+rng.uniform(-5,5),y,r,rng)
    elif terrain == 'hills':
        for i in range(9):
            x, y = rng.uniform(30, 170), rng.uniform(55, 250)
            brush.line(_curve(x, y, rng.uniform(50, 105), -rng.uniform(5, 16)), (199, 173, 114, 45), 2)
            brush.line(_curve(x+2, y+3, rng.uniform(50, 100), -9), (58, 66, 56, 40), 1)
        _hill(brush,112,87,39,15,rng)
        _hill(brush,235,134,32,13,rng)
        _stone(brush,226,137,6,rng)
    elif terrain == 'marsh':
        for x, y, rx, ry in ((91, 97, 39, 13), (221, 176, 39, 15), (108, 221, 24, 8)):
            _pool(brush, x+rng.uniform(-12,12), y+rng.uniform(-8,8), rx, ry, rng)
        _grass(brush, rng, 95, reeds=True)
    elif terrain == 'water':
        for i in range(34):
            x, y = rng.uniform(15, 260), rng.uniform(25, 305)
            brush.line(_curve(x,y,rng.uniform(18,65),rng.uniform(1,3),rng.random()),
                       (142, 171, 161, rng.randint(28, 65)), rng.uniform(.5,1.5))
    elif terrain == 'mountains':
        for _ in range(46):
            x, y, w = rng.uniform(25,290), rng.uniform(28,276), rng.uniform(5,16)
            brush.polygon([(x-w,y+2),(x,y-4),(x+w,y),(x+w*.2,y+5)],
                          rng.choice(((166,166,142,75),(46,69,75,65),(129,141,131,65))))
            brush.line([(x-w,y+2),(x,y-4),(x+w,y)], (199,191,154,70), .8)
    if terrain not in ('water', 'marsh'):
        for _ in range(14):
            _stone(brush,rng.uniform(42,277),rng.uniform(45,265),rng.uniform(1.3,3),rng,
                   moss=terrain != 'mountains')


def _paint_province(brush, terrain, variant, rng):
    shift = (-8, 7, -3, 10)[variant]
    if terrain == 'plains':
        path = [(91+shift+math.sin(i*.19)*16, 62+i*3.6) for i in range(44)]
        brush.line([(x+2,y+2) for x,y in path], (56, 69, 46, 80), 9)
        brush.line(path, (182, 159, 99, 165), 6)
        brush.line([(x-1,y) for x,y in path], (208, 182, 115, 95), 1.1)
        for x,y,w,h in ((151,83,60,31),(192,151,57,34),(60,165,51,27)):
            x += shift
            brush.polygon([(x,y),(x+w,y+9),(x+w-9,y+h),(x-8,y+h-9)], (80,83,49,145))
            for row in range(7):
                t = (row+.5)/7
                brush.line([(x-8*t,y+(h-9)*t),(x+w-9*t,y+9+(h-9)*t)],
                           (187,163,86,185) if row%2 else (141,142,66,185), 2)
                brush.line([(x-8*t,y+(h-9)*t+1.8),(x+w-9*t,y+9+(h-9)*t+1.8)],
                           (55,72,46,85), .8)
        _grass(brush,rng,100,limit=230)
        _canopy(brush,238+shift,98,14,rng)
        _canopy(brush,132+shift,205,10,rng)
    elif terrain == 'forest':
        trees = [(125,76,27),(171,84,28),(214,104,27),(85,115,26),
                 (137,127,31),(182,140,32),(229,151,25),(71,164,22),
                 (112,178,29),(155,192,27),(203,201,24)]
        for x,y,r in trees:
            _canopy(brush,x+shift+rng.uniform(-5,5),y+rng.uniform(-5,5),r*rng.uniform(.87,1.07),rng)
    elif terrain == 'hills':
        for x,y,w,h in ((173,109,56,40),(94,143,48,35),(214,185,57,47),(128,211,57,36)):
            _hill(brush,x+shift,y,w,h,rng)
        for x,y,r in ((111,139,10),(195,154,8),(218,193,13),(94,209,8),(153,214,5)):
            _stone(brush,x+shift,y,r,rng)
    elif terrain == 'marsh':
        for x,y,rx,ry in ((116,114,58,25),(208,175,49,26),(105,213,42,15)):
            _pool(brush,x+shift,y,rx,ry,rng)
        for x,y in ((73,97),(165,121),(226,150),(182,207),(70,204),(128,225)):
            for _ in range(11):
                px,py=x+rng.uniform(-10,10),y+rng.uniform(-4,4)
                height=rng.uniform(6,13)
                brush.line([(px,py),(px-2,py-height)],(164,150,85,170),.8)
                brush.line([(px-2,py-height),(px-2.5,py-height-3)],(77,70,43,200),1.3)
        brush.line([(231,91),(233,123),(244,131)],(69,72,55,220),3)
        brush.line([(233,110),(221,99),(215,99)],(138,125,84,170),1.5)
    elif terrain == 'water':
        for x,y,r in ((85,141,14),(223,100,18),(233,202,10)):
            _pool(brush,x+shift,y,r*2,r*.8,rng)
            _stone(brush,x+shift,y,r,rng)
        for i in range(9):
            brush.line(_curve(107+shift,80+i*16,110,5,i*.3),(174,190,167,45),1.2)
    elif terrain == 'mountains':
        for x,y,w,h in ((157,139,61,91),(211,192,60,92),(105,211,65,102)):
            _mountain(brush,x+shift,y,w,h,rng)
        for x,y,r in ((166,218,13),(201,221,8),(80,227,10)):
            _stone(brush,x+shift,y,r,rng,moss=False)


def render_tile(terrain: str, variant: int, *, mode: str = 'province') -> Image.Image:
    """Compose one deterministic RGBA tile, ready for the runtime image cache."""
    if terrain not in TERRAINS or variant not in VARIANTS or mode not in MODES:
        raise ValueError(f'Unknown terrain tile: {mode}/{terrain}/{variant}')
    seed = _seed(terrain, variant, mode)
    rng = random.Random(seed)
    size = (SIZE[0]*SCALE, SIZE[1]*SCALE)
    result = Image.new('RGBA',size)
    relief = Brush(result)
    relief.polygon([(x,y+20) for x,y in HEX], (42,49,42,255))
    relief.polygon([HEX[2],HEX[3],(HEX[3][0],HEX[3][1]+20),(HEX[2][0],HEX[2][1]+20)],
                   (35,48,46,255))
    relief.polygon([HEX[3],HEX[4],(HEX[4][0],HEX[4][1]+20),(HEX[3][0],HEX[3][1]+20)],
                   (69,69,49,255))
    for i in range(3):
        relief.line([(HEX[4][0]+3,HEX[4][1]+5+i*4),(160,315+i*4),
                     (HEX[2][0]-2,HEX[2][1]+5+i*4)], (80,80,58,255),.8)
    surface = _material(terrain,seed)
    brush = Brush(surface)
    _paint_ground(brush,terrain,rng)
    if mode == 'province':
        _paint_province(brush,terrain,variant,rng)
    # An inset painterly rim defines geometry without competing with game cues.
    brush.line([HEX[4],HEX[5],HEX[0],HEX[1]],(220,197,138,75),1.2)
    brush.line([HEX[1],HEX[2],HEX[3],HEX[4]],(19,43,41,90),1.1)
    mask = Image.new('L',size)
    ImageDraw.Draw(mask).polygon([(round(x*SCALE),round(y*SCALE)) for x,y in HEX],fill=255)
    surface.putalpha(mask)
    result.alpha_composite(surface)
    return result.resize(SIZE,Image.Resampling.LANCZOS)
