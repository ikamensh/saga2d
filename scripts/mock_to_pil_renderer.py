"""Replay MockBackend recorded draw calls onto a PIL Image.

This module provides a renderer that takes the recorded draw calls from
MockBackend (rects, circles, texts, images) and renders them onto a PIL
Image, allowing screenshot generation in headless environments without
requiring a GPU/display.
"""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageDraw, ImageFont


class MockToPILRenderer:
    """Renders MockBackend draw calls to a PIL Image."""

    def __init__(
        self,
        width: int,
        height: int,
        background: tuple[int, int, int, int] = (15, 23, 42, 255),
    ) -> None:
        """Initialize the renderer.

        Args:
            width: Image width in pixels
            height: Image height in pixels
            background: RGBA background color
        """
        self.width = width
        self.height = height
        self.background = background
        self.image = Image.new("RGBA", (width, height), background)
        self.draw = ImageDraw.Draw(self.image)

        # Font cache
        self._font_cache: dict[int, ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}

    def _get_font(self, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        """Get or create a font of the given size."""
        if size not in self._font_cache:
            try:
                # Try to load a system font
                self._font_cache[size] = ImageFont.truetype(
                    "/System/Library/Fonts/Helvetica.ttc", size
                )
            except Exception:
                # Fallback to default
                self._font_cache[size] = ImageFont.load_default()
        return self._font_cache[size]

    def render_rects(self, rects: list[dict[str, Any]]) -> None:
        """Render recorded rectangles."""
        for rect in rects:
            x = rect["x"]
            y = rect["y"]
            w = rect["width"]
            h = rect["height"]
            color = rect["color"]
            opacity = rect.get("opacity", 1.0)

            # Apply opacity to color
            r, g, b, a = color
            a = int(a * opacity)
            final_color = (r, g, b, a)

            # Draw rectangle
            self.draw.rectangle(
                [(x, y), (x + w, y + h)],
                fill=final_color,
            )

    def render_circles(self, circles: list[dict[str, Any]]) -> None:
        """Render recorded circles."""
        for circle in circles:
            x = circle["x"]
            y = circle["y"]
            radius = circle["radius"]
            color = circle["color"]
            opacity = circle.get("opacity", 1.0)

            # Apply opacity to color
            r, g, b, a = color
            a = int(a * opacity)
            final_color = (r, g, b, a)

            # Draw circle (ellipse with equal width/height)
            # Note: PIL's ellipse is defined by bounding box
            self.draw.ellipse(
                [(x - radius, y - radius), (x + radius, y + radius)],
                fill=final_color,
            )

    def render_texts(self, texts: list[dict[str, Any]]) -> None:
        """Render recorded text."""
        for text in texts:
            content = text["text"]
            x = text["x"]
            y = text["y"]
            font_size = text["font_size"]
            color = text["color"]

            # Get font
            font = self._get_font(font_size)

            # Draw text
            # Note: MockBackend uses top-left positioning
            self.draw.text(
                (x, y),
                content,
                fill=color,
                font=font,
            )

    def render_images(self, images: list[dict[str, Any]]) -> None:
        """Render recorded images.

        Note: This requires the actual PIL Image objects to be available,
        which they typically aren't in pure mock backend tests. This method
        is a placeholder for completeness.
        """
        for img_call in images:
            x = img_call["x"]
            y = img_call["y"]
            img = img_call.get("image")
            opacity = img_call.get("opacity", 1.0)

            if img is None or not isinstance(img, Image.Image):
                # Skip if no actual image data
                continue

            # Apply opacity if needed
            if opacity < 1.0:
                img = img.copy()
                img.putalpha(int(255 * opacity))

            # Paste image
            self.image.paste(img, (x, y), img if img.mode == "RGBA" else None)

    def render_all(
        self,
        rects: list[dict[str, Any]],
        circles: list[dict[str, Any]],
        texts: list[dict[str, Any]],
        images: list[dict[str, Any]] | None = None,
    ) -> Image.Image:
        """Render all draw calls in order and return the final image.

        Args:
            rects: List of rectangle draw calls
            circles: List of circle draw calls
            texts: List of text draw calls
            images: List of image draw calls (optional)

        Returns:
            The rendered PIL Image
        """
        # Render in order: rects, circles, images, texts
        # This matches the typical draw order in UI rendering
        self.render_rects(rects)
        self.render_circles(circles)
        if images:
            self.render_images(images)
        self.render_texts(texts)

        return self.image

    def save(self, filename: str) -> None:
        """Save the rendered image to a file."""
        self.image.save(filename)
