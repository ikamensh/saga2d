# Campaign transition reading

CampaignScene uses the existing 100% / 125% Reading size for departure offers,
retinue labels and focused details, recovery rules, completed-shard records,
hero-build summaries and complete save errors. Its large headings retain their
existing size; ordinary action controls remain the same size. The logical canvas
is still 1280×800. This extends the scoped reading preference, not the shard or
battle HUD.

`T` opens Reading size. Apply, Cancel, returning from Saves and window resizing
preserve selected troop/relic IDs and each column's first visible item. If the
anchored page becomes shorter, a keyboard cursor pushed off-page moves to its
first visible row. Space always operates on a visible gold-outlined choice.
Left/Right selects a column, Up/Down still traverses one logical item at a time,
and mouse Previous/Next focuses the destination page's first item. The existing
`PlayerInput.choose_retinue` route and Keep/Leave button labels remain compatible.

The scene reserves measured ordinary error, focused-detail, funding and rules space before
packing whole retinue rows. Offers and endings use whole prose sections when an
error requires an additional page, with visible Previous/Next and PageUp/PageDown.
When a diagnostic leaves insufficient space for even one reviewed entry, the
same screen opens its complete diagnostic view. `reading_text_pages` packs exact
text with measured heights, including long path tokens; joining its pages loses
no characters. The player can return to the unchanged review, then reopen the
diagnostic with **Read error / D**. Hidden retinue/abandon commands cannot act while
reading it. This was verified with a legitimate 760-character nested save path
whose actual filesystem error contains 1,597 characters.

No description or error is truncated or made smaller to fit. Only visible offer
buttons activate their numbered shortcuts. Retinue selection remains local until
the checkpointed departure/recovery command; ordinary save errors do not consume
it. A valid exact manual snapshot can still recover a blocked automatic checkpoint.

Saga2D supplies `Scene.measure`, wrapped Labels and layout/input ownership;
Shardbound supplies `reading_pages`, available space, selection and campaign rules.
CampaignPlanScene is unchanged by this increment. There is no new schema,
settings key, framework widget or history browser.

Verification:

```sh
.venv/bin/python -m pytest tests/eador/test_campaign_reading.py tests/eador/test_campaign_scene.py tests/eador/test_campaign_plan_reading.py -q
.venv/bin/python tools/verify_eador_campaign_reading.py --output /tmp/shardbound-campaign-reading
.venv/bin/python tools/verify_eador_campaign.py --middle foundries --finale throne --recovery
```

The retained verifier prepares victories/recoveries through public campaign
commands in all three current modes, both second-stage contracts and finales,
a full earned relic inventory, a declined recovery and a second lost capital.
Historical Challenge-1 departure/recovery fixtures are loaded unchanged. It
checks actual funding, troop health, relic descriptions, skill ranks and records,
walks every item through public input at both reading sizes in 1280×720,
1280×800 and 1920×1080 windows, and exercises real filesystem failures and exact
save reloads. The native regression originally found that an offers screen at
125% could not fit the complete macOS directory error; section paging fixes that
case without discarding the error or advice.

[Retained native evidence](evidence/shardbound-campaign-reading-8b686c3/README.md)
records the exact source, full suite, stress outcomes and seven inspected frames.
