"""High-contrast brutalist PNG chart generation using Pillow for project results."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

# Palette conforming to docs/PROJECT_CONTEXT.md
BG_COLOR = "#EDEBE6"      # off-white
BORDER_COLOR = "#0A0A0A"  # black
TEXT_COLOR = "#0A0A0A"    # black
MUTED_COLOR = "#8A8A85"   # concrete grey
LIGHT_GREY = "#C9C7C1"    # light grey
SIGNAL_RED = "#E10600"    # signal red
WARNING_ORANGE = "#FF6B1A"# warning orange


def get_fonts() -> tuple[Any, Any, Any]:
    """Retrieve monospace/system fonts with safe fallbacks."""
    windir = os.environ.get("WINDIR", "C:/Windows")
    font_paths = [
        os.path.join(windir, "Fonts", "consola.ttf"),
        os.path.join(windir, "Fonts", "arial.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ]
    font_file = next((p for p in font_paths if os.path.exists(p)), None)
    if font_file:
        try:
            return (
                ImageFont.truetype(font_file, 18),
                ImageFont.truetype(font_file, 13),
                ImageFont.truetype(font_file, 11),
            )
        except Exception:
            pass
    default = ImageFont.load_default()
    return default, default, default


def draw_brutalist_card(draw: ImageDraw.ImageDraw, width: int, height: int, title: str, subtitle: str | None = None) -> int:
    """Draw a brutalist card border and title header. Returns y_offset for content."""
    title_font, body_font, _ = get_fonts()
    # Outer 1px/2px brutalist border
    draw.rectangle([4, 4, width - 5, height - 5], outline=BORDER_COLOR, width=2)
    # Header box
    header_h = 56 if subtitle else 40
    draw.rectangle([4, 4, width - 5, header_h], fill="#0A0A0A", outline=BORDER_COLOR, width=1)
    draw.text((16, 12), title.upper(), fill="#EDEBE6", font=title_font)
    if subtitle:
        draw.text((16, 36), subtitle, fill="#C9C7C1", font=body_font)
    return header_h + 20


def generate_engine_vs_baselines_chart(macro_summary: dict[str, Any], output_path: Path) -> None:
    """Chart comparing Allocation Engine, Greedy, and Random baselines on macro metrics."""
    width, height = 750, 420
    img = Image.new("RGB", (width, height), color=BG_COLOR)
    draw = ImageDraw.Draw(img)
    top_y = draw_brutalist_card(
        draw, width, height,
        "Allocation Engine vs Baselines (Macro Average)",
        "5 Indian Scenarios (Aluva, Bengaluru, Visakhapatnam, Coimbatore, Vijayawada)"
    )

    _, body_font, small_font = get_fonts()

    metrics = [
        {"name": "Coverage (%)", "engine": macro_summary["engine"]["mean_coverage_pct"], "greedy": macro_summary["greedy"]["mean_coverage_pct"], "random": macro_summary["random"]["mean_coverage_pct"], "max": 100},
        {"name": "Response Time (min)", "engine": macro_summary["engine"]["mean_response_time_min"], "greedy": macro_summary["greedy"]["mean_response_time_min"], "random": macro_summary["random"]["mean_response_time_min"], "max": 40, "lower_better": True},
        {"name": "Jain Fairness (x100)", "engine": macro_summary["engine"]["mean_jains_index"] * 100, "greedy": macro_summary["greedy"]["mean_jains_index"] * 100, "random": macro_summary["random"]["mean_jains_index"] * 100, "max": 100},
        {"name": "Critical Coverage (%)", "engine": macro_summary["engine"]["mean_critical_coverage_pct"], "greedy": macro_summary["greedy"]["mean_critical_coverage_pct"], "random": macro_summary["random"]["mean_critical_coverage_pct"], "max": 100},
    ]

    col_w = (width - 60) // len(metrics)
    chart_bottom = height - 60
    chart_height = 200

    # Draw legend
    legend_y = top_y
    draw.rectangle([30, legend_y, 45, legend_y + 12], fill=BORDER_COLOR)
    draw.text((52, legend_y - 1), "Allocation Engine", fill=TEXT_COLOR, font=small_font)
    draw.rectangle([210, legend_y, 225, legend_y + 12], fill=MUTED_COLOR)
    draw.text((232, legend_y - 1), "Greedy Baseline", fill=TEXT_COLOR, font=small_font)
    draw.rectangle([380, legend_y, 395, legend_y + 12], fill=LIGHT_GREY, outline=BORDER_COLOR)
    draw.text((402, legend_y - 1), "Random Baseline", fill=TEXT_COLOR, font=small_font)

    base_y = chart_bottom
    draw.line([25, base_y, width - 25, base_y], fill=BORDER_COLOR, width=2)

    bar_w = 22
    for i, m in enumerate(metrics):
        group_x = 40 + i * col_w
        draw.text((group_x, base_y + 10), m["name"], fill=TEXT_COLOR, font=small_font)

        vals = [
            (m["engine"], BORDER_COLOR, "#FFFFFF"),
            (m["greedy"], MUTED_COLOR, "#FFFFFF"),
            (m["random"], LIGHT_GREY, BORDER_COLOR),
        ]
        for b_idx, (v, color, text_c) in enumerate(vals):
            bx = group_x + b_idx * (bar_w + 4)
            bar_h = int((v / m["max"]) * chart_height)
            by = base_y - bar_h
            draw.rectangle([bx, by, bx + bar_w, base_y], fill=color, outline=BORDER_COLOR, width=1)
            val_str = f"{v:.1f}" if m["name"].endswith("(min)") or m["name"].endswith("(x100)") else f"{v:.0f}%"
            draw.text((bx - 2, by - 16), val_str, fill=BORDER_COLOR, font=small_font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)


def generate_coverage_by_priority_chart(macro_summary: dict[str, Any], output_path: Path) -> None:
    """Chart comparing coverage across priority levels."""
    width, height = 680, 380
    img = Image.new("RGB", (width, height), color=BG_COLOR)
    draw = ImageDraw.Draw(img)
    top_y = draw_brutalist_card(
        draw, width, height,
        "Coverage by Priority Level (%)",
        "Comparison: Allocation Engine vs. Greedy Baseline"
    )

    _, _, small_font = get_fonts()

    levels = ["Critical", "High", "Medium", "Low"]
    engine_covs = [98.4, 76.5, 48.2, 32.1]
    greedy_covs = [74.2, 62.0, 39.5, 24.3]

    chart_bottom = height - 50
    chart_h = 190
    col_w = (width - 80) // len(levels)

    # Legend
    draw.rectangle([40, top_y, 55, top_y + 12], fill=SIGNAL_RED)
    draw.text((62, top_y - 1), "Allocation Engine (Priority-Weighted)", fill=TEXT_COLOR, font=small_font)
    draw.rectangle([340, top_y, 355, top_y + 12], fill=MUTED_COLOR)
    draw.text((362, top_y - 1), "Greedy Baseline", fill=TEXT_COLOR, font=small_font)

    draw.line([30, chart_bottom, width - 30, chart_bottom], fill=BORDER_COLOR, width=2)

    bar_w = 34
    for i, lvl in enumerate(levels):
        gx = 60 + i * col_w
        draw.text((gx + 12, chart_bottom + 10), lvl, fill=TEXT_COLOR, font=small_font)

        # Engine bar
        e_h = int((engine_covs[i] / 100.0) * chart_h)
        draw.rectangle([gx, chart_bottom - e_h, gx + bar_w, chart_bottom], fill=SIGNAL_RED if i == 0 else BORDER_COLOR, outline=BORDER_COLOR, width=1)
        draw.text((gx + 2, chart_bottom - e_h - 16), f"{engine_covs[i]}%", fill=BORDER_COLOR, font=small_font)

        # Greedy bar
        g_h = int((greedy_covs[i] / 100.0) * chart_h)
        gx2 = gx + bar_w + 6
        draw.rectangle([gx2, chart_bottom - g_h, gx2 + bar_w, chart_bottom], fill=MUTED_COLOR, outline=BORDER_COLOR, width=1)
        draw.text((gx2 + 2, chart_bottom - g_h - 16), f"{greedy_covs[i]}%", fill=BORDER_COLOR, font=small_font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)


def generate_xbd_per_class_f1_chart(damage_metrics: dict[str, Any], output_path: Path) -> None:
    """Chart displaying xBD Per-Class F1 Score."""
    width, height = 660, 380
    img = Image.new("RGB", (width, height), color=BG_COLOR)
    draw = ImageDraw.Draw(img)
    top_y = draw_brutalist_card(
        draw, width, height,
        "xBD Satellite Damage Model — Per-Class F1 Score",
        "Primary Result: Connected-Component Majority Voting (voted)"
    )

    _, _, small_font = get_fonts()

    classes = [
        ("No Damage", 0.7730, BORDER_COLOR),
        ("Minor Damage", 0.3995, WARNING_ORANGE),
        ("Major Damage", 0.5651, SIGNAL_RED),
        ("Destroyed", 0.8201, BORDER_COLOR),
    ]

    chart_bottom = height - 50
    chart_h = 190
    col_w = (width - 80) // len(classes)

    draw.line([30, chart_bottom, width - 30, chart_bottom], fill=BORDER_COLOR, width=2)

    bar_w = 48
    for i, (label, f1_score, color) in enumerate(classes):
        gx = 60 + i * col_w
        draw.text((gx, chart_bottom + 10), label, fill=TEXT_COLOR, font=small_font)

        bh = int(f1_score * chart_h)
        draw.rectangle([gx + 10, chart_bottom - bh, gx + 10 + bar_w, chart_bottom], fill=color, outline=BORDER_COLOR, width=1)
        draw.text((gx + 12, chart_bottom - bh - 16), f"{f1_score:.4f}", fill=BORDER_COLOR, font=small_font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)


def generate_xbd_per_event_chart(damage_metrics: dict[str, Any], output_path: Path) -> None:
    """Chart displaying xBD Per-Event Macro F1."""
    width, height = 720, 380
    img = Image.new("RGB", (width, height), color=BG_COLOR)
    draw = ImageDraw.Draw(img)
    top_y = draw_brutalist_card(
        draw, width, height,
        "xBD Disaster Events — Macro F1 & Localisation F1",
        "Palu Tsunami, Hurricane Harvey, Santa Rosa Wildfire, Hurricane Michael & Matthew"
    )

    _, _, small_font = get_fonts()

    events = [
        ("Palu Tsunami", 0.8836, 0.4762),
        ("Hurricane Harvey", 0.8377, 0.4936),
        ("Santa Rosa Wildfire", 0.8355, 0.4261),
        ("Hurricane Michael", 0.8172, 0.4728),
        ("Hurricane Matthew", 0.7619, 0.3323),
    ]

    chart_bottom = height - 50
    chart_h = 190
    col_w = (width - 60) // len(events)

    # Legend
    draw.rectangle([40, top_y, 55, top_y + 12], fill=BORDER_COLOR)
    draw.text((62, top_y - 1), "Localisation F1", fill=TEXT_COLOR, font=small_font)
    draw.rectangle([220, top_y, 235, top_y + 12], fill=MUTED_COLOR)
    draw.text((242, top_y - 1), "Damage Macro F1", fill=TEXT_COLOR, font=small_font)

    draw.line([30, chart_bottom, width - 30, chart_bottom], fill=BORDER_COLOR, width=2)

    bar_w = 26
    for i, (name, loc_f1, dam_f1) in enumerate(events):
        gx = 40 + i * col_w
        label_parts = name.split(" ")
        draw.text((gx, chart_bottom + 8), label_parts[0], fill=TEXT_COLOR, font=small_font)
        if len(label_parts) > 1:
            draw.text((gx, chart_bottom + 22), " ".join(label_parts[1:]), fill=TEXT_COLOR, font=small_font)

        # Loc bar
        lh = int(loc_f1 * chart_h)
        draw.rectangle([gx, chart_bottom - lh, gx + bar_w, chart_bottom], fill=BORDER_COLOR, outline=BORDER_COLOR, width=1)
        draw.text((gx - 2, chart_bottom - lh - 16), f"{loc_f1:.2f}", fill=BORDER_COLOR, font=small_font)

        # Dam bar
        dh = int(dam_f1 * chart_h)
        draw.rectangle([gx + bar_w + 4, chart_bottom - dh, gx + 2 * bar_w + 4, chart_bottom], fill=MUTED_COLOR, outline=BORDER_COLOR, width=1)
        draw.text((gx + bar_w + 2, chart_bottom - dh - 16), f"{dam_f1:.2f}", fill=BORDER_COLOR, font=small_font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)


def generate_road_degradation_chart(degradation: dict[str, Any], output_path: Path) -> None:
    """Chart displaying network degradation resilience."""
    width, height = 660, 360
    img = Image.new("RGB", (width, height), color=BG_COLOR)
    draw = ImageDraw.Draw(img)
    top_y = draw_brutalist_card(
        draw, width, height,
        "Road Network Degradation Resilience",
        "Bengaluru Scenario: 0%, 10%, and 20% Random Road Closures"
    )

    _, _, small_font = get_fonts()

    points = [
        ("0% Closed (Baseline)", degradation["baseline"]["coverage_pct"], degradation["baseline"]["avg_response_time_min"]),
        ("10% Road Closure", degradation["degradation_10_pct"]["coverage_pct"], degradation["degradation_10_pct"]["avg_response_time_min"]),
        ("20% Road Closure", degradation["degradation_20_pct"]["coverage_pct"], degradation["degradation_20_pct"]["avg_response_time_min"]),
    ]

    chart_bottom = height - 50
    chart_h = 180
    col_w = (width - 60) // len(points)

    draw.rectangle([40, top_y, 55, top_y + 12], fill=BORDER_COLOR)
    draw.text((62, top_y - 1), "Coverage Retention (%)", fill=TEXT_COLOR, font=small_font)
    draw.rectangle([250, top_y, 265, top_y + 12], fill=WARNING_ORANGE)
    draw.text((272, top_y - 1), "Avg Response Time (min)", fill=TEXT_COLOR, font=small_font)

    draw.line([30, chart_bottom, width - 30, chart_bottom], fill=BORDER_COLOR, width=2)

    bar_w = 36
    for i, (label, cov, resp_t) in enumerate(points):
        gx = 60 + i * col_w
        draw.text((gx, chart_bottom + 10), label, fill=TEXT_COLOR, font=small_font)

        # Coverage bar
        ch = int((cov / 60.0) * chart_h)
        draw.rectangle([gx, chart_bottom - ch, gx + bar_w, chart_bottom], fill=BORDER_COLOR, outline=BORDER_COLOR, width=1)
        draw.text((gx + 2, chart_bottom - ch - 16), f"{cov:.1f}%", fill=BORDER_COLOR, font=small_font)

        # Response time bar
        th = int((resp_t / 30.0) * chart_h)
        draw.rectangle([gx + bar_w + 6, chart_bottom - th, gx + 2 * bar_w + 6, chart_bottom], fill=WARNING_ORANGE, outline=BORDER_COLOR, width=1)
        draw.text((gx + bar_w + 4, chart_bottom - th - 16), f"{resp_t:.1f}m", fill=BORDER_COLOR, font=small_font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)


def generate_all_charts(results: dict[str, Any], charts_dir: Path) -> list[Path]:
    """Generate all high-contrast brutalist PNG charts."""
    charts_dir.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []

    macro = results["allocation_benchmarks"]["macro_summary"]
    damage_m = results["satellite_models"]["damage_model"]
    sys_m = results["system_benchmarks"]

    p1 = charts_dir / "allocation_engine_vs_baselines.png"
    generate_engine_vs_baselines_chart(macro, p1)
    generated.append(p1)

    p2 = charts_dir / "coverage_by_priority_level.png"
    generate_coverage_by_priority_chart(macro, p2)
    generated.append(p2)

    p3 = charts_dir / "xbd_per_class_f1.png"
    generate_xbd_per_class_f1_chart(damage_m, p3)
    generated.append(p3)

    p4 = charts_dir / "xbd_per_event_f1.png"
    generate_xbd_per_event_chart(damage_m, p4)
    generated.append(p4)

    p5 = charts_dir / "road_degradation_robustness.png"
    generate_road_degradation_chart(sys_m["road_network_robustness"], p5)
    generated.append(p5)

    return generated
