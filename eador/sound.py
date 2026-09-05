"""Original Shardbound compositions; generation is an explicit build step.

The game owns the E-minor motif, voicings, rhythms and cue meanings. Saga2D
supplies tone/noise/envelope/sample helpers. Runtime uses ordinary WAV assets
through game.audio; importing this module generates nothing and opens no files.
"""

import numpy as np

from saga2d.synth import BELL, DARK, GLASS, SOFT, SAMPLE_RATE, level, mix, noise, pan, thump, tone

GENERATOR_VERSION = '1'


def confirm():
    """A small E–B answering chime: clear, brief and affirmative."""
    return level(mix(tone('E5', .14, attack=.006, tau=.055, partials=GLASS),
                     (.075, tone('B5', .19, attack=.006, tau=.07, partials=GLASS) * .7)), .42)


def refuse():
    """A dry descending semitone, without an alarming buzzer."""
    return level(mix(tone('G3', .13, attack=.012, tau=.055, partials=DARK),
                     (.105, tone('F#3', .19, attack=.012, tau=.08, partials=DARK))), .38)


def move():
    """Two weighted bootfalls with distinct gravel grains."""
    return level(mix(noise(.11, 160, 1700, attack=.008, tau=.026, seed=510),
                     thump(105, 54, .13, attack=.008, tau=.035) * .45,
                     (.18, noise(.12, 220, 2000, attack=.009, tau=.03, seed=511) * .8),
                     (.18, thump(95, 49, .14, attack=.008, tau=.038) * .35)), .43)


def attack_hit():
    """A quick edged impact above a short low body, not a musical reward."""
    return level(mix(thump(240, 58, .25, attack=.004, tau=.07),
                     noise(.085, 1800, 5500, attack=.004, tau=.017, seed=520) * .7,
                     (.014, tone('E3', .15, attack=.004, tau=.045, partials=DARK) * .4)), .62)


def guard():
    """A hollow shield knock followed by a muted metallic ring."""
    return level(mix(thump(115, 76, .17, attack=.006, tau=.05),
                     noise(.09, 350, 1800, attack=.006, tau=.025, seed=530) * .35,
                     (.014, tone('B3', .46, attack=.006, tau=.14, partials=BELL) * .55)), .5)


def bolt():
    """A rising electric streak releases into a high, short spark."""
    return level(mix(thump(380, 1100, .26, attack=.018, tau=.11) * .7,
                     noise(.30, 1200, 6200, attack=.025, tau=.075, seed=540) * .6,
                     (.19, tone('B6', .22, attack=.004, tau=.055, partials=BELL) * .4)), .58)


def heal():
    """A soft opening minor triad, with a quiet breath rather than an impact."""
    return level(mix(tone('E4', .68, attack=.045, tau=.27, partials=SOFT),
                     (.08, tone('G4', .65, attack=.045, tau=.26, partials=SOFT) * .75),
                     (.19, tone('B4', .61, attack=.045, tau=.25, partials=SOFT) * .55),
                     noise(.76, 2200, 5200, attack=.12, tau=.19, seed=550) * .09), .47)


def reward():
    """Three lightly struck upper notes: a small material reward."""
    return level(mix(tone('E5', .36, attack=.005, tau=.12, partials=GLASS),
                     (.105, tone('G5', .38, attack=.005, tau=.13, partials=GLASS) * .85),
                     (.24, tone('B5', .43, attack=.005, tau=.15, partials=GLASS) * .7)), .49)


def level_up():
    """A wider, longer ascent than reward, resolving a second into the high tonic."""
    phrases = [('E4', 0), ('B4', .12), ('F#5', .28), ('G5', .43), ('E6', .66)]
    return level(mix(*[(at, tone(note, .55, attack=.009, tau=.21, partials=BELL) * (.95 - i * .08))
                       for i, (note, at) in enumerate(phrases)]), .56)


def victory():
    """The E–F#–B–G shard motif settles into an open minor-add-nine chord."""
    layers = [(at, tone(note, .45, attack=.012, tau=.19, partials=GLASS))
              for note, at in [('E4', 0), ('F#4', .18), ('B4', .38), ('G4', .58)]]
    layers += [(.82, tone(note, 1.35, attack=.025, tau=.47, partials=SOFT) * gain)
               for note, gain in [('E3', .6), ('B3', .6), ('E4', .7), ('G4', .55), ('F#5', .25)]]
    return level(mix(*layers), .6)


def defeat():
    """An unhurried descent to B, leaving the tonic unresolved."""
    return level(mix(*[(at, tone(note, .85, attack=.025, tau=.31, partials=DARK) * gain)
                       for note, at, gain in [('E3', 0, 1), ('D3', .25, .9), ('C3', .54, .85), ('B2', .87, .8)]],
                     noise(1.6, 80, 360, attack=.25, tau=.45, seed=560) * .1), .46)


def end_turn():
    """A wooden tick and an answering downward fifth close the command phase."""
    return level(mix(noise(.055, 750, 2500, attack=.004, tau=.014, seed=570) * .35,
                     tone('B4', .25, attack=.012, tau=.11, partials=DARK),
                     (.23, tone('E4', .37, attack=.017, tau=.15, partials=DARK))), .4)


CUES = {'confirm': confirm, 'refuse': refuse, 'move': move, 'attack_hit': attack_hit,
        'guard': guard, 'bolt': bolt, 'heal': heal, 'reward': reward, 'level_up': level_up,
        'victory': victory, 'defeat': defeat, 'end_turn': end_turn}


# E–F#–B–G is the shared shard motif. Sparse answers vary across six eight-second
# harmonic fields; these voicings/timings are game compositions, not synth API.
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


def campaign():
    """48 seconds: twelve slow 4/4 bars, overlapping low reeds and sparse glass answers."""
    out = np.zeros((48 * SAMPLE_RATE, 2))
    for phrase, (chord, answer) in enumerate(zip(_CAMPAIGN_VOICINGS, _CAMPAIGN_ANSWERS)):
        start = phrase * 8
        for voice, note in enumerate(chord):
            weight = .55 if voice == 0 else .35
            pad = tone(note, 10.8, attack=1.3, tau=3.6, partials=DARK if voice < 2 else SOFT)
            _wrap(out, pan(pad * weight, -.55 + voice * .24), start - .9)
        for note, offset, position in zip(answer, (1.15, 2.55, 4.4, 6.25), (-.4, .2, .45, -.15)):
            if note is not None:
                _wrap(out, pan(tone(note, 2.1, attack=.012, tau=.65, partials=GLASS) * .105,
                               position), start + offset)
        # A very quiet, seeded air wash is a texture within each phrase.
        wash = noise(9.5, 180, 1200, attack=1.8, tau=2.6, seed=700 + phrase)
        _wrap(out, pan(wash * .035, .35 if phrase % 2 else -.35), start - .6)
    return level(out, .16)


def battle():
    """32 seconds: sixteen 4/4 bars at 120 BPM, felt in half-time with sparse toms."""
    out = np.zeros((32 * SAMPLE_RATE, 2))
    fields = (('E2', 'B2', 'G3'), ('A2', 'E3', 'C4'),
              ('C3', 'G3', 'E4'), ('B2', 'F#3', 'E4'))
    answers = (('E3', 'B3', 'E4', 'D4'), ('A3', 'E4', 'C4', 'B3'),
               ('G3', 'E4', 'D4', 'B3'), ('F#3', 'B3', 'E4', 'F#4'))
    for section, (chord, answer) in enumerate(zip(fields, answers)):
        start = section * 8
        for voice, note in enumerate(chord):
            bed = tone(note, 10, attack=.8, tau=3.2, partials=DARK)
            _wrap(out, pan(bed * (.5 if voice == 0 else .27), (voice - 1) * .4), start - .5)
        for cell in range(2):
            at = start + cell * 4
            for index, (offset, weight) in enumerate(((0, .5), (1.5, .32), (2, .42), (3.25, .24))):
                drum = mix(thump(92, 43, .29, attack=.008, tau=.075),
                           noise(.11, 130, 920, attack=.006, tau=.027, seed=800 + section * 20 + cell * 4 + index) * .23)
                _wrap(out, pan(drum * weight, -.12 if index % 2 else .12), at + offset)
            for index, note in enumerate(answer):
                # Half the statements answer low rather than doubling a lead melody.
                offset = (.5, 1.25, 2.75, 3.5)[index]
                phrase = tone(note, .8, attack=.018, tau=.24, partials=GLASS)
                _wrap(out, pan(phrase * (.12 if cell else .09), (-.35, .2, .35, -.1)[index]), at + offset)
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
