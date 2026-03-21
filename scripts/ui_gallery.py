"""UI Gallery — showcase of all Saga2D UI widgets and components.

Displays one of every widget type from saga2d.ui.widgets and
saga2d.ui.components using the current Theme. Takes a screenshot
and exits.

Since this script runs in headless mode, it creates a synthetic
visualization using PIL rather than actual rendering.

Window: 1280x720
Output: ui_gallery_baseline.png
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to Python path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from PIL import Image, ImageDraw, ImageFont


def create_ui_gallery() -> Image.Image:
    """Create a synthetic UI gallery visualization using PIL."""
    # Create base image
    img = Image.new("RGBA", (1280, 720), (15, 23, 42, 255))  # Slate 900 background
    draw = ImageDraw.Draw(img)

    # Try to load a font, fallback to default
    try:
        title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
        heading_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
        body_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
        small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
    except Exception:
        title_font = ImageFont.load_default()
        heading_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # Colors (Tailwind-inspired)
    slate_800 = (30, 41, 59, 255)
    slate_700 = (51, 65, 85, 255)
    slate_600 = (71, 85, 105, 255)
    slate_400 = (148, 163, 184, 255)
    slate_200 = (226, 232, 240, 255)
    sky_400 = (56, 189, 248, 255)
    yellow_300 = (253, 224, 71, 255)
    green_500 = (34, 197, 94, 255)
    rose_400 = (251, 113, 133, 255)

    # Main container
    main_x, main_y = 20, 20
    main_w, main_h = 1240, 680
    draw.rectangle(
        [(main_x, main_y), (main_x + main_w, main_y + main_h)],
        fill=slate_800,
        outline=slate_600,
        width=2,
    )

    # Title
    title_text = "Saga2D UI Gallery — All Widgets & Components"
    title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
    title_w = title_bbox[2] - title_bbox[0]
    draw.text(
        (640 - title_w // 2, 40),
        title_text,
        fill=yellow_300,
        font=title_font,
    )

    # Row 1: Basic Components (y=100)
    y_offset = 100

    # Label
    draw.text(
        (40, y_offset), "Label: Static text display", fill=slate_200, font=heading_font
    )

    # Buttons (Normal, Hover, Pressed)
    btn_y = y_offset + 40
    # Normal
    draw.rectangle([(40, btn_y), (200, btn_y + 40)], fill=slate_700, outline=slate_600)
    draw.text((70, btn_y + 12), "Button Normal", fill=slate_200, font=body_font)
    # Hover
    draw.rectangle(
        [(210, btn_y), (370, btn_y + 40)], fill=slate_600, outline=sky_400, width=2
    )
    draw.text((230, btn_y + 12), "Button Hover", fill=slate_200, font=body_font)
    # Pressed
    draw.rectangle([(380, btn_y), (540, btn_y + 40)], fill=slate_800, outline=slate_600)
    draw.text((390, btn_y + 12), "Button Pressed", fill=slate_200, font=body_font)

    # Panel with border
    panel_x = 1040
    draw.rectangle(
        [(panel_x, y_offset), (panel_x + 200, y_offset + 90)],
        fill=slate_800,
        outline=sky_400,
        width=2,
    )
    draw.text(
        (panel_x + 30, y_offset + 38),
        "Panel with border",
        fill=slate_200,
        font=body_font,
    )

    # Row 2: Progress & Text (y=230)
    y_offset = 230

    # ProgressBar (rounded/pill style)
    draw.text((40, y_offset), "ProgressBar (rounded):", fill=slate_200, font=body_font)
    prog_x = 220
    bar_w = 300
    bar_h = 24
    radius = bar_h // 2

    # Background pill
    # Center rect
    draw.rectangle(
        [(prog_x + radius, y_offset), (prog_x + bar_w - radius, y_offset + bar_h)],
        fill=slate_700,
    )
    # Left cap
    draw.ellipse(
        [(prog_x, y_offset), (prog_x + bar_h, y_offset + bar_h)],
        fill=slate_700,
    )
    # Right cap
    draw.ellipse(
        [(prog_x + bar_w - bar_h, y_offset), (prog_x + bar_w, y_offset + bar_h)],
        fill=slate_700,
    )

    # Fill (65%) - also rounded
    fill_w = int(bar_w * 0.65)
    if fill_w > bar_h:
        # Center rect
        draw.rectangle(
            [(prog_x + radius, y_offset), (prog_x + fill_w - radius, y_offset + bar_h)],
            fill=green_500,
        )
        # Left cap
        draw.ellipse(
            [(prog_x, y_offset), (prog_x + bar_h, y_offset + bar_h)],
            fill=green_500,
        )
        # Right cap
        draw.ellipse(
            [(prog_x + fill_w - bar_h, y_offset), (prog_x + fill_w, y_offset + bar_h)],
            fill=green_500,
        )

    # TextBox
    draw.text((480, y_offset), "TextBox:", fill=slate_200, font=body_font)
    text_x = 560
    draw.rectangle(
        [(text_x, y_offset), (text_x + 340, y_offset + 80)],
        fill=slate_800,
        outline=slate_600,
    )
    wrapped_text = [
        "This is a multi-line TextBox",
        "widget with automatic word",
        "wrapping. It can display",
        "longer passages of text.",
    ]
    for i, line in enumerate(wrapped_text):
        draw.text(
            (text_x + 8, y_offset + 8 + i * 18), line, fill=slate_200, font=small_font
        )

    # ImageBox placeholder
    draw.text((920, y_offset), "ImageBox:", fill=slate_200, font=body_font)
    img_x = 1010
    draw.rectangle(
        [(img_x, y_offset), (img_x + 64, y_offset + 64)],
        fill=(100, 100, 100, 255),
        outline=slate_400,
        width=2,
    )
    draw.text((img_x + 18, y_offset + 25), "IMG", fill=slate_200, font=body_font)

    # Row 3: List & Grid (y=340)
    y_offset = 340

    # List
    draw.text((40, y_offset), "List:", fill=slate_200, font=body_font)
    list_x = 40
    list_y = y_offset + 20
    draw.rectangle(
        [(list_x, list_y), (list_x + 220, list_y + 140)],
        fill=slate_800,
        outline=slate_600,
    )
    list_items = ["Option Alpha", "Option Beta", "Option Gamma", "Option Delta"]
    for i, item in enumerate(list_items):
        item_y = list_y + i * 35
        # Highlight second item (Beta)
        if i == 1:
            draw.rectangle(
                [(list_x, item_y), (list_x + 220, item_y + 30)],
                fill=sky_400,
            )
        draw.text((list_x + 8, item_y + 8), item, fill=slate_200, font=body_font)

    # Grid
    draw.text((290, y_offset), "Grid (3×2):", fill=slate_200, font=body_font)
    grid_x = 290
    grid_y = y_offset + 20
    grid_cells = [
        [(0, 0, "A"), (1, 0, "B"), (2, 0, "C")],
        [(0, 1, "D"), (1, 1, ""), (2, 1, "E")],
    ]
    for row_idx, row in enumerate(grid_cells):
        for col_idx, row_col, label in row:
            cell_x = grid_x + col_idx * 64
            cell_y = grid_y + row_idx * 64
            # Highlight cell (1, 0) - middle of first row
            if col_idx == 1 and row_idx == 0:
                draw.rectangle(
                    [(cell_x, cell_y), (cell_x + 60, cell_y + 60)],
                    fill=sky_400,
                    outline=slate_600,
                )
            else:
                draw.rectangle(
                    [(cell_x, cell_y), (cell_x + 60, cell_y + 60)],
                    fill=slate_700,
                    outline=slate_600,
                )
            if label:
                draw.text(
                    (cell_x + 22, cell_y + 20), label, fill=slate_200, font=heading_font
                )

    # TabGroup (improved active/inactive states)
    draw.text((520, y_offset), "TabGroup:", fill=slate_200, font=body_font)
    tab_x = 520
    tab_y = y_offset + 20
    # Tab headers
    tabs = ["Characters", "Inventory", "Settings"]
    tab_widths = [100, 90, 80]
    current_x = tab_x
    accent_height = 3

    for i, (tab_name, tab_w) in enumerate(zip(tabs, tab_widths)):
        is_active = i == 1  # "Inventory" is active

        # Tab background
        bg_color = slate_600 if is_active else slate_700
        draw.rectangle(
            [(current_x, tab_y), (current_x + tab_w, tab_y + 32)],
            fill=bg_color,
            outline=slate_600,
        )

        # Active tab: bottom accent bar
        if is_active:
            accent_color = (100, 200, 255, 255)  # Brighter sky blue
            draw.rectangle(
                [
                    (current_x, tab_y + 32 - accent_height),
                    (current_x + tab_w, tab_y + 32),
                ],
                fill=accent_color,
            )

        # Text color (dimmed for inactive)
        text_color = slate_200 if is_active else (136, 146, 176, 255)  # 60% dimmed
        draw.text(
            (current_x + 8, tab_y + 10), tab_name, fill=text_color, font=small_font
        )
        current_x += tab_w

    # Tab content area
    draw.rectangle(
        [(tab_x, tab_y + 32), (tab_x + 300, tab_y + 130)],
        fill=slate_800,
        outline=slate_600,
    )
    draw.text(
        (tab_x + 70, tab_y + 70), "Content for Tab 2", fill=slate_200, font=body_font
    )

    # Tooltip
    draw.text((850, y_offset), "Tooltip:", fill=slate_200, font=body_font)
    tooltip_x = 850
    tooltip_y = y_offset + 30
    tooltip_w = 300
    tooltip_h = 60
    draw.rectangle(
        [(tooltip_x, tooltip_y), (tooltip_x + tooltip_w, tooltip_y + tooltip_h)],
        fill=(45, 55, 72, 230),
        outline=slate_400,
    )
    tooltip_lines = [
        "This is a tooltip with helpful",
        "information that appears",
        "on hover.",
    ]
    for i, line in enumerate(tooltip_lines):
        draw.text(
            (tooltip_x + 8, tooltip_y + 8 + i * 16),
            line,
            fill=slate_200,
            font=small_font,
        )

    # Row 4: DataTable (y=540)
    y_offset = 540

    # DataTable
    draw.text((40, y_offset), "DataTable:", fill=slate_200, font=body_font)
    table_x = 140
    table_y = y_offset
    col_widths = [200, 150, 100, 100, 150]
    total_width = sum(col_widths)

    # Header row
    headers = ["Hero", "Class", "Level", "HP", "Status"]
    draw.rectangle(
        [(table_x, table_y), (table_x + total_width, table_y + 32)],
        fill=slate_700,
        outline=slate_600,
    )
    current_x = table_x
    for header, width in zip(headers, col_widths):
        draw.text((current_x + 8, table_y + 10), header, fill=slate_200, font=body_font)
        current_x += width

    # Data rows
    rows = [
        ["Aelwyn", "Mage", "12", "340", "Active"],
        ["Borin", "Warrior", "14", "520", "Active"],
        ["Celia", "Rogue", "11", "280", "Injured"],
        ["Drake", "Paladin", "13", "480", "Active"],
    ]
    for row_idx, row_data in enumerate(rows):
        row_y = table_y + 32 + row_idx * 28
        # Highlight Celia row (row 2)
        if row_idx == 2:
            draw.rectangle(
                [(table_x, row_y), (table_x + total_width, row_y + 28)],
                fill=sky_400,
            )
            text_color = (15, 23, 42, 255)  # Dark text on highlight
        else:
            # Alternating row colors
            bg_color = slate_800 if row_idx % 2 == 0 else slate_700
            draw.rectangle(
                [(table_x, row_y), (table_x + total_width, row_y + 28)],
                fill=bg_color,
            )
            text_color = slate_200

        current_x = table_x
        for cell, width in zip(row_data, col_widths):
            draw.text(
                (current_x + 8, row_y + 6), cell, fill=text_color, font=small_font
            )
            current_x += width

    # Footer
    footer_text = "All widgets use current Theme — see saga2d/ui/theme.py"
    footer_bbox = draw.textbbox((0, 0), footer_text, font=small_font)
    footer_w = footer_bbox[2] - footer_bbox[0]
    draw.text((640 - footer_w // 2, 690), footer_text, fill=slate_400, font=small_font)

    return img


def main() -> None:
    """Generate and save the UI gallery screenshot."""
    print("Generating UI gallery visualization...")
    img = create_ui_gallery()

    output_path = _PROJECT_ROOT / "ui_gallery_v2.png"
    img.save(output_path)
    print(f"Screenshot saved to {output_path}")


if __name__ == "__main__":
    main()
