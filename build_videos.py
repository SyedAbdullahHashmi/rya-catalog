#!/usr/bin/env python3
"""Build the brand video pages (videos_ryra.html, videos_rstreet.html).

Public grid of reels, one page per brand:
  - video files live in videos/<brand>/ in this repo, served public by Pages
    (Buffer fetches the .mp4 URLs from here — no auth)
  - clicking a card opens the brand's Instagram page in a new tab
  - pages are linked from index.html like normal catalog sections

Data: catalogs/videos_ryra.json / catalogs/videos_rstreet.json
Each entry: {id, title, file, instagram, added, note}
  file = filename inside videos/<brand>/
  instagram = URL the card links to (per-entry, falls back to brand default)
Entries whose file is missing on disk are SKIPPED with a warning, so a
half-uploaded reel never 404s on the page.
"""
import html as H
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CATA_DIR = os.path.join(BASE_DIR, "catalogs")
VID_DIR = os.path.join(BASE_DIR, "videos")
OUT_DIR = os.path.join(BASE_DIR, "html_catalogs")
os.makedirs(OUT_DIR, exist_ok=True)

BRANDS = [
    ("ryra", "RYRA & CO.", "Women's Reels", "https://www.instagram.com/ryraco_"),
    ("rstreet", "RSTREET", "Men's Reels", "https://www.instagram.com/rstreetstore"),
]

# Same palette as build_catalogs.py
BG = "#edd3a8"
TEXT = "#2f2115"
TEXT_MUTED = "#604622"
TEXT_SECONDARY = "#4a3720"
GOLD = "#d5ac55"
GOLD_LIGHT = "#e8c98a"
CARD_BG = "#fdf2de"
BORDER = "#c9b896"
BORDER_LIGHT = "#e0ceaa"
WHITE = "#ffffff"


def esc(s):
    return H.escape(str(s or ""))


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024.0


def video_css():
    return f"""
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
            color: {TEXT};
            background: {BG};
            padding: 0;
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
        }}
        .page {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 32px 40px;
        }}
        .topbar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-top: 16px;
        }}
        .back-link {{
            font-size: 0.75rem;
            font-weight: 600;
            color: {TEXT_SECONDARY};
            text-decoration: none;
            letter-spacing: 0.05em;
        }}
        .back-link:hover {{ color: {GOLD}; }}
        .brand-strip {{
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            padding: 14px 0 14px;
            border-bottom: 1.5px solid {GOLD};
            margin-bottom: 24px;
        }}
        .brand-mark {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .brand-icon {{
            width: 20px;
            height: 20px;
            border: 2px solid {GOLD};
            border-radius: 50%;
            position: relative;
            flex-shrink: 0;
        }}
        .brand-icon::after {{
            content: "";
            position: absolute;
            top: 50%;
            left: 50%;
            width: 7px;
            height: 7px;
            background: {GOLD};
            border-radius: 50%;
            transform: translate(-50%, -50%);
        }}
        .brand-name {{
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.25em;
            text-transform: uppercase;
            color: {TEXT};
        }}
        .section-header {{ margin-bottom: 24px; }}
        .section-title {{
            font-family: Georgia, "Times New Roman", serif;
            font-size: 2rem;
            font-weight: 700;
            color: {TEXT};
            line-height: 1.15;
            margin-bottom: 4px;
        }}
        .section-sub {{
            font-size: 0.75rem;
            font-weight: 600;
            color: {GOLD};
            letter-spacing: 0.12em;
            text-transform: uppercase;
        }}

        .grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
        }}
        .video-card {{
            background: {CARD_BG};
            border: 1px solid {BORDER};
            border-radius: 2px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            text-decoration: none;
            color: inherit;
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }}
        .video-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 18px rgba(94, 66, 25, 0.18);
        }}
        .video-thumb {{
            position: relative;
            width: 100%;
            aspect-ratio: 9 / 16;
            background: {WHITE};
            overflow: hidden;
            border-bottom: 1px solid {BORDER};
        }}
        .video-thumb video {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }}
        .play-overlay {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 52px;
            height: 52px;
            border-radius: 50%;
            background: rgba(47, 33, 21, 0.55);
            display: flex;
            align-items: center;
            justify-content: center;
            pointer-events: none;
            transition: background 0.15s;
        }}
        .video-card:hover .play-overlay {{ background: rgba(213, 172, 85, 0.9); }}
        .play-overlay::after {{
            content: "";
            border-style: solid;
            border-width: 10px 0 10px 16px;
            border-color: transparent transparent transparent {WHITE};
            margin-left: 4px;
        }}
        .card-body {{ padding: 12px 14px 14px; }}
        .card-title {{
            font-family: Georgia, "Times New Roman", serif;
            font-size: 0.95rem;
            color: {TEXT};
            margin-bottom: 3px;
        }}
        .card-meta {{
            font-size: 0.72rem;
            color: {TEXT_SECONDARY};
            letter-spacing: 0.03em;
        }}
        .card-file {{
            font-size: 0.62rem;
            color: {BORDER};
            font-family: monospace;
            margin-top: 6px;
            word-break: break-all;
        }}
        .empty {{
            grid-column: 1 / -1;
            background: {CARD_BG};
            border: 1px dashed {BORDER};
            border-radius: 2px;
            padding: 48px 24px;
            text-align: center;
            color: {TEXT_SECONDARY};
            font-size: 0.9rem;
        }}
        .empty strong {{ font-family: Georgia, serif; font-size: 1.2rem; display: block; margin-bottom: 6px; }}
        .footer {{
            margin-top: 36px;
            padding-top: 14px;
            border-top: 1px solid {BORDER_LIGHT};
            text-align: center;
            font-size: 0.72rem;
            color: {TEXT_MUTED};
        }}
        @media (max-width: 900px) {{
            .grid {{ grid-template-columns: repeat(2, 1fr); }}
        }}
        @media (max-width: 600px) {{
            .page {{ padding: 0 18px 32px; }}
            .section-title {{ font-size: 1.5rem; }}
        }}
    """


def build_one(brand, brand_name, brand_sub, default_ig):
    json_path = os.path.join(CATA_DIR, f"videos_{brand}.json")
    video_dir = os.path.join(VID_DIR, brand)
    output_path = os.path.join(OUT_DIR, f"videos_{brand}.html")

    if not os.path.isfile(json_path):
        print(f"Skip {brand} (missing {json_path})")
        return
    with open(json_path, encoding="utf-8") as f:
        videos = json.load(f)
    if not isinstance(videos, list):
        videos = list(videos.values())

    cards = []
    for v in videos:
        fname = v.get("file", "")
        fpath = os.path.join(video_dir, fname)
        if not os.path.isfile(fpath):
            print(f"  WARN {brand}/{fname}: file missing in {video_dir} — skipped")
            continue
        size = human_size(os.path.getsize(fpath))
        ig = v.get("instagram") or default_ig
        added = esc(v.get("added", ""))
        added_html = f"{added} · " if added else ""
        cards.append(f"""        <a class="video-card" href="{esc(ig)}" target="_blank" rel="noopener">
            <div class="video-thumb">
                <video src="../videos/{esc(brand)}/{esc(fname)}" preload="metadata" muted playsinline></video>
                <div class="play-overlay"></div>
            </div>
            <div class="card-body">
                <div class="card-title">{esc(v.get('title', fname))}</div>
                <div class="card-meta">{added_html}{size} · Instagram ↗</div>
                <div class="card-file">videos/{esc(brand)}/{esc(fname)}</div>
            </div>
        </a>""")

    if cards:
        grid_html = "\n".join(cards)
    else:
        grid_html = """        <div class="empty">
            <strong>Reels coming soon</strong>
            New videos land here as they're rendered.
        </div>"""

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{esc(brand_name)} — Videos</title>
    <style>{video_css()}</style>
</head>
<body>
    <div class="page">
        <div class="topbar">
            <a class="back-link" href="../index.html">&larr; Back to all catalogs</a>
            <a class="back-link" href="{esc(default_ig)}" target="_blank" rel="noopener">Instagram &rarr;</a>
        </div>
        <div class="brand-strip">
            <div class="brand-mark">
                <div class="brand-icon"></div>
                <div class="brand-name">{esc(brand_name)}</div>
            </div>
            <div class="brand-name">{esc(brand_sub)}</div>
        </div>
        <div class="section-header">
            <h1 class="section-title">Videos</h1>
            <div class="section-sub">{len(cards)} reel{"s" if cards and len(cards) != 1 else ""} &middot; tap any reel to open it on Instagram</div>
        </div>
        <div class="grid">
{grid_html}
        </div>
        <div class="footer">{esc(brand_name)} &middot; videos page</div>
    </div>
</body>
</html>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"Built: {output_path}  ({len(cards)} videos)")


def main():
    for brand, name, sub, ig in BRANDS:
        build_one(brand, name, sub, ig)
    print(f"\nAll video pages built into: {OUT_DIR}")


if __name__ == "__main__":
    main()
