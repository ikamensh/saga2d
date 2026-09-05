# Linked campaign player journey

At the title, **L** starts a three-shard campaign with the selected hero and
seed, beginning in Frontier. **Enter** retains the quick single-shard mode
and its selected world. Completing Westwatch offers Rootward in Elderwild
or the Foundries in Ruins. The finale visits the remaining theme, choosing
between an unrestricted rout and the timed Last Gate seal.

The departure screen compares both contracts before committing. Choose with
**1 / 2**, then select up to two surviving veterans and two owned relics.
**Left / Right** changes the column, **Up / Down** browses every item and
**Space** toggles it. Mouse buttons provide the same choices. **Esc** returns
to contract comparison. The preview names the destination, starting wealth
and fresh Militia; **Enter** commits the expedition. Quicksaving here saves
the finished shard and its recorded offers; an unsubmitted retinue is a UI
draft. Departure requires a successful pre-transition autosave and attempts
another checkpoint after arrival.

The first lost capital offers one recovery expedition in its exact initial
world with 60 gold and two crystals. The hero's learned skills and selected
surviving veterans/relics persist, while local holdings and buildings reset.
Declining recovery or losing another capital ends the campaign. The ending
records all completed shards, turns, casualties, hero levels and garrisons.
Saves remain accessible at departures, recovery and endings.

## Verification

`tools/verify_eador_campaign.py` executes the existing public-command campaign
policy through actual controls. Model reads choose a legal strategy; every
build, recruit, travel, battle round, reward, equipment change and transition
uses a key or mouse event. The policy's reload seam uses F5/F9 and compares
the complete saved state. No prepared victory is injected into this journey.

On 2026-09-06, the native Pyglet checks completed:

| Route | Recovery | Input activations | Exact reloads | Automated runtime |
|---|---|---:|---:|---:|
| Rootward → Gate | No | 347 | 11 | 5.86 seconds |
| Foundries → Throne | Yes, stage two | 371 | 13 | 5.51 seconds |

Captures of the title, both sets of offers, retinues, arrivals, recovery and
endings were inspected. These timings measure automated execution, not human
play duration or enjoyment. Tests also reproduce a real unavailable save
directory: the failed checkpoint leaves the reviewed departure untouched and
the same selection succeeds after storage becomes available. A separate
input journey declines recovery, reloads that ending, and returns to title.

Campaign rules and progression remain in `eador.campaign`/`eador.model`; these
screens use ordinary Saga2D scenes, buttons and save storage. No campaign
concept or retinue state was added to the framework.
