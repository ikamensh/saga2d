"""Player-facing build facts; packaging supplies the identity of a frozen app."""

from saga2d.release import build_info


VERSION = '0.1.0-development'


def build_label():
    """Source launches say so; installed apps identify their recorded source."""
    info = build_info()
    if info is None:
        return f'{VERSION} · source checkout'
    modified = ' · modified source' if info['working_tree_dirty'] else ''
    return f"{info['version']} · {info['source_commit'][:12]}{modified}"


def about_text(game):
    return f'''Development build · {build_label()}

THE CURRENT GAME
Lead one hero and a persistent army through three linked shards, or play a standalone shard. Four heroes, three world themes and three difficulties offer different starts. Develop your realm, counter the rival's finite expedition and command hex battles. Twelve authored encounter patterns include rout, hold and extraction objectives. Manual orders and optional automatic rounds share the same rules.

WHAT IS STILL UNFINISHED
This is a development checkpoint, not an Early Access release. Strategic balance, onboarding and presentation are still being evaluated. Audio listening and human playtests remain outstanding. Windows and clean-account installations have not been verified. The app uses a development icon and system fonts. Two-player shared-realm co-op is available online through room codes, with LAN/private VPN as an optional mode. Competitive multiplayer, diplomacy and an astral metacampaign are not implemented.

CONTROLS AND ACCESSIBILITY
The Field Guide (F1 during play) explains your first turns. The Codex (C during play) contains rules, troops, skills and adventures. Every visible keycap names a keyboard control. Settings offer sound, display, reduced motion and larger reading text. Space finishes battle playback. F6 opens saves; F5/F9 save/load Manual 1.

CREDITS
Game and Saga2D framework: Ilya Kamenshchikov and contributors, under the MIT license. Original terrain, icons, miniatures, music and sound cues use the project's drawing and synthesis code. The environment painting and four hero portraits were generated with Codex image generation from original text prompts; their provenance ships with the assets. Eador inspired the gameplay research; Shardbound is an independent game. CPython, pyglet, Pillow, NumPy and websockets power the application. Packaged builds include their license texts and the PyInstaller bootloader license under release/licenses.

FEEDBACK DURING LOCAL TESTING
Send the project maintainer the build identity above, your operating system, hero, seed, difficulty, what you expected, and the steps that caused the problem. Include a screenshot or save file when useful. Packaged builds include a build manifest for the full source identity. No public support address or automatic report upload is configured.

Your saves and settings are in:
{game.data_dir}

F6 offers three manual slots, rolling autosaves and explicit previous-file recovery. Copy a save before experimenting with it. A separate test profile can be launched with --data-dir PATH; it keeps its own saves and settings.'''
