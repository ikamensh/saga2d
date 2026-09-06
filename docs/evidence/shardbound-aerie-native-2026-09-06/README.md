# Aerie native paid journeys

All five scripted journeys passed against clean source
`3ba80da54c4de436f8123d4c74c896949e2316ae`, after merging committed main
`94bc7b1`. The combined suite passed 1,128 tests. Every report's 83 source
hashes matched both the checkout and the recorded Git revision after execution.
[Provenance](provenance.json) includes hashes of the retained reports and images.

These are actual Pyglet frames and keyboard/mouse activations through
`PlayerInput`, `PlayerState` and `ControlOrders`. Preparation buys buildings and
troops through the game UI and uses the explicit auto command for prior
conquests. Every Aerie order is manual. F5/F9 checks compare the complete saved
campaign exactly. Screenshots were opened and visually inspected.

| Standard, seed 7 | Input activations | Exact reloads | Rout round | Missing HP | Mana spent |
|---|---:|---:|---:|---:|---:|
| [Western Commander](western.json) | 200 | 10 | 4 | 53 | 4 |
| [Western with Heal](western-heal.json) | 202 | 10 | 4 | 45 | 8 |
| [Northern Commander](northern.json) | 174 | 7 | 3 | 34 | 8 |
| [Six-body Scout](scout.json) | 190 | 9 | 5 | 27 | 4 |
| [Failed sortie and saved retry](failed-retry.json) | 664 | 65 | 1 on retry | 58 already wounded | 4 on retry |

Total: **1,430 input activations, 101 exact save/reloads and 362 manual battle
orders**, including the failed attempt. Commander preparation pays 395 gold and
seven crystals; Scout pays 200 gold and no crystals. The replacement after the
loss costs another 60 gold and three crystals. Both assemblies themselves are
free and keep identical finite defenders, terrain and reward.

The [western deployment](western-deployment.png) allows the enemy flyers to
land behind the army. Its [Repulse forecast](western-repulse.png),
[Brace position](western-brace.png) and [flight landing](western-flight.png)
show the reaction and counter-sortie. The [northern deployment](northern-deployment.png)
instead permits an [early focused Bolt](northern-first-bolt.png), followed by
a [different hill landing](northern-flight.png) and ordered corridor opening.
The cheaper Scout demonstrates [Swap extraction](scout-swap.png) and
[exact healing](scout-heal.png), without a purchased flyer or Adept.

The failure deliberately attacks with the Skyrider before support is ready,
then keeps guarding without advancing. It loses five soldiers and the hero at
round 56. That artificial refusal to advance tests finite persistence, not
ordinary encounter pacing. The [loss result](failed-result.png),
[paid replacement](paid-replacement.png), [wounded retry briefing](retry-briefing-125.png),
[12-HP Bolt forecast](retry-bolt.png) and [retry victory](retry-victory.png)
show the complete path. Only the original surviving Archer returns, at 12 HP;
there is no partial-kill reward or regenerated guard. The replacement purchase
is real, although the final Bolt does not require it to win. The reward is
granted once and subsequent exploration is rejected without state mutation.

The full [125% briefing](western-briefing-125.png) and tactical forecasts are
readable. One shared ShardScene issue remains visible in
[the final reward frame](retry-reward-sidebar-clip.png): the exhausted-action
guidance sentence clips at the right edge. This was reported separately for
the root-owned scene layout; it does not invalidate the recorded commands or
save/reward checks. Do not describe this revision as visually flawless.

Reproduce from the recorded source, on a machine with an active graphical
session and the project dependencies installed:

```sh
/usr/bin/caffeinate -u -t 5
PYTHONPATH=. /usr/bin/caffeinate -d -i python tools/verify_eador_aerie.py \
  --plan western --output /tmp/aerie-native/western
```

Repeat with `western-heal`, `northern`, `scout` and `failed-retry`. The machine
was macOS 26.6.2 arm64, Python 3.13.2, with a 1280×800 logical window and
2560×1600 framebuffer; briefing reading size was 125%. The five mock input
integration tests are in `tests/eador/test_aerie_scene.py`.

This is scripted native evidence for these purchased plans, not independent
human playtesting or a release-depth claim. Earlier randomized/model probes
remain attributed to their own source in
[the model evidence](../shardbound-aerie-model-2026-09-06/README.md).
