# Shardbound — local store-description draft

**Unpublished draft for review.** This is not a Steam listing or a release
announcement. The copy below describes the current development game; it must
be checked against the actual candidate before publication.

## Short description

Lead a hero and a persistent army through a fantasy strategy campaign.
Develop your realm, investigate guarded sites and command turn-based hex
battles. Choose which veterans and relics accompany you into the next shard.

## About the game

Your stronghold needs soldiers, supplies and time. Build a marketplace to
fund your army, train specialist troops, or invest in magic and recovery.
Meanwhile, a rival expedition advances across the shard. Inspect its next
target, intercept its army and seize the opening to attack its stronghold.

Take command as a Commander, Warrior, Scout or Wizard. Choose between two
advancement disciplines for each hero, recruit from ten troop roles and
discover twelve relics. Veterans keep their experience; fallen troops are
lost. A Warden can exchange places with an exposed ally, a Sapper can block
a firing lane with Smoke, and a Rune Adept can push an enemy out of position.

Guarded expeditions ask you to do more than defeat an army. Hold a seal,
extract cargo or fight through an ambush. Inspect deployments, deadlines
and available approaches before committing. Cover, occupied hexes and
remaining orders can determine whether your hero reaches an exit in time.
Issue orders yourself or use optional automatic rounds, then watch the
resolved actions play out in sequence. Playback can be skipped.

The current game includes a three-shard linked campaign with choices of
the next challenge and a standalone shard mode. Carry selected veterans,
relics and your learned hero skills between shards. Three world themes,
seed selection and three difficulty settings vary the starting conditions.
Twelve authored encounter patterns use rout, hold and extraction objectives.
Their locations vary within progression bands; inspect a province or the
Codex to find the current sources before committing to a route.
An in-game Field Guide and Codex explain the rules. Manual saves, rolling
autosaves, sound controls, reduced motion and larger reading text are
available.

Two players can command a shared realm and army through online room codes.
Direct LAN connections are also available. Co-op shares decisions and progress;
it is not competitive multiplayer.

## Current development status

This is a development checkpoint, not an Early Access release. Strategic
balance, campaign pacing, first-time guidance and presentation are still
under review. Human playtests, audio listening review and release-platform
verification remain outstanding. The current presentation uses original
painted environments and hero portraits, procedural terrain and miniatures,
and synthesized music and effects. The app still uses a development icon and
system fonts. Competitive multiplayer, diplomacy and an astral metacampaign
are absent.

## Internal claim audit — not store copy

Reviewed against the source worktree on 2026-09-07. This audit identifies
implemented behavior; it does not establish balance, enjoyment, platform
readiness or acceptance of G18. The current release gates remain incomplete
in [early-access-progress.md](early-access-progress.md).

| Copy claim | Source to recheck for the candidate | Limits retained in the copy |
|---|---|---|
| Realm investment, rival targets and interception | `eador/model.py`: `BUILDINGS`, campaign commands; `eador/rival.py`; `eador/rival_scene.py` | Describes available decisions, without claiming equally strong strategies or a particular playtime. |
| Four heroes, two disciplines each, ten recruitable roles, twelve relics | `eador/model.py`: `HERO_CLASSES`, `RECRUITABLE`; `eador/content.py`: `SKILLS`, `RELICS` | Catalogue counts do not prove distinct viable whole-campaign builds. |
| Veteran experience, casualties and specialist orders | `eador/model.py`: `Troop`, battle resolution; `eador/battle.py`; `eador/content.py` | Individual troops, not stacked armies; named abilities are examples, not a promise that every role has an active ability. |
| Adventure approaches, deadlines and twelve authored patterns across three objectives | `eador/content.py`: `SITES`; `eador/encounters.py`; `eador/encounter_scene.py`; [eador-causeway.md](eador-causeway.md) | Twelve is the implemented authored catalogue, not twelve encounters guaranteed in each shard. Ordinary renamed sites do not add to that count. |
| Manual orders, optional automatic rounds and skippable ordered playback | `eador/battle.py`; `eador/scene.py`: `BattleScene`; `eador/battle_playback_scene.py` | No claim that automatic play finds the best plan or that playback changes resolved outcomes. |
| Three linked shards, destination choices, selected carryover and standalone mode | `eador/campaign.py`; `eador/campaign_scene.py`; `eador/model.py`: campaign departure; `eador/scene.py`: `TitleScene` | Selected veterans and relics travel; local buildings and holdings do not. |
| Three themes, seeds and three difficulties | `eador/worldgen.py`: `THEMES`; `eador/difficulty.py`: `DIFFICULTIES`; `eador/scene.py`: `TitleScene` | Does not claim unlimited content, tested difficulty balance or a different map topology on every seed. |
| Varied sites and recorded source locations | `eador/worldgen.py`; `eador/scene.py`; `eador/codex.py`; [placement and route evidence](evidence/adventure-variety/README.md) | Saved maps keep their recorded layout. Package identity does not imply equal access costs or difficulty. |
| Shared-realm online and LAN co-op | `eador/multiplayer.py`; `saga2d/multiplayer_ui.py`; [online guide](online-multiplayer.md) | Shared control of one army, not competitive play or a server-availability guarantee. |
| Field Guide, Codex, saves and settings | `eador/scene.py`: `HelpScene`; `eador/codex.py`; `eador/persistence.py`; `eador/settings_scene.py`; `eador/preferences.py` | “Larger reading text” describes the 100/125 reading setting; it does not promise every marker and control scales. |
| Original painted/generated artwork, procedural art and synthesized audio | `eador/art.py`; `eador/sound.py`; `eador/assets/VISUAL-PROVENANCE.md`; `eador/assets/hero-portrait-provenance.json`; `eador/assets/AUDIO-PROVENANCE.md` | Environment and portrait provenance records image generation; other graphics use drawing code. Listening quality is still unverified. |
| Development status and known gaps | `eador/release.py`; [early-access-criteria.md](early-access-criteria.md); [early-access-progress.md](early-access-progress.md) | No release date, price, platform assurance, public support channel or promised future feature. |

Before publication, record the packaged build identity, reread its About
screen, check these claims in that build and select gameplay media captured
from it. Existing source reports and older development archives do not
substitute for that candidate audit. Public support details and platform
claims require actual verified arrangements; this draft supplies neither.
