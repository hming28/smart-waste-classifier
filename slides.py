"""
Presentation slide deck for the Smart Waste AI Streamlit app.

Renders a self-contained interactive deck inside a single HTML component, so
navigation (arrow keys, click zones, progress dots, fullscreen) happens entirely
in the browser. Nothing here triggers a Streamlit rerun, which means the deck
never jumps back to slide 1 while you're presenting.

Usage in app.py:

    from slides import render_slides
    ...
    tab_home, tab_compare, tab_about, tab_slides = st.tabs(
        ["🏠 Home", "📊 Compare", "ℹ️ About", "🎤 Slides"]
    )
    ...
    with tab_slides:
        render_slides()

To change the look, set ACTIVE_THEME below to any key in THEMES.
To edit content, edit the SLIDES list.
"""

import base64
import os

import streamlit as st
import streamlit.components.v1 as components

# Same folder the Compare tab reads its exported Colab charts from.
FIGURES_DIR = "figures"

# Height of the deck component in pixels. Raise this if your slides get taller.
DECK_HEIGHT = 720


# ─────────────────────────────────────────────────────────────────────────────
# Themes
# ─────────────────────────────────────────────────────────────────────────────
# The four bin colours are the same ones RECYCLE_INFO uses in app.py, so the
# deck, the app UI and the physical bin colours all agree. Each slide picks one
# of them as its accent, which is what makes the deck read as "recycling"
# rather than just "green".
BIN_COLORS = {
    "glass": "#2ecc71",    # green bin
    "metal": "#3498db",    # blue bin
    "paper": "#9b59b6",    # purple bin
    "plastic": "#f39c12",  # yellow/amber bin
}

THEMES = {
    # Default. Dark slate base so the four bin colours stay legible and loud.
    "recycle": {
        "bg": "linear-gradient(155deg, #14231f 0%, #10201c 40%, #131d26 100%)",
        "text": "#eef4f0",
        "muted": "#93aaa1",
        "strong": "#ffffff",
        "surface": "rgba(255, 255, 255, .055)",
        "border": "rgba(255, 255, 255, .10)",
        "watermark": "rgba(255, 255, 255, .028)",
        "img_bg": "#ffffff",
    },
    # Light alternative — better on a washed-out projector or a bright room.
    "recycle_light": {
        "bg": "linear-gradient(155deg, #f7faf8 0%, #eef4f0 55%, #e9f0f4 100%)",
        "text": "#1d2b26",
        "muted": "#5d7169",
        "strong": "#0f1a16",
        "surface": "rgba(0, 0, 0, .035)",
        "border": "rgba(0, 0, 0, .09)",
        "watermark": "rgba(0, 0, 0, .030)",
        "img_bg": "#ffffff",
    },
    # Cooler, more "engineering report" feel; same accent colours.
    "midnight": {
        "bg": "linear-gradient(155deg, #0e1626 0%, #111a2b 45%, #0d1a22 100%)",
        "text": "#e8eef7",
        "muted": "#8fa3bd",
        "strong": "#ffffff",
        "surface": "rgba(255, 255, 255, .05)",
        "border": "rgba(255, 255, 255, .10)",
        "watermark": "rgba(255, 255, 255, .026)",
        "img_bg": "#ffffff",
    },
}

ACTIVE_THEME = "recycle"


# ─────────────────────────────────────────────────────────────────────────────
# Inline illustrations
# ─────────────────────────────────────────────────────────────────────────────
# Drawn as SVG rather than loaded as photos so the deck stays self-contained —
# no extra files to commit, nothing to break if figures/ is missing.

def _bin_svg(x, color, label, lid_open=False):
    """One wheelie-bin shape at horizontal offset x."""
    lid_y = 26 if not lid_open else 20
    return f"""
      <g transform="translate({x},0)">
        <rect x="6" y="{lid_y + 12}" width="68" height="76" rx="7" fill="{color}" opacity=".92"/>
        <rect x="0" y="{lid_y}" width="80" height="14" rx="6" fill="{color}"/>
        <rect x="33" y="{lid_y - 6}" width="14" height="8" rx="3" fill="{color}"/>
        <line x1="26" y1="{lid_y + 24}" x2="26" y2="{lid_y + 78}" stroke="rgba(0,0,0,.18)" stroke-width="3"/>
        <line x1="54" y1="{lid_y + 24}" x2="54" y2="{lid_y + 78}" stroke="rgba(0,0,0,.18)" stroke-width="3"/>
        <text x="40" y="{lid_y + 104}" text-anchor="middle" font-size="13"
              fill="currentColor" opacity=".75">{label}</text>
      </g>
    """


SORTING_COMPARISON_SVG = f"""
<svg viewBox="0 0 900 210" xmlns="http://www.w3.org/2000/svg" class="illus">
  <!-- LEFT: everything in one bin -->
  <text x="20" y="18" font-size="14" font-weight="700" fill="#e74c3c">&#10007; &nbsp;Without classification</text>
  <g transform="translate(60,26)" color="currentColor">
    {_bin_svg(0, "#7f8c8d", "One mixed bin", lid_open=True)}
    <circle cx="18" cy="14" r="7" fill="{BIN_COLORS['glass']}"/>
    <rect x="32" y="6" width="13" height="13" rx="2" fill="{BIN_COLORS['plastic']}"/>
    <circle cx="58" cy="12" r="6" fill="{BIN_COLORS['metal']}"/>
    <rect x="44" y="18" width="12" height="9" rx="2" fill="{BIN_COLORS['paper']}"/>
  </g>
  <text x="52" y="196" font-size="12.5" fill="#e74c3c" opacity=".9">
    Recyclables get contaminated &#8594; landfill
  </text>

  <line x1="330" y1="34" x2="330" y2="180" stroke="currentColor" stroke-opacity=".16" stroke-width="1.5"/>

  <!-- RIGHT: sorted into four -->
  <text x="380" y="18" font-size="14" font-weight="700" fill="#2ecc71">&#10003; &nbsp;With AI classification</text>
  <g transform="translate(380,26)" color="currentColor">
    {_bin_svg(0, BIN_COLORS['glass'], "Glass")}
    {_bin_svg(115, BIN_COLORS['metal'], "Metal")}
    {_bin_svg(230, BIN_COLORS['paper'], "Paper")}
    {_bin_svg(345, BIN_COLORS['plastic'], "Plastic")}
  </g>
  <text x="380" y="196" font-size="12.5" fill="#2ecc71" opacity=".9">
    Clean streams &#8594; actually recycled
  </text>
</svg>
"""


IOT_UPGRADE_SVG = f"""
<svg viewBox="0 0 880 132" xmlns="http://www.w3.org/2000/svg" class="illus">
  <!-- BEFORE -->
  <rect x="4" y="14" width="330" height="104" rx="12"
        fill="currentColor" fill-opacity=".05" stroke="currentColor" stroke-opacity=".16"/>
  <text x="24" y="42" font-size="12" font-weight="700" fill="currentColor" opacity=".55"
        letter-spacing="1.6">PREVIOUS IoT PROJECT</text>
  <text x="24" y="70" font-size="17" font-weight="700" fill="currentColor">Wet / Dry waste bin</text>
  <text x="24" y="94" font-size="13" fill="currentColor" opacity=".65">2 categories &#183; no camera</text>
  <text x="24" y="112" font-size="13" fill="currentColor" opacity=".65">Bin decides by hardware</text>

  <!-- ARROW -->
  <line x1="352" y1="66" x2="510" y2="66" stroke="{BIN_COLORS['glass']}" stroke-width="2.5"/>
  <polygon points="510,60 524,66 510,72" fill="{BIN_COLORS['glass']}"/>
  <text x="368" y="52" font-size="12.5" font-weight="700" fill="{BIN_COLORS['glass']}">
    give it eyes
  </text>

  <!-- AFTER -->
  <rect x="540" y="14" width="336" height="104" rx="12"
        fill="{BIN_COLORS['glass']}" fill-opacity=".10"
        stroke="{BIN_COLORS['glass']}" stroke-opacity=".45"/>
  <text x="560" y="42" font-size="12" font-weight="700" fill="{BIN_COLORS['glass']}"
        letter-spacing="1.6">THIS PROJECT</text>
  <text x="560" y="70" font-size="17" font-weight="700" fill="currentColor">Computer vision classifier</text>
  <text x="560" y="94" font-size="13" fill="currentColor" opacity=".75">4 categories &#183; camera input</text>
  <text x="560" y="112" font-size="13" fill="currentColor" opacity=".75">Bin decides by what it sees</text>
</svg>
"""


MODEL_TIMELINE_SVG = f"""
<svg viewBox="0 0 900 172" xmlns="http://www.w3.org/2000/svg" class="illus">
  <line x1="40" y1="96" x2="860" y2="96" stroke="currentColor" stroke-opacity=".18" stroke-width="2"/>

  <g>
    <circle cx="90" cy="96" r="9" fill="{BIN_COLORS['glass']}"/>
    <text x="90" y="76" text-anchor="middle" font-size="13" font-weight="700" fill="currentColor">CNN</text>
    <text x="90" y="122" text-anchor="middle" font-size="12" fill="currentColor" opacity=".6">1998 &#8594;</text>
    <text x="90" y="140" text-anchor="middle" font-size="11" fill="currentColor" opacity=".5">from scratch</text>
  </g>
  <g>
    <circle cx="280" cy="96" r="9" fill="{BIN_COLORS['metal']}"/>
    <text x="280" y="76" text-anchor="middle" font-size="13" font-weight="700" fill="currentColor">ResNet50</text>
    <text x="280" y="122" text-anchor="middle" font-size="12" fill="currentColor" opacity=".6">2015</text>
    <text x="280" y="140" text-anchor="middle" font-size="11" fill="currentColor" opacity=".5">Microsoft</text>
  </g>
  <g>
    <circle cx="470" cy="96" r="9" fill="{BIN_COLORS['paper']}"/>
    <text x="470" y="76" text-anchor="middle" font-size="13" font-weight="700" fill="currentColor">MobileNetV2</text>
    <text x="470" y="122" text-anchor="middle" font-size="12" fill="currentColor" opacity=".6">2018</text>
    <text x="470" y="140" text-anchor="middle" font-size="11" fill="currentColor" opacity=".5">Google &#183; built for phones</text>
  </g>
  <g>
    <circle cx="660" cy="96" r="9" fill="{BIN_COLORS['plastic']}"/>
    <text x="660" y="76" text-anchor="middle" font-size="13" font-weight="700" fill="currentColor">CLIP</text>
    <text x="660" y="122" text-anchor="middle" font-size="12" fill="currentColor" opacity=".6">2021</text>
    <text x="660" y="140" text-anchor="middle" font-size="11" fill="currentColor" opacity=".5">OpenAI &#183; learned from the web</text>
  </g>
  <g>
    <circle cx="840" cy="96" r="12" fill="none" stroke="{BIN_COLORS['glass']}" stroke-width="3"/>
    <circle cx="840" cy="96" r="5" fill="{BIN_COLORS['glass']}"/>
    <text x="840" y="70" text-anchor="middle" font-size="13" font-weight="700"
          fill="{BIN_COLORS['glass']}">Fusion</text>
    <text x="840" y="122" text-anchor="middle" font-size="12"
          fill="{BIN_COLORS['glass']}" opacity=".85">ours</text>
    <text x="840" y="140" text-anchor="middle" font-size="11" fill="currentColor" opacity=".5">ResNet50 + CLIP</text>
  </g>
</svg>
"""


# ─────────────────────────────────────────────────────────────────────────────
# Slide content
# ─────────────────────────────────────────────────────────────────────────────
# Each slide is a dict:
#   "title"   — heading
#   "kicker"  — optional small section label above the title
#   "accent"  — which bin colour this slide uses (glass/metal/paper/plastic)
#   "body"    — HTML content
#   "figure"  — optional PNG filename inside FIGURES_DIR, embedded as base64
#   "layout"  — optional; "title" for the big centred cover slide

SLIDES = [
    {
        "layout": "title",
        "accent": "glass",
        "title": "Smart Waste AI",
        "kicker": "BMCS2074 Artificial Intelligence &#183; 202605 Session",
        "body": """
            <p class="lead">AI-Based Smart Waste Classification Using Computer Vision</p>
            <div class="chips chips-center">
              <span class="chip chip-glass">Glass</span>
              <span class="chip chip-metal">Metal</span>
              <span class="chip chip-paper">Paper</span>
              <span class="chip chip-plastic">Plastic</span>
            </div>
            <p class="team">Lee Hao Ming &nbsp;&#183;&nbsp; Goh Jian Hao &nbsp;&#183;&nbsp; Kyra Aerin Leong</p>
        """,
    },
    {
        "kicker": "Introduction",
        "accent": "plastic",
        "title": "The Problem",
        "body": """
            <p class="note">Recycling only works if waste is sorted correctly &mdash; and today that
            sorting depends on manual identification and public knowledge.</p>
        """
        + SORTING_COMPARISON_SVG
        + """
            <div class="callout">
              One wrong item can contaminate a whole stream. The bin on the left doesn't know
              what's in it &mdash; so everything in it gets treated as landfill.
            </div>
        """,
    },
    {
        "kicker": "Introduction",
        "accent": "glass",
        "title": "Where This Came From",
        "body": IOT_UPGRADE_SVG
        + """
            <ul>
              <li>Our previous IoT project was a <b>wet / dry waste bin</b> &mdash; two categories,
                  decided by hardware, with no idea what the item actually was.</li>
              <li>This project is the <b>upgrade</b>: give the system <b>eyes</b>. A camera and a
                  trained model replace the guesswork.</li>
              <li>That jump also lets us go from <b>2 categories to 4</b> &mdash; the recyclable
                  streams that actually matter at the bin.</li>
            </ul>
        """,
    },
    {
        "kicker": "Introduction",
        "accent": "metal",
        "title": "Objectives",
        "body": """
            <ul>
              <li>Develop an AI-based waste classification system for <b>4 recyclable categories</b>.</li>
              <li>Preprocess the dataset &mdash; resizing, normalization, augmentation.</li>
              <li>Implement and compare <b>multiple deep learning approaches</b> under one common experiment.</li>
              <li>Evaluate using Accuracy, Precision, Recall and F1-score.</li>
              <li>Propose and evaluate a <b>feature-level fusion</b> approach combining task-specific
                  CNN features with general-purpose CLIP features.</li>
            </ul>
        """,
    },
    {
        "kicker": "Methodology",
        "accent": "paper",
        "title": "Dataset",
        "body": """
            <ul>
              <li>Combined <b>two public Kaggle datasets</b> (Garbage Classification + Garbage
                  Classification 12-Classes) for more images and more visual variation.</li>
              <li>Kept only the 4 recyclable categories, and removed exact duplicates across the merge.</li>
            </ul>
            <p class="note">Each class is colour-coded to its recycling bin &mdash; the same colours
            the app uses when it gives disposal guidance:</p>
            <div class="bins">
              <div class="bin bin-glass"><span class="bin-icon">&#127870;</span><span class="bin-name">Glass</span><span class="bin-where">Green bin</span></div>
              <div class="bin bin-metal"><span class="bin-icon">&#129387;</span><span class="bin-name">Metal</span><span class="bin-where">Metal recycling</span></div>
              <div class="bin bin-paper"><span class="bin-icon">&#128196;</span><span class="bin-name">Paper</span><span class="bin-where">Blue bin</span></div>
              <div class="bin bin-plastic"><span class="bin-icon">&#129508;</span><span class="bin-name">Plastic</span><span class="bin-where">Yellow bin</span></div>
            </div>
            <p class="note">Stratified 70 / 15 / 15 split, fixed once as CSV files and reused by every model:</p>
            <div class="stats">
              <div class="stat"><span class="stat-num">3,940</span><span class="stat-label">Training</span></div>
              <div class="stat"><span class="stat-num">844</span><span class="stat-label">Validation</span></div>
              <div class="stat"><span class="stat-num">845</span><span class="stat-label">Test</span></div>
            </div>
        """,
    },
    {
        "kicker": "Methodology",
        "accent": "metal",
        "title": "Five Approaches, One Test Set",
        "body": """
            <p class="note">These aren't five random choices &mdash; they're five eras of computer
            vision, put against each other on the same 845 images.</p>
        """
        + MODEL_TIMELINE_SVG
        + """
            <ul>
              <li><b>CNN</b> &mdash; the classic approach, trained from scratch on our data only. Our baseline.</li>
              <li><b>ResNet50 &amp; MobileNetV2</b> &mdash; pretrained on millions of images, then
                  fine-tuned on ours. One built for accuracy, one built for phones.</li>
              <li><b>CLIP</b> &mdash; learned from image&ndash;text pairs across the web, so it carries
                  general knowledge no waste dataset could teach.</li>
              <li><b>Feature Fusion</b> &mdash; our proposal: combine ResNet50's task-specific features
                  with CLIP's general ones, and see whether two views beat one.</li>
            </ul>
        """,
    },
    {
        "kicker": "Results",
        "accent": "glass",
        "title": "Overall Test Accuracy",
        "body": """
            <p class="note">Every number comes from evaluating each model's <i>actual deployed file</i>
            on the shared 845-image test set.</p>
        """,
        "figure": "fig1_overall_accuracy.png",
    },
    {
        "kicker": "Results",
        "accent": "plastic",
        "title": "Where Each Model Struggles",
        "body": """
            <p class="note">The diagonal is correct predictions &mdash; everything off it is a specific
            error mode, which tells us far more than a single accuracy number.</p>
        """,
        "figure": "fig3_confusion_matrices.png",
    },
    {
        "kicker": "Results",
        "accent": "paper",
        "title": "Does CLIP Verify Actually Help?",
        "body": """
            <ul>
              <li>CLIP Verify re-checks predictions the base model isn't confident about (below 90%).</li>
              <li>On this benchmark test set it did <b>not</b> improve accuracy for any of the three models.</li>
              <li>Kept in the app as an experiment for real-world photos &mdash; not claimed as an accuracy win.</li>
            </ul>
        """,
        "figure": "fig8_clip_verify_effect.png",
    },
    {
        "kicker": "Conclusion",
        "accent": "glass",
        "title": "Achievements",
        "body": """
            <ul>
              <li>Built a working end-to-end prototype, deployed on Streamlit Community Cloud.</li>
              <li>Implemented and fairly compared <b>5 approaches</b> on one shared test set.</li>
              <li>Evaluated with accuracy, precision, recall, F1 and confusion-matrix error analysis.</li>
              <li>Fusion showed <b>complementary</b> behaviour &mdash; slightly stronger on Paper,
                  weaker on Glass / Metal / Plastic than ResNet50 alone.</li>
            </ul>
            <div class="stats">
              <div class="stat"><span class="stat-num">97.16%</span><span class="stat-label">ResNet50 &mdash; best</span></div>
              <div class="stat"><span class="stat-num">96.80%</span><span class="stat-label">Feature Fusion</span></div>
              <div class="stat"><span class="stat-num">92.66%</span><span class="stat-label">MobileNetV2</span></div>
            </div>
        """,
    },
    {
        "kicker": "Conclusion",
        "accent": "plastic",
        "title": "Limitations",
        "body": """
            <ul>
              <li>The 90% CLIP-verify threshold was a design choice, <b>not tuned</b> on the validation set.</li>
              <li>845 test images &mdash; close results (the 0.36-point ResNet50 vs. Fusion gap) should be read with that in mind.</li>
              <li>Only 4 categories under controlled conditions; real waste is dirtier, overlapping and mixed.</li>
              <li>Classification runs on a <b>single snapshot</b>, not a continuous video stream.</li>
              <li>CLIP-verify results were measured on the <i>same</i> test set as the base models, not a separate holdout.</li>
              <li>Random seed fixed only for ResNet50 and Fusion &mdash; not CNN, MobileNetV2 or CLIP Linear Probe.</li>
            </ul>
        """,
    },
    {
        "kicker": "Conclusion",
        "accent": "metal",
        "title": "Future Work",
        "body": """
            <ul>
              <li>Tune the confidence threshold empirically on the validation set.</li>
              <li>Expand the dataset &mdash; more images, more categories, more real-world lighting and backgrounds.</li>
              <li>Re-test CLIP Verify on a genuinely independent holdout set.</li>
              <li>Standardise random seeds across all five models, and report mean &plusmn; std over repeated runs.</li>
              <li>Close the loop back to IoT &mdash; put this model on the bin itself, classifying
                  items continuously instead of one snapshot at a time.</li>
              <li>Compare against other fusion strategies &mdash; late fusion, attention-based fusion.</li>
            </ul>
        """,
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Rendering
# ─────────────────────────────────────────────────────────────────────────────

def _figure_data_uri(filename):
    """Read a PNG from FIGURES_DIR and return it as a base64 data URI.

    The deck renders inside a sandboxed iframe, which cannot read local files by
    path, so images have to be inlined. Returns None if the file isn't there,
    and the slide falls back to a placeholder instead of breaking the deck."""
    path = os.path.join(FIGURES_DIR, filename)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("ascii")
        return "data:image/png;base64," + encoded
    except OSError:
        return None


def _build_slide_html(slide, index):
    """Render one slide dict into its <section> markup."""
    accent = BIN_COLORS.get(slide.get("accent", "glass"), BIN_COLORS["glass"])

    classes = "slide"
    if slide.get("layout") == "title":
        classes += " slide-title"
    if index == 0:
        classes += " active"

    parts = [
        '<section class="' + classes + '" data-index="' + str(index)
        + '" style="--accent:' + accent + '">'
    ]
    parts.append('<div class="slide-inner">')

    if slide.get("kicker"):
        parts.append('<div class="kicker"><span class="kicker-dot"></span>' + slide["kicker"] + "</div>")
    parts.append("<h1>" + slide["title"] + "</h1>")
    parts.append('<div class="content">' + slide.get("body", "") + "</div>")

    if slide.get("figure"):
        uri = _figure_data_uri(slide["figure"])
        if uri:
            parts.append('<div class="figure"><img src="' + uri + '" alt="' + slide["figure"] + '"></div>')
        else:
            parts.append(
                '<div class="figure missing">Figure <code>'
                + os.path.join(FIGURES_DIR, slide["figure"])
                + "</code> not found &mdash; export it from "
                "<code>04_Visualize_result_model.ipynb</code> and commit it to the repo."
                "</div>"
            )

    parts.append("</div></section>")
    return "".join(parts)


def _build_css(theme):
    t = THEMES[theme]
    return f"""
<style>
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: "Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }}
  .deck {{
    --text: {t['text']};
    --muted: {t['muted']};
    --strong: {t['strong']};
    --surface: {t['surface']};
    --border: {t['border']};
    --glass: {BIN_COLORS['glass']};
    --metal: {BIN_COLORS['metal']};
    --paper: {BIN_COLORS['paper']};
    --plastic: {BIN_COLORS['plastic']};
    position: relative;
    height: 700px;
    border-radius: 18px;
    overflow: hidden;
    background: {t['bg']};
    color: var(--text);
    box-shadow: 0 18px 46px rgba(0, 0, 0, 0.28);
    user-select: none;
  }}
  .deck:fullscreen {{ height: 100vh; border-radius: 0; }}

  /* Recycling mobius watermark, bottom-right of every slide. */
  .deck::after {{
    content: "\\267B";
    position: absolute;
    right: -30px; bottom: -76px;
    font-size: 310px; line-height: 1;
    color: {t['watermark']};
    pointer-events: none;
    z-index: 0;
  }}

  /* Four-colour ribbon down the left edge — the deck's recycling signature. */
  .deck::before {{
    content: "";
    position: absolute; left: 0; top: 0; bottom: 0; width: 7px; z-index: 4;
    background: linear-gradient(180deg,
      var(--glass) 0%, var(--glass) 25%,
      var(--metal) 25%, var(--metal) 50%,
      var(--paper) 50%, var(--paper) 75%,
      var(--plastic) 75%, var(--plastic) 100%);
  }}

  .slide {{
    position: absolute;
    inset: 0;
    padding: 42px 58px 74px 68px;
    opacity: 0;
    visibility: hidden;
    transform: translateY(14px);
    transition: opacity .32s ease, transform .32s ease;
    overflow-y: auto;
    z-index: 1;
  }}
  .slide.active {{ opacity: 1; visibility: visible; transform: none; }}
  .slide-inner {{ max-width: 1000px; margin: 0 auto; }}

  .slide-title {{ display: flex; align-items: center; justify-content: center; text-align: center; }}
  .slide-title h1 {{ font-size: 3.5rem; border: none; padding: 0; margin-bottom: .5rem; }}
  .slide-title .kicker {{ justify-content: center; }}

  .kicker {{
    display: inline-flex; align-items: center; gap: 9px;
    font-size: .76rem; letter-spacing: .17em; text-transform: uppercase;
    color: var(--accent); margin-bottom: 13px; font-weight: 700;
  }}
  .kicker-dot {{ width: 7px; height: 7px; border-radius: 50%; background: var(--accent); }}
  h1 {{
    font-size: 2.25rem; line-height: 1.15; margin: 0 0 20px;
    padding-bottom: 13px; font-weight: 700; color: var(--strong);
    border-bottom: 2px solid var(--accent);
  }}
  .content {{ font-size: 1.06rem; line-height: 1.6; }}
  ul {{ padding-left: 20px; margin: 0 0 14px; }}
  li {{ margin-bottom: 10px; }}
  li::marker {{ color: var(--accent); }}
  b {{ color: var(--strong); font-weight: 700; }}
  .lead {{ font-size: 1.35rem; color: var(--text); margin: 0 0 16px; }}
  .team {{ font-size: 1.05rem; color: var(--muted); margin: 18px 0 0; }}
  .note {{ font-size: .95rem; color: var(--muted); margin: 8px 0 12px; }}

  .illus {{ width: 100%; height: auto; margin: 4px 0 10px; color: var(--text); }}

  .callout {{
    margin-top: 14px; padding: 14px 19px;
    background: var(--surface);
    border-left: 4px solid var(--accent);
    border-radius: 0 10px 10px 0; font-size: 1rem;
  }}

  .chips {{ display: flex; gap: 10px; flex-wrap: wrap; margin: 18px 0; }}
  .chips-center {{ justify-content: center; }}
  .chip {{
    padding: 7px 20px; border-radius: 999px;
    font-weight: 700; font-size: .92rem; color: #11201b;
  }}
  .chip-glass {{ background: var(--glass); }}
  .chip-metal {{ background: var(--metal); }}
  .chip-paper {{ background: var(--paper); color: #fff; }}
  .chip-plastic {{ background: var(--plastic); }}

  .bins {{ display: flex; gap: 12px; flex-wrap: wrap; margin: 14px 0; }}
  .bin {{
    flex: 1; min-width: 140px; border-radius: 12px; padding: 13px 16px;
    background: var(--surface); border-top: 4px solid;
  }}
  .bin-glass {{ border-color: var(--glass); }}
  .bin-metal {{ border-color: var(--metal); }}
  .bin-paper {{ border-color: var(--paper); }}
  .bin-plastic {{ border-color: var(--plastic); }}
  .bin-icon {{ font-size: 1.5rem; display: block; }}
  .bin-name {{ display: block; font-weight: 700; margin-top: 3px; color: var(--strong); }}
  .bin-where {{ display: block; font-size: .82rem; color: var(--muted); }}

  .stats {{ display: flex; gap: 13px; flex-wrap: wrap; margin-top: 12px; }}
  .stat {{
    flex: 1; min-width: 130px; background: var(--surface);
    border: 1px solid var(--border); border-left: 4px solid var(--accent);
    border-radius: 12px; padding: 13px 17px;
  }}
  .stat-num {{ display: block; font-size: 1.65rem; font-weight: 700; color: var(--accent); }}
  .stat-label {{ display: block; font-size: .82rem; color: var(--muted); margin-top: 2px; }}

  .figure {{ margin-top: 12px; text-align: center; }}
  .figure img {{
    max-width: 100%; max-height: 385px;
    border-radius: 10px; background: {t['img_bg']}; padding: 10px;
  }}
  .figure.missing {{
    padding: 24px; border: 1px dashed var(--accent);
    border-radius: 12px; color: var(--muted); font-size: .94rem; text-align: left;
  }}
  code {{ background: var(--surface); padding: 2px 6px; border-radius: 4px; font-size: .88em; }}

  /* Click zones — left edge goes back, right edge goes forward. */
  .zone {{ position: absolute; top: 0; bottom: 58px; width: 20%; cursor: pointer; z-index: 2; }}
  .zone-prev {{ left: 7px; }}
  .zone-next {{ right: 0; }}

  .bar {{
    position: absolute; left: 0; right: 0; bottom: 0; height: 58px; z-index: 5;
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 22px 0 30px; gap: 16px;
    background: linear-gradient(to top, rgba(0, 0, 0, .30), transparent);
  }}
  .dots {{ display: flex; gap: 7px; flex-wrap: wrap; }}
  .dot {{
    width: 9px; height: 9px; border-radius: 50%; cursor: pointer;
    background: var(--border); border: none; padding: 0; transition: all .2s ease;
  }}
  .dot:hover {{ transform: scale(1.3); opacity: .8; }}
  .dot.active {{ width: 26px; border-radius: 5px; }}
  .dot-glass.active {{ background: var(--glass); }}
  .dot-metal.active {{ background: var(--metal); }}
  .dot-paper.active {{ background: var(--paper); }}
  .dot-plastic.active {{ background: var(--plastic); }}
  .bar-right {{ display: flex; align-items: center; gap: 14px; }}
  .counter {{ font-size: .85rem; color: var(--muted); font-variant-numeric: tabular-nums; }}
  .fs-btn {{
    background: var(--surface); border: 1px solid var(--border);
    color: var(--muted); border-radius: 7px; padding: 5px 11px;
    font-size: .8rem; cursor: pointer;
  }}
  .fs-btn:hover {{ color: var(--text); }}

  .progress {{
    position: absolute; top: 0; left: 0; height: 3px; z-index: 6;
    background: var(--glass); transition: width .3s ease, background .3s ease;
  }}
</style>
"""


_DECK_JS = """
<script>
  (function () {
    var deck = document.getElementById('deck');
    var slides = Array.prototype.slice.call(deck.querySelectorAll('.slide'));
    var dots = Array.prototype.slice.call(deck.querySelectorAll('.dot'));
    var counter = deck.querySelector('.counter');
    var progress = deck.querySelector('.progress');
    var current = 0;

    function go(next) {
      if (next < 0 || next >= slides.length) { return; }
      slides[current].classList.remove('active');
      if (dots[current]) { dots[current].classList.remove('active'); }
      current = next;
      slides[current].classList.add('active');
      if (dots[current]) { dots[current].classList.add('active'); }
      slides[current].scrollTop = 0;
      counter.textContent = (current + 1) + ' / ' + slides.length;
      progress.style.width = ((current + 1) / slides.length * 100) + '%';
      // Progress bar takes on the current slide's bin colour.
      progress.style.background = getComputedStyle(slides[current]).getPropertyValue('--accent');
    }

    deck.querySelector('.zone-next').addEventListener('click', function () { go(current + 1); });
    deck.querySelector('.zone-prev').addEventListener('click', function () { go(current - 1); });
    dots.forEach(function (dot, i) {
      dot.addEventListener('click', function () { go(i); });
    });

    // Keyboard. The deck has tabindex so it can hold focus inside the iframe;
    // click it once and the arrow keys / space / a presenter clicker all work.
    deck.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight' || e.key === 'PageDown' || e.key === ' ') { go(current + 1); e.preventDefault(); }
      else if (e.key === 'ArrowLeft' || e.key === 'PageUp') { go(current - 1); e.preventDefault(); }
      else if (e.key === 'Home') { go(0); e.preventDefault(); }
      else if (e.key === 'End') { go(slides.length - 1); e.preventDefault(); }
      else if (e.key === 'f' || e.key === 'F') { toggleFullscreen(); }
    });
    deck.focus();

    // Touch swipe, for presenting from a tablet.
    var startX = null;
    deck.addEventListener('touchstart', function (e) { startX = e.touches[0].clientX; }, { passive: true });
    deck.addEventListener('touchend', function (e) {
      if (startX === null) { return; }
      var dx = e.changedTouches[0].clientX - startX;
      if (Math.abs(dx) > 55) { go(dx < 0 ? current + 1 : current - 1); }
      startX = null;
    }, { passive: true });

    function toggleFullscreen() {
      try {
        if (!document.fullscreenElement) { deck.requestFullscreen(); }
        else { document.exitFullscreen(); }
      } catch (err) { /* blocked by iframe policy — use browser F11 instead */ }
    }
    deck.querySelector('.fs-btn').addEventListener('click', toggleFullscreen);

    go(0);
  })();
</script>
"""


def build_deck_html(theme=None):
    """Assemble the whole deck into one HTML string."""
    theme = theme or ACTIVE_THEME
    slides_html = "".join(_build_slide_html(s, i) for i, s in enumerate(SLIDES))

    dots_html = ""
    for i, slide in enumerate(SLIDES):
        accent_name = slide.get("accent", "glass")
        dots_html += (
            '<button class="dot dot-' + accent_name
            + (" active" if i == 0 else "")
            + '" title="Slide ' + str(i + 1) + '"></button>'
        )

    return (
        _build_css(theme)
        + '<div class="deck" id="deck" tabindex="0">'
        + '<div class="progress" style="width:0%"></div>'
        + slides_html
        + '<div class="zone zone-prev"></div><div class="zone zone-next"></div>'
        + '<div class="bar">'
        + '<div class="dots">' + dots_html + "</div>"
        + '<div class="bar-right">'
        + '<span class="counter">1 / ' + str(len(SLIDES)) + "</span>"
        + '<button class="fs-btn">&#9906; Fullscreen</button>'
        + "</div></div></div>"
        + _DECK_JS
    )


def render_slides(theme=None):
    """Drop the deck into the current Streamlit container."""
    st.caption(
        "Click the deck, then use \u2190 / \u2192 (or a presenter clicker) to navigate. "
        "You can also click the left/right edges, jump with the dots, or press F for fullscreen."
    )
    components.html(build_deck_html(theme), height=DECK_HEIGHT, scrolling=False)
