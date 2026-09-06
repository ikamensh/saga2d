# Battle pieces and persistent health

Source **0e4dec3** keeps remaining HP and its bar on each piece's base, within
the occupied hex. Exact current/maximum HP remains in the selected/hovered
panel. Smaller, lowered pieces leave adjacent silhouettes clear. Separate
corner ticks retain visible selection; the pointer uses a continuous outline.
No rules, picking coordinates, saves or framework interfaces changed.

The new public-scene regression failed on both the opening and earned crowded
formation because health text extended outside its unit's hex. It now passes
at all three supported window sizes and both reading settings without changing
State. The combined footprint, forecast, playback, Guard, Pin and Vault checks
pass **23 tests**. A first combined run exposed the new test's shared preferences
directory; its profile is now isolated beneath its own temporary directory.

Twelve native opening/crowded layouts were captured; the two smallest 125%
frames were inspected. Independent review caught reduced selection visibility,
leading to the corner ticks. The retained final Pin and Brace frames were then
inspected by root and an independent reviewer: the markers and neighboring
heads/weapons remain visible. These two final frames include the selection fix.

The native Pin verifier also needed to finish the existing playback modal
before checking the next turn's cooldown control. Its first run failed there;
after using the shared visible Finish control, the complete forecast, status,
cooldown, save/reload and earned Watch Bell journey passes. All windows close.

Reproduce that final native path, one job at a time:

```sh
caffeinate -diu uv run python tools/verify_eador_pin.py --out /tmp/shardbound-pin-footprints
```

This is bounded presentation evidence, not completion of G10 or G11.
