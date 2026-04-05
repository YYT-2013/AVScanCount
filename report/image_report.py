from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _load_font(size: int, language: str) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    cn_candidates = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
    ]
    en_candidates = ["arial.ttf", "C:/Windows/Fonts/segoeui.ttf"]
    candidates = cn_candidates + en_candidates if language == "zh" else en_candidates + cn_candidates
    for font_path in candidates:
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _draw_vendor_icon(img: Image.Image, icon_path: Path | None) -> None:
    if not icon_path or not icon_path.exists():
        return
    try:
        icon = Image.open(icon_path).convert("RGBA")
        icon.thumbnail((92, 92))
        x = img.width - icon.width - 16
        y = 9
        img.alpha_composite(icon, (x, y))
    except Exception:
        pass


def generate_png_report(
    output_path: Path,
    antivirus_name: str,
    total: int,
    removed: int,
    remaining: int,
    removed_rate: float,
    language: str = "zh",
    icon_path: Path | None = None,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 960, 540
    img = Image.new("RGBA", (width, height), color=(245, 248, 252, 255))
    draw = ImageDraw.Draw(img)

    title_font = _load_font(42, language)
    body_font = _load_font(28, language)

    if language == "zh":
        title = "杀毒软件查杀报告"
        rows = [
            f"杀毒软件: {antivirus_name or '未填写'}",
            f"样本总数: {total}",
            f"查杀数量: {removed}",
            f"剩余数量: {remaining}",
            f"查杀率: {removed_rate:.2f}%",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ]
    else:
        title = "AV Scan Compare Report"
        rows = [
            f"Antivirus: {antivirus_name or 'N/A'}",
            f"Sample Total: {total}",
            f"Removed: {removed}",
            f"Remaining: {remaining}",
            f"Removed Rate: {removed_rate:.2f}%",
            f"Generated At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ]

    draw.rectangle((0, 0, width, 110), fill=(19, 67, 117))
    draw.text((32, 32), title, fill=(255, 255, 255), font=title_font)
    _draw_vendor_icon(img, icon_path)

    y = 145
    line_height = 50
    for row in rows:
        draw.text((50, y), row, fill=(32, 45, 58), font=body_font)
        y += line_height

    bar_left, bar_top, bar_right, bar_bottom = 50, 460, 910, 500
    draw.rectangle((bar_left, bar_top, bar_right, bar_bottom), fill=(218, 226, 235))
    if total > 0:
        removed_width = int((bar_right - bar_left) * (removed / total))
        draw.rectangle((bar_left, bar_top, bar_left + removed_width, bar_bottom), fill=(35, 154, 92))

    img.convert("RGB").save(output_path, format="PNG")
    return output_path
