"""The local high-score browser, shared by the title and match results."""

from saga2d import Anchor, Button, Column, Label, Row, SaveError, Scene, Style
from tribes.scores import HighScores
from tribes.style import BAD, GHOST_BUTTON, GOLD, RESULTS_STYLE


class HighScoresScene(Scene):
    transparent = True
    pop_on_cancel = True

    def __init__(self, *, size: int = 14, tribes: int = 3, highlight: str | None = None, error: str | None = None) -> None:
        self.size = size
        self.tribes = tribes
        self.highlight = highlight
        self.error = error

    def on_enter(self) -> None:
        self._build()

    def _build(self) -> None:
        self.ui.clear()
        panel = Column(spacing=7, anchor=Anchor.CENTER, style=RESULTS_STYLE)
        panel.add(Label("High scores", text_style="title"))
        panel.add(Label("Stored on this device · Best 10 for each map setup", text_style="sub"))
        self.ui.add(panel)
        try:
            if self.error is not None:
                raise SaveError(self.error)
            self.entries = HighScores(self.game.data_dir).load()
        except SaveError as error:
            panel.add(Label(str(error), text_style="body", text_color=BAD, width=694, wrap=True))
            panel.add(Button("Back", shortcut="Esc", on_click=self.game.pop, style=GHOST_BUTTON, width=220))
            return
        panel.add(Row(
            Button(f"Map {self.size}×{self.size}", shortcut="M", on_click=self.next_size, width=240),
            Button(f"{self.tribes} tribes", shortcut="P", on_click=self.next_tribes, width=240), spacing=12,
        ))
        widths = (44, 114, 88, 92, 64, 92, 100)
        headings = ("Rank", "Tribe", "Score", "Result", "Rounds", "Seed", "Date")
        panel.add(Row(*(Label(name, text_style="caption", width=width) for name, width in zip(headings, widths)), spacing=0))
        table = Column(spacing=3, height=287, width=sum(widths))
        entries = [e for e in self.entries if (e.size, e.tribes) == (self.size, self.tribes)]
        if not entries:
            table.add(Label("No completed games for this setup.", text_style="body", height=180))
        for rank, entry in enumerate(entries[:10], 1):
            selected = entry.run_id == self.highlight
            values = (f"{rank}.", entry.tribe, f"{entry.score:,}", "Victory" if entry.victory else "Defeat",
                      str(entry.rounds), str(entry.seed), entry.completed_at[:10])
            row = Row(spacing=0, height=26, style=Style(background_color=(255, 224, 120, 28) if selected else (255, 255, 255, 6),
                                                     padding=0, border_width=0, radius=4))
            for value, width in zip(values, widths):
                row.add(Label(value, text_style="sub", width=width, text_color=GOLD if selected else None))
            table.add(row)
        panel.add(table)
        panel.add(Label("One best finish per run. Ties: fewer rounds, then earlier finish.", text_style="sub"))
        panel.add(Button("Back", shortcut="Esc", on_click=self.game.pop, style=GHOST_BUTTON, width=220))

    def next_size(self) -> None:
        sizes = sorted({11, 14, 18, self.size, *(e.size for e in self.entries)})
        self.size = sizes[(sizes.index(self.size) + 1) % len(sizes)]
        self._build()

    def next_tribes(self) -> None:
        counts = sorted({2, 3, 4, self.tribes, *(e.tribes for e in self.entries)})
        self.tribes = counts[(counts.index(self.tribes) + 1) % len(counts)]
        self._build()

    def draw(self) -> None:
        self.draw_rect(0, 0, *self.game.resolution, (4, 6, 12, 200))
