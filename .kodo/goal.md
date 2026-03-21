# Goal: Fix specific visual defects — verified one-by-one by Gemini

## Approach

There is a numbered list of visual defects below. Work through them **one at a time**. For each defect:

1. Fix it
2. Render the relevant screenshot
3. Submit to Gemini asking: "Is this defect FIXED: [description]? Answer FIXED or NOT FIXED and explain what you see."
4. If Gemini says **NOT FIXED**: fix again and re-submit. Do NOT move on.
5. If Gemini says **FIXED**: move to the next defect.

**Rules:**
- Do NOT skip defects. Do NOT bundle multiple fixes and hope they work.
- Do NOT argue with Gemini's assessment. If Gemini says it's still broken, it's still broken.
- Each defect must get its own Gemini verification before moving on.
- After all defects are fixed, do a final full review (all 4 screenshots) and verify Gemini says no new defects were introduced.

## How to render screenshots

```python
from tests.screenshot.harness import render_scene
from pathlib import Path
import sys

# Battle vignette (1920x1080)
sys.path.insert(0, 'examples/battle_vignette')
def setup(game):
    from saga2d.assets import AssetManager
    game.assets = AssetManager(game.backend, base_path=Path('examples/battle_vignette/assets'))
    from battle_demo import BattleScene  # or TitleScene
    game.push(BattleScene())
image = render_scene(setup, tick_count=5, resolution=(1920, 1080))
image.save('/tmp/battle_gameplay.png')

# Tower defense (1280x960)
sys.path.insert(0, 'examples/tower_defense')
def setup(game):
    from saga2d.assets import AssetManager
    game.assets = AssetManager(game.backend, base_path=Path('examples/tower_defense/assets'))
    from main import GameScene  # or TitleScene
    game.push(GameScene())
image = render_scene(setup, tick_count=10, resolution=(1280, 960))
image.save('/tmp/td_gameplay.png')
```

## How to verify with Gemini

```python
import base64, json, os
from urllib.request import Request, urlopen

api_key = os.environ["GOOGLE_API_KEY"]
with open("/tmp/screenshot.png", "rb") as f:
    b64 = base64.b64encode(f.read()).decode()

parts = [
    {"text": "DEFECT CHECK: [paste specific defect description here]. Is this defect FIXED in this screenshot? Answer FIXED or NOT FIXED, then explain what you see."},
    {"inline_data": {"mime_type": "image/png", "data": b64}},
]
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
body = json.dumps({"contents": [{"parts": parts}]}).encode()
req = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
resp = urlopen(req, timeout=60)
result = json.loads(resp.read())
print(result["candidates"][0]["content"]["parts"][0]["text"])
```

## Defect List

### Battle Gameplay (HIGHEST PRIORITY — do these first)

**DEFECT 1: Units are nearly invisible on the battle grid.**
The warrior and skeleton sprites are tiny colored specks on the green grass. The gray rock obstacles are far more prominent than the actual playable units. Units should be the most visually prominent elements on the grid. Screenshot: battle_gameplay.png.

**DEFECT 2: Health bars overflow their side panel containers.**
In the WARRIORS and SKELETONS side panels, the health bar graphics extend beyond the panel boundaries. Screenshot: battle_gameplay.png.

### Battle Title

**DEFECT 3: Decorative sprites on the title screen are too small to be recognizable.**
The warrior and skeleton sprites flanking the title text are tiny — barely visible specks. They should be large enough to clearly show what the game is about. Screenshot: battle_title.png.

### Tower Defense Title

**DEFECT 4: Decorative sprites overlap and obscure the subtitle text.**
A row of green bush sprites is rendered on top of the "An Saga2D Example" subtitle, making the text unreadable. The subtitle should be fully visible with no sprites overlapping it. Screenshot: td_title.png.

**DEFECT 5: Enemy sprites in the top-left corner overlap each other randomly.**
Pink/magenta enemy sprites are piled on top of each other in the top-left, looking broken rather than decorative. They should either be removed or arranged with proper spacing. Screenshot: td_title.png.

**DEFECT 6: Tower sprites overlap into the title text area.**
Tower sprites are rendered on top of or too close to the "Tower Defense" title text, creating visual clutter. Text and decorative elements should not overlap. Screenshot: td_title.png.

### Tower Defense Gameplay

**DEFECT 7: Map does not fill the viewport.**
The tile map is cut off at the top (HUD/top bar not visible) and there is a large empty dark gap at the bottom and right side of the screen. The game content should fill the entire viewport. Screenshot: td_gameplay.png.

**DEFECT 8: "Starting soon..." text is clipped at the viewport edge.**
The wave announcement text is cut off on the right side of the screen. It should be fully visible. Screenshot: td_gameplay.png.

## Constraints
- Don't change the framework's public API
- Don't break existing tests (`uv run python -m pytest tests/ -x -q`)
- Don't add new dependencies
- Don't call `game.run()` — use `game.tick()` and the screenshot harness only
- All Python script executions must have `timeout: 30000` in the Bash tool
- Gemini's YES/NO answer is the source of truth — do not override it with your own judgment
