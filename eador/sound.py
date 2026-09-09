"""Original Shardbound compositions; generation is an explicit build step.

The game owns instruments, the E-minor motif, voicings, rhythms and cue meanings.
Saga2D supplies sample primitives. Runtime uses ordinary WAV assets through
Game.audio; importing this module generates nothing and opens no files.
"""

import numpy as np

from sagaforge.synth import SAMPLE_RATE, envelope, hz, level, mix, noise, pan, seconds, thump, tone

GENERATOR_VERSION = '3'


def _plucked(note, length, *, seed=0):
    """Damped lute strings, a wooden body and a brief pick scrape."""
    string = tone(note, length, attack=.004, tau=length * .27,
                  partials=((1, 1), (2.002, .64), (3.008, .38), (4.016, .22), (5.025, .1), (6.036, .05)))
    return mix(string, noise(.035, 1500, 6500, attack=.003, tau=.008, seed=seed) * .11,
               tone(285, min(length, .15), attack=.005, tau=.035, partials=((1, .6), (1.71, .25), (2.32, .15))) * .12)


def _bowed(note, length, *, attack=.7, seed=0):
    """Two gently detuned bowed voices, slow vibrato and restrained bow friction."""
    t, freq = seconds(length), hz(note)
    out = np.zeros_like(t)
    for detune, phase in ((.9991, .2), (1.0009, 1.4)):
        vibrato = freq * .0016 / 4.7 * np.sin(2 * np.pi * 4.7 * t + phase)
        for harmonic, weight in ((1, 1), (2, .48), (3, .24), (4, .13), (5, .065), (6, .025)):
            out += weight * np.sin(2 * np.pi * freq * detune * harmonic * t + harmonic * vibrato)
    out *= envelope(length, attack, length * .43) / 3.88
    return out + noise(length, 900, 3800, attack=attack, tau=length * .3, seed=seed) * .025


def _flute(note, length, *, seed=0):
    """A breathed wooden flute with a soft attack and moving upper harmonics."""
    t, freq = seconds(length), hz(note)
    phase = 2 * np.pi * freq * t + freq * .0018 / 5.1 * np.sin(2 * np.pi * 5.1 * t)
    voice = np.sin(phase) + .22 * np.sin(2 * phase) + .09 * np.sin(3 * phase)
    return voice * envelope(length, .055, length * .4) / 1.31 + noise(
        length, 1400, 4800, attack=.07, tau=length * .25, seed=seed) * .045


def _skin(length=.48, *, seed=0):
    """Low skin drum: falling pitch, inharmonic membrane modes and a fingertip."""
    return mix(thump(118, 48, length, attack=.005, tau=.11),
               tone(143, length, attack=.006, tau=.065, partials=((1, .5), (1.59, .3), (2.14, .2))) * .4,
               noise(.075, 250, 2800, attack=.004, tau=.016, seed=seed) * .32)


def _metal(freq, length):
    return tone(freq, length, attack=.005, tau=length * .24,
                partials=((1, 1), (2.756, .53), (5.404, .3), (8.933, .12)))


def _room(clip, position):
    """Three quiet stereo reflections give the chamber depth, without a dry echo."""
    return mix(pan(clip, position), (.071, pan(clip * .16, -position)),
               (.137, pan(clip * .09, position * .35)), (.223, pan(clip * .045, -position * .6)))


def confirm():
    """Two small wooden E–B plucks, with a delicate metallic overtone."""
    return level(mix(_plucked('E5', .17, seed=500),
                     (.075, _plucked('B5', .22, seed=501) * .7),
                     _metal(1318, .20) * .09), .42)


def refuse():
    """Two muted descending wood knocks; dry and distinct from a reward."""
    return level(mix(_plucked('G3', .14, seed=502),
                     (.105, _plucked('F#3', .20, seed=503) * .85)), .38)


def move():
    """Two weighted bootfalls with leather creak and distinct gravel grains."""
    return level(mix(noise(.13, 160, 2300, attack=.007, tau=.033, seed=510),
                     _skin(.16, seed=512) * .4,
                     (.18, noise(.14, 220, 2600, attack=.009, tau=.035, seed=511) * .8),
                     (.18, _skin(.17, seed=513) * .32)), .43)


def attack_hit():
    """An edged strike: short metal scrape, a wooden crack and low contact."""
    return level(mix(thump(220, 58, .27, attack=.004, tau=.065),
                     noise(.12, 1600, 7500, attack=.004, tau=.023, seed=520) * .85,
                     _metal(710, .31) * .32,
                     (.012, tone(310, .19, attack=.004, tau=.055,
                                 partials=((1, .6), (1.73, .25), (2.41, .15))) * .5)), .62)


def attack_arrow():
    """Bowstring snap and feathered flight; contact has its own timed impact cue."""
    return level(mix(tone(172, .22, attack=.004, tau=.035,
                           partials=((1, 1), (2.01, .65), (3.03, .4), (4.06, .2))),
                     noise(.055, 1800, 7400, attack=.004, tau=.01, seed=521) * .45,
                     (.025, noise(.28, 1300, 4600, attack=.045, tau=.055, seed=522) * .5)), .48)


def attack_heavy():
    """A weighty shield or polearm impact with a deep body and loose armour rattle."""
    return level(mix(_skin(.44, seed=523),
                     thump(76, 31, .47, attack=.006, tau=.13) * .65,
                     noise(.17, 350, 4700, attack=.005, tau=.04, seed=524) * .65,
                     (.022, _metal(386, .48) * .4),
                     (.067, noise(.16, 2000, 6500, attack=.009, tau=.045, seed=525) * .22)), .64)


def guard():
    """A hollow shield knock followed by damped, inharmonic iron resonance."""
    return level(mix(_skin(.22, seed=530), _metal(438, .47) * .55,
                     noise(.11, 420, 2400, attack=.006, tau=.025, seed=531) * .3), .5)


def bolt():
    """A tearing air streak releases into branching sparks and a resonant crack."""
    return level(mix(noise(.32, 600, 7000, attack=.022, tau=.09, seed=540),
                     thump(280, 1500, .23, attack=.02, tau=.09) * .3,
                     (.16, noise(.17, 2400, 9000, attack=.004, tau=.023, seed=541) * .85),
                     (.18, _metal(1480, .31) * .23),
                     (.2, thump(170, 53, .23, attack=.004, tau=.055) * .6)), .58)


def heal():
    """A breathed opening minor triad over gently resonating strings."""
    return level(mix(_flute('E4', .72, seed=550),
                     (.085, _flute('G4', .69, seed=551) * .7),
                     (.19, _plucked('B4', .66, seed=552) * .65),
                     (.23, _metal(988, .49) * .1)), .47)


def reward():
    """Three bright hammered strings, with a small coin-like shimmer."""
    return level(mix(_plucked('E5', .38, seed=553),
                     (.105, _plucked('G5', .40, seed=554) * .85),
                     (.24, _plucked('B5', .45, seed=555) * .7),
                     (.25, _metal(1520, .34) * .15)), .49)


def level_up():
    """A rising lute figure opens into a short breathed high tonic."""
    phrases = [('E4', 0), ('B4', .12), ('F#5', .28), ('G5', .43), ('E6', .66)]
    return level(mix(*[(at, _plucked(note, .60, seed=560 + i) * (.95 - i * .08))
                       for i, (note, at) in enumerate(phrases)],
                     (.65, _flute('E5', .63, seed=565) * .55)), .56)


def victory():
    """The shard motif resolves into an open minor-add-nine bowed chord and low drum."""
    layers = [(at, _plucked(note, .5, seed=570 + i))
              for i, (note, at) in enumerate([('E4', 0), ('F#4', .18), ('B4', .38), ('G4', .58)])]
    layers += [(.82, _bowed(note, 1.45, attack=.09, seed=580 + i) * gain)
               for i, (note, gain) in enumerate([('E3', .6), ('B3', .6), ('E4', .7), ('G4', .55), ('F#5', .25)])]
    return level(mix(*layers, (.81, _skin(seed=585) * .35)), .6)


def defeat():
    """A bowed descent to unresolved B, with a low wind tail."""
    return level(mix(*[(at, _bowed(note, .95, attack=.065, seed=590 + i) * gain)
                       for i, (note, at, gain) in enumerate([('E3', 0, 1), ('D3', .25, .9), ('C3', .54, .85), ('B2', .87, .8)])],
                     noise(1.8, 80, 650, attack=.25, tau=.55, seed=595) * .16), .46)


def end_turn():
    """A woodblock tick and two muted lute notes close the command phase."""
    return level(mix(noise(.065, 750, 3000, attack=.004, tau=.015, seed=600) * .35,
                     _plucked('B4', .28, seed=601),
                     (.23, _plucked('E4', .39, seed=602) * .8)), .4)


def seal_gain():
    """Two rising ritual-bell strikes and a soft breath mark one secured holding turn."""
    return level(mix(_metal(hz('E5'), .48) * .62,
                     (.13, _metal(hz('B5'), .58) * .5),
                     _flute('E4', .5, seed=610) * .17), .46)


def seal_loss():
    """A short falling pair of damped bells and escaping air mark broken seal progress."""
    return level(mix(_metal(hz('B4'), .38) * .55,
                     (.12, _metal(hz('F#4'), .46) * .6),
                     noise(.4, 180, 1300, attack=.04, tau=.1, seed=611) * .18), .44)


CUES = {'confirm': confirm, 'refuse': refuse, 'move': move, 'attack_hit': attack_hit,
        'attack_arrow': attack_arrow, 'attack_heavy': attack_heavy,
        'guard': guard, 'bolt': bolt, 'heal': heal, 'reward': reward, 'level_up': level_up,
        'victory': victory, 'defeat': defeat, 'end_turn': end_turn,
        'seal_gain': seal_gain, 'seal_loss': seal_loss}


# E–F#–B–G is the shared shard motif. Timings and instrument choices belong here,
# not in the framework. Six fields give the campaign a complete 48-second form.
_CAMPAIGN_VOICINGS = (
    ('E2', 'B2', 'E3', 'G3', 'F#4'), ('C3', 'G3', 'B3', 'E4'),
    ('G2', 'D3', 'A3', 'B3'), ('D3', 'A3', 'E4', 'F#4'),
    ('A2', 'E3', 'G3', 'B3'), ('B2', 'F#3', 'A3', 'E4'),
)
_CAMPAIGN_ANSWERS = (
    ('E4', 'F#4', 'B3', 'G3'), ('E4', 'D4', 'G4', None),
    ('B3', None, 'A4', 'G4'), ('F#4', 'E4', 'A3', None),
    ('B3', 'C4', 'E4', 'G4'), ('F#4', None, 'E4', 'B3'),
)


def _wrap(out, clip, start):
    """Place a stereo phrase on the loop, preserving tails across its seam."""
    at = round(start * SAMPLE_RATE) % len(out)
    first = min(len(clip), len(out) - at)
    out[at:at + first] += clip[:first]
    out[:len(clip) - first] += clip[first:]


def campaign(*, budget=None):
    """48 seconds: bowed harmonic fields, wooden lute figures, flute answers and a soft hand drum."""
    out = np.zeros((48 * SAMPLE_RATE, 2))
    for phrase, (chord, answer) in enumerate(zip(_CAMPAIGN_VOICINGS, _CAMPAIGN_ANSWERS)):
        start = phrase * 8
        for voice, note in enumerate(chord):
            pad = _bowed(note, 10.8, attack=1.25, seed=700 + phrase * 10 + voice)
            _wrap(out, _room(pad * (.29 if voice == 0 else .17), -.65 + voice * .29), start - .9)
            if budget:
                budget.checkpoint()
        for index, (note, offset) in enumerate(zip(answer, (1.0, 2.5, 4.25, 6.25))):
            if note is not None:
                _wrap(out, _room(_flute(note, 1.9, seed=770 + phrase * 4 + index) * .16,
                                 -.25 if phrase % 2 else .3), start + offset)
        # Lute arpeggios change register and spacing, leaving the flute room to breathe.
        for step, offset in enumerate((.25, 1.75, 3.0, 4.75, 5.5, 7.25)):
            note = chord[1 + (step + phrase) % (len(chord) - 1)]
            _wrap(out, _room(_plucked(note, 1.5, seed=810 + phrase * 6 + step) * (.16 if step % 3 else .21),
                             -.45 if step % 2 else .45), start + offset)
        for beat in (0, 4):
            _wrap(out, _room(_skin(seed=860 + phrase + beat) * (.12 if beat else .17), -.08), start + beat)
        wash = noise(9.5, 180, 1600, attack=1.8, tau=2.6, seed=900 + phrase)
        _wrap(out, pan(wash * .045, .45 if phrase % 2 else -.45), start - .6)
        if budget:
            budget.checkpoint()
    return level(out, .16)


def battle(*, budget=None):
    """32 seconds: bowed low ostinato, skin drums, dry rattles and alternating flute/lute answers."""
    out = np.zeros((32 * SAMPLE_RATE, 2))
    fields = (('E2', 'B2', 'G3'), ('A2', 'E3', 'C4'),
              ('C3', 'G3', 'E4'), ('B2', 'F#3', 'E4'))
    answers = (('E3', 'B3', 'E4', 'D4'), ('A3', 'E4', 'C4', 'B3'),
               ('G3', 'E4', 'D4', 'B3'), ('F#3', 'B3', 'E4', 'F#4'))
    for section, (chord, answer) in enumerate(zip(fields, answers)):
        start = section * 8
        for voice, note in enumerate(chord):
            bed = _bowed(note, 10, attack=.8, seed=1000 + section * 3 + voice)
            _wrap(out, _room(bed * (.23 if voice == 0 else .14), (voice - 1) * .5), start - .5)
            if budget:
                budget.checkpoint()
        for cell in range(2):
            at = start + cell * 4
            for index, (offset, weight) in enumerate(((0, .45), (1.5, .23), (2, .36), (3.25, .19))):
                _wrap(out, _room(_skin(seed=1100 + section * 20 + cell * 4 + index) * weight,
                                 -.18 if index % 2 else .12), at + offset)
            for beat in range(8):
                # Repeated lower strings carry urgency without turning the melody into an alarm.
                note = chord[beat % 2]
                bow = _bowed(note, .43, attack=.025, seed=1200 + section * 16 + cell * 8 + beat)
                _wrap(out, _room(bow * (.16 if beat % 3 else .22), -.3), at + beat * .5 + .015)
                rattle = noise(.10, 2800, 7600, attack=.006, tau=.022, seed=1300 + section * 16 + cell * 8 + beat)
                _wrap(out, pan(rattle * (.065 if beat % 2 else .04), .45), at + beat * .5 + .25)
            for index, note in enumerate(answer):
                offset = (.5, 1.25, 2.75, 3.5)[index]
                line = (_flute(note, .88, seed=1400 + index) if cell and section % 2
                        else _plucked(note, .85, seed=1410 + index))
                _wrap(out, _room(line * (.18 if cell else .13), .35), at + offset)
            if cell:
                _wrap(out, _room(_metal(530, 1.4) * .035, -.35), at + 3.5)
            if budget:
                budget.checkpoint()
    return level(out, .18)


TRACKS = {'campaign': campaign, 'battle': battle}


def set_music(game, name):
    """Select a shipped track without restarting an unchanged selection; None stops."""
    if name is None:
        game.audio.stop_music()
    elif name not in TRACKS:
        raise KeyError(f'Unknown Shardbound track: {name!r}')
    elif game.audio.music_name != name:
        game.audio.play_music(name, loop=True)
