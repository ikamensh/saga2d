"""Sounds for recorded battle events, independent of authoritative battle rules."""


_CONTACTS = ('attack', 'pin', 'brace', 'retaliation')


def direct_event_duration(trace):
    """One direct-order clock for poses, sound contacts and health notices."""
    return min(.65, 1.4 / len(trace.events))


def is_magic_attack(actor, hero_class):
    """Classify the existing ranged staff/rune weapons for both sound and drawing."""
    return actor.attack_range > 1 and (actor.kind in ('adept', 'healer')
                                      or actor.kind == 'hero' and hero_class == 'Wizard')


def seal_progress_change(battle, event):
    """Only a recorded, nonterminal hold transition can celebrate or break a seal."""
    if event.kind != 'objective' or battle.objective.kind != 'hold' or event.after.outcome is not None:
        return 0
    return event.after.progress - event.before.progress


def event_cues(battle, event, hero_class):
    """Return release and contact cues; the composite magic cue plays only at contact."""
    progress = seal_progress_change(battle, event)
    if progress:
        return None, 'seal_gain' if progress > 0 else 'seal_loss'
    if event.kind in _CONTACTS:
        actor = battle.unit(event.actor_id)
        ranged = event.kind in ('attack', 'pin') and actor.attack_range > 1
        magic = ranged and is_magic_attack(actor, hero_class)
        if magic:
            return None, 'bolt'
        contact = 'attack_heavy' if actor.kind in ('guard', 'warden', 'skyrider') else 'attack_hit'
        return 'attack_arrow' if ranged else None, contact
    release = 'move' if event.kind in ('move', 'swap', 'repulse') else None
    contact = {'guard': 'guard', 'bolt': 'bolt', 'heal': 'heal', 'rally': 'confirm',
               'swap': 'confirm', 'smoke': 'confirm'}.get(event.kind)
    return release, contact


class AttackSounds:
    """Drain direct attack sounds once, on the same elapsed clock as visual feedback.

    A newer order may replace the visual trace. Finish its already-earned contacts
    first, without starting late projectile releases. Discard this local object
    when leaving/loading the scene; it owns no timer or audio-manager callback.
    """

    def __init__(self, battle, trace, hero_class):
        self.pending = []
        duration = direct_event_duration(trace)
        for index, event in enumerate(trace.events):
            if event.kind not in _CONTACTS:
                continue
            release, contact = event_cues(battle, event, hero_class)
            if release:
                self.pending.append((index * duration, release, False))
            self.pending.append(((index + .5) * duration, contact, True))

    def advance(self, elapsed):
        cues = [cue for when, cue, _ in self.pending if when <= elapsed]
        self.pending = [item for item in self.pending if item[0] > elapsed]
        return cues

    def finish(self):
        cues = [cue for _, cue, contact in self.pending if contact]
        self.pending.clear()
        return cues
