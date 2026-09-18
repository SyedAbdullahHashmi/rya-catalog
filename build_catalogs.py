#!/usr/bin/env python3
"""Build all 4 HTML catalogs from the JSON files — RYRA & CO. style.

Matching the RYRA & CO. CATALOGUE - STORES.pdf reference design:
- Warm golden beige background (#edd3a8)
- Deep warm brown text (#2f2115)
- Gold accent lines (#d5ac55)
- Serif product names, sans-serif headers/prices
- Thin product cards on warm ivory (#fdf2de)
- Section headers with gold underline accent
- RYRA & CO. wordmark with gold dot logo mark
"""
import hashlib
import html
import json
import os
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CATA_DIR = os.path.join(BASE_DIR, "catalogs")
IMG_DIR = os.path.join(BASE_DIR, "images")
OUT_DIR = os.path.join(BASE_DIR, "html_catalogs")
os.makedirs(OUT_DIR, exist_ok=True)

CATALOG_FILES = [
    ("mens_jewelry",      "catalog_mens_jewelry.html"),
    ("womens_jewelry",    "catalog_womens_jewelry.html"),
    ("womens_clutches",   "catalog_womens_clutches.html"),
    ("mens_accessories",  "catalog_mens_accessories.html"),
]

# RYRA & CO. PDF-reference colour palette
BG             = "#edd3a8"   # warm golden beige background
TEXT           = "#2f2115"   # deep warm brown — primary text
TEXT_MUTED     = "#604622"   # muted brown — product names (serif)
TEXT_SECONDARY = "#4a3720"   # secondary dark brown — prices, section sub
GOLD           = "#d5ac55"   # gold accent — lines, logo dot, hover
GOLD_LIGHT     = "#e8c98a"   # lighter gold — subtle accents
CARD_BG        = "#fdf2de"   # warm ivory — product card background
BORDER         = "#c9b896"   # warm tan — card borders, dividers
BORDER_LIGHT  = "#e0ceaa"   # lighter tan — subtle borders
WHITE          = "#ffffff"
SECTION_BG    = "#f5e6c8"   # slightly lighter beige for section header area


def ryra_css():
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

        /* ---- top brand strip (RYRA & CO. wordmark) ---- */
        .brand-strip {{
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            padding: 18px 0 14px;
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
        .brand-contact {{
            font-size: 0.7rem;
            color: {TEXT_SECONDARY};
            text-align: right;
            line-height: 1.4;
        }}

        /* ---- section header ---- */
        .section-header {{
            margin-bottom: 24px;
            padding-bottom: 16px;
        }}
        .section-title {{
            font-family: Georgia, "Times New Roman", serif;
            font-size: 2rem;
            font-weight: 700;
            color: {TEXT};
            letter-spacing: -0.01em;
            margin-bottom: 4px;
            line-height: 1.15;
        }}
        .section-sub {{
            font-size: 0.75rem;
            font-weight: 600;
            color: {GOLD};
            letter-spacing: 0.12em;
            text-transform: uppercase;
        }}

        /* ---- category bar ---- */
        .category-bar {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 1px solid {BORDER_LIGHT};
        }}
        .category-btn {{
            font-size: 0.75rem;
            font-weight: 600;
            letter-spacing: 0.03em;
            text-transform: uppercase;
            color: {TEXT};
            background: {CARD_BG};
            border: 1px solid {BORDER};
            border-radius: 20px;
            padding: 6px 14px;
            cursor: pointer;
            transition: all 0.15s ease;
            text-decoration: none;
            display: inline-block;
        }}
        .category-btn:hover {{
            background: {TEXT};
            color: {CARD_BG};
            border-color: {TEXT};
        }}
        .category-btn.active {{
            background: {TEXT};
            color: {CARD_BG};
            border-color: {TEXT};
        }}
        .category-count {{
            font-weight: 400;
            opacity: 0.65;
            margin-left: 4px;
            font-size: 0.65rem;
        }}

        /* ---- product grid ---- */
        .grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 18px 20px;
        }}

        /* ---- product card ---- */
        .product-card {{
            background: {CARD_BG};
            border: 1px solid {BORDER};
            border-radius: 1px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            break-inside: avoid;
            page-break-inside: avoid;
            scroll-margin-top: 20px;
        }}
        .card-image {{
            background: {WHITE};
            width: 100%;
            height: 320px;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            border-bottom: 1px solid {BORDER};
        }}
        .product-image {{
            width: 100%;
            height: 320px;
            object-fit: cover;
            display: block;
        }}
        .product-image-placeholder {{
            font-size: 2.2rem;
            color: {BORDER};
            font-weight: 300;
        }}
        .product-image-missing {{
            font-size: 0.7rem;
            color: {BORDER};
            padding: 10px;
            text-align: center;
        }}
        .card-body {{
            padding: 12px 14px 16px;
            flex: 1;
        }}
        .card-category {{
            font-size: 0.65rem;
            font-weight: 600;
            color: {TEXT_SECONDARY};
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 3px;
        }}
        .card-name {{
            font-family: Georgia, "Times New Roman", serif;
            font-size: 0.92rem;
            font-weight: 400;
            color: {TEXT_MUTED};
            margin-bottom: 5px;
            line-height: 1.35;
            white-space: pre-wrap;
            word-break: break-word;
        }}
        .card-price {{
            font-size: 0.88rem;
            font-weight: 700;
            color: {TEXT};
            letter-spacing: 0.02em;
            white-space: nowrap;
        }}

        .empty-state {{
            grid-column: 1 / -1;
            text-align: center;
            padding: 56px 20px;
            color: {TEXT_SECONDARY};
            font-size: 0.85rem;
        }}

        .catalog-footer {{
            margin-top: 36px;
            padding-top: 14px;
            border-top: 1px solid {BORDER};
            font-size: 0.68rem;
            color: {TEXT_SECONDARY};
            text-align: center;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }}

        @media (max-width: 960px) {{
            .grid {{ grid-template-columns: repeat(2, 1fr); gap: 14px; }}
            .card-image {{ height: 260px; }}
            .product-image {{ height: 260px; }}
            .page {{ padding: 0 20px 32px; }}
            .section-title {{ font-size: 1.6rem; }}
        }}
        @media (max-width: 560px) {{
            .grid {{ grid-template-columns: 1fr; gap: 12px; }}
            .card-image {{ height: 280px; }}
            .product-image {{ height: 280px; }}
            .brand-strip {{ flex-direction: column; align-items: flex-start; gap: 6px; }}
            .brand-contact {{ text-align: left; }}
            .section-title {{ font-size: 1.3rem; }}
            .page {{ padding: 0 14px 24px; }}
        }}
        @media print {{
            body {{ background: {WHITE}; }}
            .page {{ max-width: 100%; padding: 20px; }}
            .product-card {{
                box-shadow: none;
                border: 1px solid #bbb;
                break-inside: avoid;
                page-break-inside: avoid;
            }}
            .card-image {{ border-bottom: 1px solid #bbb; }}
            .brand-strip {{ border-bottom: 1px solid #bbb; }}
            .catalog-footer {{ border-top: 1px solid #bbb; }}
            .category-bar {{ display: none; }}
            .section-title {{ font-size: 1.4rem; }}
            .section-sub {{ color: {TEXT}; }}
        }}
    """


def build_one(catalog_name, json_path, output_path):
    with open(json_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    catalog_title = catalog.get("name", catalog_name.replace("_", " ").title())
    products = catalog.get("products", [])

    # Build category list: preserve order of first appearance
    seen = set()
    categories = []
    for p in products:
        cat = (p.get("category") or "Other").strip() or "Other"
        if cat not in seen:
            seen.add(cat)
            categories.append(cat)

    out_img_dir = os.path.join(OUT_DIR, "images")
    os.makedirs(out_img_dir, exist_ok=True)

    cards = []
    for i, p in enumerate(products, 1):
        image_src = (p.get("image") or "").strip()
        name = p.get("name", "").strip()
        price = p.get("price", "").strip()
        category = (p.get("category") or "Other").strip() or "Other"

        if image_src.startswith("http"):
            img_tag = f'<img class="product-image" src="{html.escape(image_src)}" alt="{html.escape(name)}">'
        elif image_src:
            ext = os.path.splitext(image_src)[1].lower() or ".jpg"
            local_name = f"{catalog_name}_{i}_{hashlib.sha1(image_src.encode()).hexdigest()[:6]}{ext}"
            src_path = os.path.join(BASE_DIR, image_src)
            if os.path.isfile(src_path):
                dst = os.path.join(out_img_dir, local_name)
                if not os.path.exists(dst):
                    shutil.copy2(src_path, dst)
                img_tag = f'<img class="product-image" src="images/{html.escape(local_name)}" alt="{html.escape(name)}">'
            else:
                img_tag = f'<div class="product-image-missing" title="Image not found: {html.escape(image_src)}">Image missing</div>'
        else:
            img_tag = '<div class="product-image-placeholder">+</div>'

        cards.append(f"""
        <div class="product-card" data-category="{html.escape(category.lower().replace(' ', '-'))}">
            <div class="card-image">{img_tag}</div>
            <div class="card-body">
                <div class="card-category">{html.escape(category)}</div>
                <div class="card-name">{html.escape(name)}</div>
                <div class="card-price">{html.escape(price)}</div>
            </div>
        </div>
        """)

    cards_html = "\n".join(cards) if cards else (
        '<div class="empty-state">No products yet.</div>'
    )

    # Build category buttons with counts
    cat_buttons = []
    for cat in categories:
        count = sum(1 for p in products if (p.get("category") or "Other").strip() == cat)
        cat_buttons.append(
            f'<a class="category-btn" href="#category-{html.escape(cat.lower().replace(" ", "-"))}">'
            f'{html.escape(cat)}<span class="category-count">{count}</span></a>'
        )
    cat_buttons_html = "\n            ".join(cat_buttons) if cat_buttons else (
        '<span class="category-btn" style="opacity:0.5;cursor:default;background:transparent;border-color:{BORDER};">No categories</span>'
    )

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{html.escape(catalog_title)} — RYRA &amp; CO. Catalogue</title>
    <style>
{ryra_css()}
    </style>
</head>
<body>
    <div class="page">
        <div class="brand-strip">
            <div class="brand-mark">
                <span class="brand-icon" aria-hidden="true"></span>
                <span class="brand-name">RYRA &amp; CO.</span>
            </div>
            <div class="brand-contact">
                www.ryranco.com<br>
                @ryraco_
            </div>
        </div>

        <div class="section-header">
            <div class="section-title">{html.escape(catalog_title)}</div>
            <div class="section-sub">Catalog</div>
        </div>

        <div class="category-bar" id="category-bar">
            {cat_buttons_html}
        </div>

        <div class="grid" id="product-grid">
            {cards_html}
        </div>

        <footer class="catalog-footer">
            {html.escape(catalog_title)} — RYRA &amp; CO. Catalogue
        </footer>
    </div>

    <script>
    (function() {{
        var bar = document.getElementById('category-bar');
        var grid = document.getElementById('product-grid');
        if (!bar || !grid) return;

        var allCards = grid.querySelectorAll('.product-card');
        var btns = bar.querySelectorAll('.category-btn');
        var activeCat = null;

        btns.forEach(function(btn) {{
            btn.addEventListener('click', function(e) {{
                e.preventDefault();
                var target = btn.getAttribute('href');
                if (!target) return;
                var cat = target.replace('#category-', '').replace(/-/g, ' ');

                if (activeCat === cat) {{
                    activeCat = null;
                    allCards.forEach(function(c) {{ c.style.display = ''; }});
                    btns.forEach(function(b) {{ b.classList.remove('active'); }});
                    return;
                }}

                activeCat = cat;
                allCards.forEach(function(c) {{
                    var cCat = (c.getAttribute('data-category') || '').replace(/-/g, ' ');
                    c.style.display = (cCat === cat) ? '' : 'none';
                }});
                btns.forEach(function(b) {{ b.classList.remove('active'); }});
                btn.classList.add('active');
            }});
        }});
    }})();
    </script>
</body>
</html>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"Built: {output_path}  ({len(products)} products, {len(categories)} categories)")


def main():
    for catalog_name, html_name in CATALOG_FILES:
        json_path = os.path.join(CATA_DIR, f"{catalog_name}.json")
        if not os.path.isfile(json_path):
            print(f"Skip (missing {json_path})")
            continue
        output_path = os.path.join(OUT_DIR, html_name)
        build_one(catalog_name, json_path, output_path)
    print(f"\nAll catalogs built into: {OUT_DIR}")


if __name__ == "__main__":
    main()
