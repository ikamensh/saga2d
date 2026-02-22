"""
Audio: background music with crossfade, sound effects with channels, sound pools.
This is what you write TODAY with pygame.
"""
import pygame
import random

pygame.init()
pygame.mixer.init()
screen = pygame.display.set_mode((1024, 768))
clock = pygame.time.Clock()

# === Music — pygame.mixer.music is global, one track at a time ===

pygame.mixer.music.load("assets/music/exploration.ogg")
pygame.mixer.music.set_volume(0.5)
pygame.mixer.music.play(-1)


# Crossfade: pygame has fadeout() built in, and a MUSIC_END event for chaining.
# But there's no fade-IN — the new track starts at full volume.
# For true crossfade you need non-blocking state tracking in your update loop.

MUSIC_END = pygame.USEREVENT + 1
pygame.mixer.music.set_endevent(MUSIC_END)


class MusicManager:
    """Non-blocking crossfade. You build this yourself."""
    def __init__(self):
        self.pending_track = None
        self.target_volume = 0.5
        self.fading_in = False
        self.fade_speed = 0  # volume per second

    def crossfade_to(self, track, duration=1.0):
        """Fade out current, then start new track with fade in."""
        self.pending_track = track
        self.fade_speed = self.target_volume / (duration / 2)
        # pygame fadeout is non-blocking — good
        pygame.mixer.music.fadeout(int(duration * 500))

    def handle_event(self, event):
        if event.type == MUSIC_END and self.pending_track:
            # Old track finished fading out — start new one
            pygame.mixer.music.load(self.pending_track)
            pygame.mixer.music.set_volume(0)
            pygame.mixer.music.play(-1)
            self.fading_in = True
            self.pending_track = None

    def update(self, dt):
        if self.fading_in:
            vol = pygame.mixer.music.get_volume() + self.fade_speed * dt
            if vol >= self.target_volume:
                vol = self.target_volume
                self.fading_in = False
            pygame.mixer.music.set_volume(vol)


music_mgr = MusicManager()


# === Sound effects — pygame.mixer has channels but no abstraction ===

# Channels are numbered 0-7 by default. You manage what plays where.
pygame.mixer.set_num_channels(16)

# Load sounds manually
try:
    sword_hit = pygame.mixer.Sound("assets/sounds/sword_hit.wav")
    arrow_fire = pygame.mixer.Sound("assets/sounds/arrow_fire.wav")
    ui_click = pygame.mixer.Sound("assets/sounds/ui_click.wav")
except pygame.error:
    sword_hit = arrow_fire = ui_click = None

# Volume control — per-sound, not per-channel-type.
# If you want "sfx volume" vs "ui volume" vs "music volume" with a master,
# you build that yourself.
master_volume = 1.0
sfx_volume = 0.8
ui_volume = 0.6
music_volume = 0.5


def play_sfx(sound):
    if sound:
        sound.set_volume(master_volume * sfx_volume)
        sound.play()


def play_ui_sound(sound):
    if sound:
        sound.set_volume(master_volume * ui_volume)
        sound.play()


def set_master_volume(vol):
    global master_volume
    master_volume = vol
    # Update music (the one persistent channel you can control)
    pygame.mixer.music.set_volume(master_volume * music_volume)
    # For already-playing sfx: no way to retroactively change their volume.
    # New sounds will pick up the new volume.


# === Sound pools — random selection without repeats ===

class SoundPool:
    """Play one of N sounds without repeating the last one. You build this yourself."""
    def __init__(self, sounds):
        self.sounds = sounds
        self.last_played = -1

    def play(self):
        if not self.sounds:
            return
        available = list(range(len(self.sounds)))
        if len(available) > 1 and self.last_played >= 0:
            available.remove(self.last_played)
        idx = random.choice(available)
        self.last_played = idx
        play_sfx(self.sounds[idx])


# Load pool sounds
try:
    knight_acks = SoundPool([
        pygame.mixer.Sound(f"assets/sounds/knight_ack_{i:02d}.wav")
        for i in range(1, 4)
    ])
except pygame.error:
    knight_acks = SoundPool([])

# Usage
play_sfx(sword_hit)
play_ui_sound(ui_click)
knight_acks.play()
music_mgr.crossfade_to("assets/music/battle.ogg", duration=1.0)

# Main loop integration needed:
running = True
while running:
    dt = clock.tick(60) / 1000.0
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        music_mgr.handle_event(event)
    music_mgr.update(dt)
    pygame.display.flip()

pygame.quit()

# What you built:
# - MusicManager class for non-blocking crossfade (~35 lines)
# - Volume hierarchy with manual multiplication
# - SoundPool for randomized playback without repeats
# - Can't retroactively change volume on already-playing sfx
# - ~120 lines total, and you need to wire music_mgr into your event + update loop
