"""Tests for saga2d.ui.theme."""


from saga2d.ui.theme import Style, Theme


class TestStyle:
    def test_all_fields_optional(self) -> None:
        s = Style()
        assert s.font is None
        assert s.font_size is None
        assert s.text_color is None
        assert s.background_color is None
        assert s.padding is None
        assert s.border_color is None
        assert s.border_width is None
        assert s.hover_color is None
        assert s.press_color is None

    def test_partial_override(self) -> None:
        s = Style(font_size=48, text_color=(255, 0, 0, 255))
        assert s.font_size == 48
        assert s.text_color == (255, 0, 0, 255)
        assert s.font is None


class TestTheme:
    def test_resolve_label_style_defaults(self) -> None:
        t = Theme()
        r = t.resolve_label_style(None)
        assert r.font == "serif"
        assert r.font_size == 24
        assert r.text_color == (248, 250, 252, 255)
        assert r.background_color == (0, 0, 0, 0)
        assert r.padding == 0

    def test_resolve_label_style_explicit_overrides(self) -> None:
        t = Theme()
        r = t.resolve_label_style(Style(font_size=64, font="sans"))
        assert r.font_size == 64
        assert r.font == "sans"
        assert r.text_color == (248, 250, 252, 255)  # inherited

    def test_resolve_button_style_state_normal(self) -> None:
        t = Theme()
        r = t.resolve_button_style(None, "normal")
        assert r.background_color == (51, 65, 85, 255)

    def test_resolve_button_style_state_hovered(self) -> None:
        t = Theme()
        r = t.resolve_button_style(None, "hovered")
        assert r.background_color == (71, 85, 105, 255)

    def test_resolve_button_style_state_pressed(self) -> None:
        t = Theme()
        r = t.resolve_button_style(None, "pressed")
        assert r.background_color == (56, 189, 248, 255)

    def test_resolve_button_style_state_disabled(self) -> None:
        t = Theme()
        r = t.resolve_button_style(None, "disabled")
        assert r.background_color == (30, 41, 59, 255)
        assert r.text_color == (100, 116, 139, 200)

    def test_resolve_button_style_explicit_hover_overrides_state(self) -> None:
        t = Theme()
        custom = Style(hover_color=(200, 0, 0, 255))
        r = t.resolve_button_style(custom, "hovered")
        assert r.background_color == (200, 0, 0, 255)

    def test_resolve_panel_style_defaults(self) -> None:
        t = Theme()
        r = t.resolve_panel_style(None)
        assert r.background_color == (30, 41, 59, 255)
        assert r.padding == 16

    def test_resolve_panel_style_explicit_override(self) -> None:
        t = Theme()
        r = t.resolve_panel_style(Style(padding=32))
        assert r.padding == 32
        assert r.background_color == (30, 41, 59, 255)  # inherited

    def test_none_means_inherit(self) -> None:
        t = Theme(label_text_color=(100, 100, 100, 255))
        r = t.resolve_label_style(Style(font_size=None, text_color=None))
        assert r.font_size == 24  # theme default
        assert r.text_color == (100, 100, 100, 255)

    def test_button_min_width_property(self) -> None:
        t = Theme()
        assert t.button_min_width == 200
