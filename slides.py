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

To change the look, set ACTIVE_THEME to any key in THEMES.
To edit content, edit the SLIDES list.

Layout components available inside a slide "body" (all styled in STATIC_CSS):
    .cards / .card        numbered feature cards, .card.featured for the highlight
    .steps / .step        numbered vertical process flow with connectors
    .splitbar             proportional stacked bar (e.g. train/val/test)
    .rows / .row          comparison rows with a type pill and role column
    .arch / .arch-col     side-by-side architecture columns with flow boxes
    .fusion               dual-branch fusion diagram
    .tri / .tri-col       three-column summary (achievements/limitations/next)
    .banner               full-width closing statement
    .tiers / .tier        ranked result bands
"""

import base64
import os

import streamlit as st
import streamlit.components.v1 as components

# Same folder the Compare tab reads its exported Colab charts from.
FIGURES_DIR = "figures"

# Height of the deck component in pixels.
DECK_HEIGHT = 720


# ─────────────────────────────────────────────────────────────────────────────
# Themes
# ─────────────────────────────────────────────────────────────────────────────
# The four bin colours match RECYCLE_INFO in app.py, so the deck, the app UI and
# the physical bin colours all agree.
BIN_COLORS = {
    "glass": "#2ecc71",
    "metal": "#3498db",
    "paper": "#9b59b6",
    "plastic": "#f39c12",
}

# Darker versions for TEXT on a light background — the bright set above is tuned
# for shapes, and amber especially is unreadable as body text on beige.
BIN_TEXT_DARK = {
    "glass": "#12684a",
    "metal": "#1c5f8f",
    "paper": "#7333a0",
    "plastic": "#96600a",
}

THEMES = {
    # Default: clean off-white with deep green ink, in the style of a printed
    # report. Survives a washed-out projector far better than a dark deck.
    "paper": {
        "bg": "linear-gradient(160deg, #fbfcfb 0%, #f6f8f6 55%, #f2f6f4 100%)",
        "text": "#2b3330",
        "muted": "#6d7a75",
        "strong": "#0f3b2c",
        "surface": "#ffffff",
        "surface_alt": "rgba(18, 104, 74, .07)",
        "border": "rgba(20, 60, 45, .13)",
        "watermark": "rgba(18, 104, 74, .035)",
        "img_bg": "#ffffff",
        "shadow": "0 2px 10px rgba(20, 60, 45, .07)",
        "accent_mode": "dark",
        "pos": "#12684a",
        "neg": "#b03030",
    },
    # Warmer paper tone.
    "beige": {
        "bg": "linear-gradient(155deg, #faf6ed 0%, #f5efe2 55%, #f1ebde 100%)",
        "text": "#33302a",
        "muted": "#777064",
        "strong": "#1a1814",
        "surface": "#fffdf8",
        "surface_alt": "rgba(90, 72, 42, .075)",
        "border": "rgba(90, 72, 42, .17)",
        "watermark": "rgba(90, 72, 42, .05)",
        "img_bg": "#ffffff",
        "shadow": "0 2px 10px rgba(90, 72, 42, .08)",
        "accent_mode": "dark",
        "pos": "#1a7a45",
        "neg": "#c0392b",
    },
    # Dark option.
    "recycle": {
        "bg": "linear-gradient(155deg, #14231f 0%, #10201c 40%, #131d26 100%)",
        "text": "#eef4f0",
        "muted": "#93aaa1",
        "strong": "#ffffff",
        "surface": "rgba(255, 255, 255, .055)",
        "surface_alt": "rgba(255, 255, 255, .085)",
        "border": "rgba(255, 255, 255, .12)",
        "watermark": "rgba(255, 255, 255, .028)",
        "img_bg": "#ffffff",
        "shadow": "none",
        "accent_mode": "bright",
        "pos": "#4ade80",
        "neg": "#f87171",
    },
}

ACTIVE_THEME = "paper"


# ─────────────────────────────────────────────────────────────────────────────
# Inline illustrations
# ─────────────────────────────────────────────────────────────────────────────

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
<svg viewBox="0 0 900 205" xmlns="http://www.w3.org/2000/svg" class="illus">
  <text x="20" y="16" font-size="14" font-weight="700" fill="#c0392b">&#10007; &nbsp;Without classification</text>
  <g transform="translate(64,24)" color="currentColor">
    {_bin_svg(0, "#8a9490", "One mixed bin", lid_open=True)}
    <circle cx="18" cy="14" r="7" fill="{BIN_COLORS['glass']}"/>
    <rect x="32" y="6" width="13" height="13" rx="2" fill="{BIN_COLORS['plastic']}"/>
    <circle cx="58" cy="12" r="6" fill="{BIN_COLORS['metal']}"/>
    <rect x="44" y="18" width="12" height="9" rx="2" fill="{BIN_COLORS['paper']}"/>
  </g>
  <text x="46" y="192" font-size="12.5" fill="#c0392b">Contaminated &#8594; landfill</text>
  <line x1="330" y1="30" x2="330" y2="176" stroke="currentColor" stroke-opacity=".15" stroke-width="1.5"/>
  <text x="380" y="16" font-size="14" font-weight="700" fill="#12684a">&#10003; &nbsp;With AI classification</text>
  <g transform="translate(380,24)" color="currentColor">
    {_bin_svg(0, BIN_COLORS['glass'], "Glass")}
    {_bin_svg(115, BIN_COLORS['metal'], "Metal")}
    {_bin_svg(230, BIN_COLORS['paper'], "Paper")}
    {_bin_svg(345, BIN_COLORS['plastic'], "Plastic")}
  </g>
  <text x="380" y="192" font-size="12.5" fill="#12684a">Clean streams &#8594; actually recycled</text>
</svg>
"""


IOT_UPGRADE_SVG = f"""
<svg viewBox="0 0 880 128" xmlns="http://www.w3.org/2000/svg" class="illus">
  <rect x="4" y="12" width="330" height="104" rx="12"
        fill="currentColor" fill-opacity=".04" stroke="currentColor" stroke-opacity=".15"/>
  <text x="24" y="40" font-size="11.5" font-weight="700" fill="currentColor" opacity=".5"
        letter-spacing="1.6">PREVIOUS IoT PROJECT</text>
  <text x="24" y="68" font-size="17" font-weight="700" fill="currentColor">Wet / Dry waste bin</text>
  <text x="24" y="91" font-size="13" fill="currentColor" opacity=".62">2 categories &#183; no camera</text>
  <text x="24" y="109" font-size="13" fill="currentColor" opacity=".62">Bin decides by hardware</text>
  <line x1="352" y1="64" x2="508" y2="64" stroke="var(--accent)" stroke-width="2.5"/>
  <polygon points="508,58 522,64 508,70" fill="var(--accent)"/>
  <text x="374" y="50" font-size="12.5" font-weight="700" fill="var(--accent-text)">give it eyes</text>
  <rect x="540" y="12" width="336" height="104" rx="12"
        fill="var(--accent)" fill-opacity=".09"
        stroke="var(--accent)" stroke-opacity=".45"/>
  <text x="560" y="40" font-size="11.5" font-weight="700" fill="var(--accent-text)"
        letter-spacing="1.6">THIS PROJECT</text>
  <text x="560" y="68" font-size="17" font-weight="700" fill="currentColor">Computer vision classifier</text>
  <text x="560" y="91" font-size="13" fill="currentColor" opacity=".72">4 categories &#183; camera input</text>
  <text x="560" y="109" font-size="13" fill="currentColor" opacity=".72">Bin decides by what it sees</text>
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
# Each slide dict:
#   "title"   — heading
#   "kicker"  — section label; auto-prefixed with the slide number
#   "accent"  — bin colour used for rules, numbers and bold text
#   "body"    — HTML content
#   "figure"  — optional PNG in FIGURES_DIR; puts the slide in two-column mode
#   "layout"  — "title" for the centred cover slide

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
        "kicker": "The Problem",
        "accent": "plastic",
        "title": "Sorting Is the Bottleneck",
        "body": SORTING_COMPARISON_SVG
        + """
            <ul class="tight">
              <li>Recycling is one of the most effective ways to cut pollution &mdash; but it only
                  works if waste is <b>sorted correctly</b>.</li>
              <li>Sorting today relies on <b>manual identification and public knowledge</b>, both
                  inconsistent and error-prone.</li>
              <li>Misclassified recyclables get <b>contaminated</b>, and end up in landfill anyway.</li>
            </ul>
            <div class="callout">
              <b>Our approach:</b> use computer vision to classify a waste photo automatically,
              and tell the user which bin it belongs in.
            </div>
        """,
    },
    {
        "kicker": "Background",
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
        "kicker": "Background",
        "accent": "paper",
        "title": "Five Eras of Computer Vision",
        "body": """
            <p class="note">The five approaches we compare aren't five random choices &mdash;
            each is a different generation of image-recognition technique, put on the same
            845-image test set:</p>
        """
        + MODEL_TIMELINE_SVG
        + """
            <div class="callout">
              <b>Why it matters:</b> if a newer or pretrained model wins, that tells us something
              different than if our own from-scratch CNN wins &mdash; the comparison is really a test
              of <i>which era of technique</i> fits this problem best.
            </div>
        """,
    },
    {
        "kicker": "Objectives",
        "accent": "metal",
        "title": "Five Objectives",
        "body": """
            <div class="cards">
              <div class="card">
                <span class="card-num">1</span>
                <span class="card-title">BUILD</span>
                <span class="card-desc">An AI classification system for four recyclable classes</span>
              </div>
              <div class="card">
                <span class="card-num">2</span>
                <span class="card-title">PREPARE</span>
                <span class="card-desc">Resize, normalise and augment the waste dataset</span>
              </div>
              <div class="card">
                <span class="card-num">3</span>
                <span class="card-title">COMPARE</span>
                <span class="card-desc">Deep-learning algorithms, evaluated head-to-head</span>
              </div>
              <div class="card">
                <span class="card-num">4</span>
                <span class="card-title">EVALUATE</span>
                <span class="card-desc">Accuracy, precision, recall and F1-score</span>
              </div>
              <div class="card featured">
                <span class="badge">PROPOSED</span>
                <span class="card-num">5</span>
                <span class="card-title">FUSE</span>
                <span class="card-desc">ResNet50 + CLIP feature-level fusion</span>
              </div>
            </div>
            <p class="note center">Objectives map directly to report Section 1.3.</p>
        """,
    },
    {
        "kicker": "Proposed System",
        "accent": "glass",
        "title": "One Pipeline &mdash; Five Models",
        "body": """
            <div class="steps">
              <div class="step"><span class="step-num">1</span>Merge two Kaggle garbage datasets</div>
              <div class="step"><span class="step-num">2</span>Fixed stratified 70/15/15 split (CSV)</div>
              <div class="step"><span class="step-num">3</span>Preprocess + augment training data</div>
              <div class="step"><span class="step-num">4</span>Train five models</div>
              <div class="step"><span class="step-num">5</span>Evaluate on the same 845 test images</div>
              <div class="step"><span class="step-num">6</span>Deploy prototype (Streamlit + TFLite)</div>
            </div>
            <div class="callout">
              The split is written to CSV <b>once</b> and reused by every model, so all five are
              judged on <b>identical data</b> &mdash; that's what makes the comparison fair.
            </div>
        """,
        "figure": "fig_system_flowchart.png",
        "figure_caption": "System flowchart &mdash; report Fig. 3.1.1",
    },
    {
        "kicker": "Dataset",
        "accent": "paper",
        "title": "5,629 Images, Four Classes",
        "body": """
            <p class="note">Two public Kaggle datasets merged for more images and more visual
            variation, reduced to the four recyclable categories, with exact duplicates removed.</p>
            <div class="bins">
              <div class="bin bin-glass"><span class="bin-name">Glass</span><span class="bin-count">1,147</span><span class="bin-where">Green bin</span></div>
              <div class="bin bin-metal"><span class="bin-name">Metal</span><span class="bin-count">1,210</span><span class="bin-where">Metal recycling</span></div>
              <div class="bin bin-paper"><span class="bin-name">Paper</span><span class="bin-count">1,726</span><span class="bin-where">Blue bin</span></div>
              <div class="bin bin-plastic"><span class="bin-name">Plastic</span><span class="bin-count">1,546</span><span class="bin-where">Yellow bin</span></div>
            </div>
            <p class="note">Stratified split, fixed once and shared by every model:</p>
            <div class="splitbar">
              <div class="seg seg-a" style="flex:70">Train 3,940 &#183; 70%</div>
              <div class="seg seg-b" style="flex:15">Validation 844 &#183; 15%</div>
              <div class="seg seg-c" style="flex:15">Test 845 &#183; 15%</div>
            </div>
            <p class="note">Paper is both the <b>largest class</b> and the <b>easiest to classify</b>
            &mdash; worth remembering when we read the per-class results.</p>
        """,
    },
    {
        "kicker": "Algorithms",
        "accent": "metal",
        "title": "The Five Approaches",
        "body": """
            <div class="rows">
              <div class="row">
                <span class="row-name">CNN</span>
                <span class="pill">Baseline &mdash; from scratch</span>
                <span class="row-why">Learns features directly from our images</span>
                <span class="row-role">Reference point</span>
              </div>
              <div class="row">
                <span class="row-name">MobileNetV2</span>
                <span class="pill">Transfer learning</span>
                <span class="row-why">Depthwise separable convolutions keep it light</span>
                <span class="row-role">Efficient edge deployment</span>
              </div>
              <div class="row">
                <span class="row-name">ResNet50</span>
                <span class="pill">Transfer learning</span>
                <span class="row-why">Residual connections, deep feature extraction</span>
                <span class="row-role">High-accuracy end</span>
              </div>
              <div class="row">
                <span class="row-name">CLIP Linear Probe</span>
                <span class="pill">Vision-language</span>
                <span class="row-why">Frozen CLIP encoder + one trained linear layer</span>
                <span class="row-role">Semantic features + verification</span>
              </div>
              <div class="row featured">
                <span class="badge">PROPOSED</span>
                <span class="row-name">ResNet50 + CLIP Fusion</span>
                <span class="pill">Feature-level fusion</span>
                <span class="row-why">Joins task-specific and general features</span>
                <span class="row-role">Our combined algorithm</span>
              </div>
            </div>
            <p class="note center">Five eras of computer vision &mdash; 1998 &#8594; 2015 &#8594; 2018
            &#8594; 2021 &#8594; ours &mdash; on one shared test set.</p>
        """,
    },
    {
        "kicker": "CNN Family",
        "accent": "glass",
        "title": "From Baseline to Deep Transfer Learning",
        "body": """
            <div class="arch">
              <div class="arch-col">
                <span class="arch-name">CNN</span>
                <span class="pill">From scratch</span>
                <div class="flow">
                  <span class="fbox">Input 224&times;224</span>
                  <span class="farrow">&darr;</span>
                  <span class="fbox">Conv + Pool blocks</span>
                  <span class="farrow">&darr;</span>
                  <span class="fbox">Dense</span>
                  <span class="farrow">&darr;</span>
                  <span class="fbox">Softmax (4 classes)</span>
                </div>
                <span class="arch-cfg">Adam &#183; LR 1e-4 &#183; 103 epochs (early stopping)</span>
                <span class="arch-role">Baseline &mdash; what our data alone can learn</span>
              </div>
              <div class="arch-col">
                <span class="arch-name">MobileNetV2</span>
                <span class="pill">Transfer learning</span>
                <div class="flow">
                  <span class="fbox">ImageNet weights</span>
                  <span class="farrow">&darr;</span>
                  <span class="fbox">Inverted residuals + depthwise conv</span>
                  <span class="farrow">&darr;</span>
                  <span class="fbox">Feature head</span>
                  <span class="farrow">&darr;</span>
                  <span class="fbox">Fine-tune upper layers</span>
                </div>
                <span class="arch-cfg">Head 1e-4 &#8594; fine-tune 1e-5 &#183; 85 + 10 epochs</span>
                <span class="arch-role">Lightweight &mdash; built for mobile and smart bins</span>
              </div>
              <div class="arch-col">
                <span class="arch-name">ResNet50</span>
                <span class="pill">Transfer learning</span>
                <div class="flow">
                  <span class="fbox">ImageNet weights</span>
                  <span class="farrow">&darr;</span>
                  <span class="fbox">Residual (skip) connections</span>
                  <span class="farrow">&darr;</span>
                  <span class="fbox">Global pooling</span>
                  <span class="farrow">&darr;</span>
                  <span class="fbox">Fine-tune upper layers</span>
                </div>
                <span class="arch-cfg">Head 1e-3 &#8594; fine-tune 1e-5 &#183; 20 + 15 epochs &#183; seed 42</span>
                <span class="arch-role">Deepest extractor &mdash; the accuracy end</span>
              </div>
            </div>
        """,
    },
    {
        "kicker": "Proposed Fusion",
        "accent": "metal",
        "title": "Dual-Branch Feature Fusion",
        "body": """
            <div class="probe-strip">
              <b>CLIP Linear Probe:</b>
              <span class="fbox sm">image</span><span class="farrow inline">&rarr;</span>
              <span class="fbox sm">frozen CLIP encoder</span><span class="farrow inline">&rarr;</span>
              <span class="fbox sm">512-d</span><span class="farrow inline">&rarr;</span>
              <span class="fbox sm">linear layer &rarr; 4</span>
              <span class="probe-note">one trained layer reached 90.65%</span>
            </div>
            <div class="fusion">
              <div class="fnode top">Input image &#183; 224&times;224</div>
              <div class="fsplit">
                <div class="fbranch">
                  <span class="farrow">&darr;</span>
                  <div class="fcard">
                    <span class="fcard-title">ResNet50 <span class="tag">fine-tuned</span></span>
                    <span class="fbox sm">2048-d feature</span>
                    <span class="farrow inline">&rarr;</span>
                    <span class="fbox sm">dense projection</span>
                    <span class="farrow inline">&rarr;</span>
                    <span class="fbox sm">512-d</span>
                  </div>
                </div>
                <div class="fbranch">
                  <span class="farrow">&darr;</span>
                  <div class="fcard">
                    <span class="fcard-title">CLIP image encoder <span class="tag lock">FROZEN</span></span>
                    <span class="fbox sm">512-d feature</span>
                  </div>
                </div>
              </div>
              <div class="fsplit arrows">
                <span class="farrow">&darr;</span>
                <span class="farrow">&darr;</span>
              </div>
              <div class="fnode join">Concatenate &nbsp;&rarr;&nbsp; 1024-d joint representation</div>
              <div class="fsplit arrows one"><span class="farrow">&darr;</span></div>
              <div class="fhead">
                <b>Classification head:</b>
                <span class="fbox sm">dense</span><span class="farrow inline">&rarr;</span>
                <span class="fbox sm">dropout</span><span class="farrow inline">&rarr;</span>
                <span class="fbox sm">dense</span><span class="farrow inline">&rarr;</span>
                <span class="fbox sm">softmax</span>
                <span class="farrow inline">&rarr;</span>
                <span class="chip chip-glass sm">Glass</span>
                <span class="chip chip-metal sm">Metal</span>
                <span class="chip chip-paper sm">Paper</span>
                <span class="chip chip-plastic sm">Plastic</span>
              </div>
            </div>
            <div class="foot-notes">
              <span class="fnote">CLIP encoder stays frozen throughout</span>
              <span class="fnote">Two-phase training: fusion head first, then ResNet50 upper layers at 1e-5</span>
            </div>
        """,
    },
    {
        "kicker": "Results",
        "accent": "glass",
        "title": "Overall Test Accuracy",
        "body": """
            <p class="note">Every number comes from evaluating each model's <i>actual deployed
            file</i> on the shared 845-image test set. The five models fall into
            <b>three tiers</b>, not a clean five-way ranking:</p>
            <div class="tiers">
              <div class="tier">
                <span class="tier-score">97.16 / 96.80%</span>
                <span class="tier-body">
                  <span class="tier-name">ResNet50 &amp; Feature Fusion</span>
                  <span class="tier-note">Separated by 0.36 pp &mdash; 3 images out of 845.</span>
                </span>
              </div>
              <div class="tier">
                <span class="tier-score">92.66%</span>
                <span class="tier-body">
                  <span class="tier-name">MobileNetV2</span>
                  <span class="tier-note">Behind the top pair, but far smaller and faster.</span>
                </span>
              </div>
              <div class="tier">
                <span class="tier-score">90.65 / 90.41%</span>
                <span class="tier-body">
                  <span class="tier-name">CLIP Linear Probe &amp; CNN</span>
                  <span class="tier-note">Separated by 0.24 pp &mdash; 2 images. Effectively tied.</span>
                </span>
              </div>
            </div>
            <ul class="tight">
              <li><b>Pretraining matters most.</b> ResNet50 beats our from-scratch CNN by
                  <b>6.75 pp</b> &mdash; the biggest gap in the study.</li>
              <li><b>CLIP never saw a waste image</b>, yet its frozen features match a CNN trained
                  directly on our data.</li>
            </ul>
        """,
        "figure": "fig1_overall_accuracy.png",
    },
    {
        "kicker": "Error Analysis",
        "accent": "plastic",
        "title": "The Errors Are Not Random",
        "body": """
            <p class="note">Off the diagonal, every model makes the same mistake:</p>
            <ul class="tight">
              <li><b>Paper is easiest</b> for every model &mdash; matte, opaque, printed texture gives
                  stable features.</li>
              <li><b>Glass and Plastic are hardest</b>, in every architecture. Both are transparent
                  and reflective, so what the model sees depends on the background behind the item.</li>
              <li>The largest error is <b>directional</b>, not a symmetric mix-up:
                  <b>Glass predicted as Plastic</b> &mdash; from 6 images in ResNet50 up to 25 in the
                  CLIP Linear Probe. The reverse is always smaller.</li>
              <li>Half of ResNet50's <b>most confident</b> errors come from Glass alone &mdash; so the
                  model is sometimes <b>confidently wrong</b>, not merely uncertain.</li>
            </ul>
            <div class="callout">
              The pattern appears in the weakest and strongest model alike, so it points at the
              <b>materials</b>, not the architecture.
            </div>
        """,
        "figure": "fig3_confusion_matrices.png",
    },
    {
        "kicker": "Results",
        "accent": "paper",
        "title": "Does CLIP Verify Actually Help?",
        "body": """
            <p class="note">Below 90% confidence, the prediction is handed to the CLIP Linear Probe.
            The effect <b>depends entirely on which model you start from</b>:</p>
            <table>
              <tr><th>Primary model</th><th class="num">Alone</th><th class="num">Gated</th><th class="num">Change</th></tr>
              <tr><td>CNN</td><td class="num">90.41%</td><td class="num">92.43%</td>
                  <td class="num"><span class="up">+2.02 pp</span></td></tr>
              <tr><td>MobileNetV2</td><td class="num">92.66%</td><td class="num">94.32%</td>
                  <td class="num"><span class="up">+1.66 pp</span></td></tr>
              <tr class="highlight"><td>ResNet50</td><td class="num">97.16%</td><td class="num">96.21%</td>
                  <td class="num"><span class="down">&minus;0.95 pp</span></td></tr>
            </table>
            <ul class="tight">
              <li>It <b>helps the weaker models</b> &mdash; their low-confidence predictions really
                  were often wrong.</li>
              <li>It <b>hurts the strongest</b>. ResNet50 unsure is still usually more right than CLIP.</li>
              <li><b>No gated combination beats ResNet50 alone</b> (97.16%) &mdash; verification lifts
                  the weak models, never the ceiling.</li>
            </ul>
            <div class="callout">
              <b>The lesson:</b> a second model is not automatically an improvement. It has to be
              better <i>precisely where the first one is unsure</i>.
            </div>
        """,
        "figure": "fig8_clip_verify_effect.png",
    },
    {
        "kicker": "Conclusion",
        "accent": "glass",
        "title": "What We Achieved &mdash; and What Comes Next",
        "body": """
            <div class="tri">
              <div class="tri-col col-good">
                <span class="tri-head">ACHIEVEMENTS</span>
                <ul>
                  <li>Working Streamlit prototype deployed</li>
                  <li>Five approaches on one fixed test set</li>
                  <li>ResNet50 best: <b>97.16%</b> accuracy</li>
                  <li>Fusion <b>96.80%</b> &mdash; complementary class behaviour</li>
                  <li>Class-level error analysis completed</li>
                </ul>
              </div>
              <div class="tri-col col-warn">
                <span class="tri-head">LIMITATIONS</span>
                <ul>
                  <li>Only four categories &#183; <b>845</b> test images</li>
                  <li>Glass &rarr; Plastic confusion persists</li>
                  <li>Fixed <b>0.90</b> threshold, not tuned</li>
                  <li>Single snapshots &mdash; no continuous video</li>
                  <li>Gating results reused the test set</li>
                  <li>Seeds fixed for only two of five models</li>
                </ul>
              </div>
              <div class="tri-col col-next">
                <span class="tri-head">FUTURE WORK</span>
                <ul>
                  <li>Larger, more diverse dataset + more classes</li>
                  <li>Model-specific confidence thresholds</li>
                  <li>Independent holdout evaluation</li>
                  <li>Standardise seeds across all five models</li>
                  <li>Real-time smart-bin / conveyor deployment</li>
                  <li>Compare late and attention-based fusion</li>
                </ul>
              </div>
            </div>
            <div class="banner">
              AI-based image classification can support more consistent recyclable waste identification.
            </div>
        """,
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Rendering
# ─────────────────────────────────────────────────────────────────────────────

def _figure_data_uri(filename):
    """Read a PNG from FIGURES_DIR and return it as a base64 data URI.

    The deck renders inside a sandboxed iframe, which cannot read local files by
    path, so images have to be inlined. Returns None if the file isn't there and
    the slide falls back to a placeholder rather than breaking the deck."""
    path = os.path.join(FIGURES_DIR, filename)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")
    except OSError:
        return None


def _build_slide_html(slide, index, theme):
    """Render one slide dict into its <section> markup.

    Two accent vars are set: --accent for shapes and rules (always the bright bin
    colour) and --accent-text for bold text, which switches to a darker shade on
    light themes so it stays readable."""
    accent_name = slide.get("accent", "glass")
    accent = BIN_COLORS.get(accent_name, BIN_COLORS["glass"])
    if THEMES[theme].get("accent_mode") == "dark":
        accent_text = BIN_TEXT_DARK.get(accent_name, BIN_TEXT_DARK["glass"])
    else:
        accent_text = accent

    has_figure = bool(slide.get("figure"))
    is_title = slide.get("layout") == "title"

    classes = "slide"
    if is_title:
        classes += " slide-title"
    if has_figure:
        classes += " has-figure"
    if index == 0:
        classes += " active"

    parts = [
        '<section class="' + classes + '" data-index="' + str(index)
        + '" style="--accent:' + accent + ';--accent-text:' + accent_text + '">',
        '<div class="slide-inner">',
    ]

    # With a figure the slide splits into two columns, so the heading and body go
    # in their own column rather than sitting above the chart.
    if has_figure:
        # .split-inner exists so auto-fit has something to shrink: the column
        # itself is sized by the flex row, so scaling it would shrink the
        # available height by exactly as much as the content, and the overflow
        # ratio would never change.
        parts.append('<div class="split-text"><div class="split-inner">')

    if slide.get("kicker"):
        # Section labels are numbered like "04 · PROPOSED SYSTEM"; the cover
        # slide keeps its plain subtitle instead.
        label = slide["kicker"] if is_title else f"{index + 1:02d} &#183; {slide['kicker']}"
        parts.append('<div class="kicker">' + label + "</div>")
    parts.append("<h1>" + slide["title"] + "</h1>")
    if not is_title:
        parts.append('<div class="rule"></div>')
    parts.append('<div class="content">' + slide.get("body", "") + "</div>")

    if has_figure:
        parts.append("</div></div>")  # /split-inner, /split-text
        uri = _figure_data_uri(slide["figure"])
        caption = slide.get("figure_caption")
        cap_html = ('<div class="fig-caption">' + caption + "</div>") if caption else ""
        if uri:
            parts.append(
                '<div class="split-fig"><img src="' + uri
                + '" alt="' + slide["figure"] + '">' + cap_html + "</div>"
            )
        else:
            parts.append(
                '<div class="split-fig"><div class="figure missing">Figure <code>'
                + os.path.join(FIGURES_DIR, slide["figure"])
                + "</code> not found &mdash; export it from "
                "<code>04_Visualize_result_model.ipynb</code> and commit it to the repo."
                "</div></div>"
            )

    parts.append("</div></section>")
    return "".join(parts)


# Static stylesheet. Kept out of the f-string so CSS braces stay single — only
# the theme variables below are interpolated.
STATIC_CSS = """
  * { box-sizing: border-box; }
  body { margin: 0; font-family: "Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }

  .deck {
    position: relative; height: 700px; border-radius: 18px; overflow: hidden;
    color: var(--text); box-shadow: 0 18px 46px rgba(0,0,0,.22); user-select: none;
  }
  .deck:fullscreen { height: 100vh; border-radius: 0; }
  .deck::after {
    content: "\\267B"; position: absolute; right: -30px; bottom: -76px;
    font-size: 300px; line-height: 1; color: var(--watermark); pointer-events: none; z-index: 0;
  }

  .slide {
    position: absolute; inset: 0; display: flex; flex-direction: column;
    padding: 40px 56px 70px; opacity: 0; visibility: hidden; transform: translateY(12px);
    transition: opacity .3s ease, transform .3s ease; overflow-y: auto; z-index: 1;
  }
  .slide.active { opacity: 1; visibility: visible; transform: none; }
  .slide-inner { max-width: 1080px; width: 100%; margin: auto; }

  /* Figure slides: text left, chart right, both sized to the slide. min-height:0
     is what lets the flex children shrink instead of overflowing the bottom. */
  .slide.has-figure { overflow: hidden; }
  .slide.has-figure .slide-inner {
    display: flex; flex-direction: row; align-items: stretch;
    gap: 30px; max-width: 1440px; height: 100%; margin: 0 auto;
  }
  .split-text {
    flex: 1 1 50%; min-height: 0; overflow-y: auto;
    display: flex; flex-direction: column; justify-content: safe center;
  }
  .split-fig { flex: 1 1 50%; min-height: 0; display: flex; align-items: center; justify-content: center; }
  .split-fig { flex-direction: column; gap: 8px; }
  .fig-caption {
    font-size: .8rem; color: var(--muted); text-align: center; flex: none;
  }
  /* A single centred connector arrow (Concatenate -> classification head). */
  .fsplit.arrows.one { justify-content: center; }
  .split-fig img {
    max-width: 100%; max-height: 100%; width: auto; height: auto; object-fit: contain;
    border-radius: 10px; background: var(--img-bg); padding: 10px;
  }
  .slide.has-figure .content { font-size: .97rem; line-height: 1.5; }
  .slide.has-figure h1 { font-size: 1.9rem; }
  .slide.has-figure li { margin-bottom: 6px; }
  .slide.has-figure table { font-size: .9rem; }
  .slide.has-figure td, .slide.has-figure th { padding: 6px 9px; }

  .slide-title { text-align: center; }
  .slide-title h1 { font-size: 3.6rem; margin-bottom: .4rem; }

  .kicker {
    font-size: .76rem; letter-spacing: .18em; text-transform: uppercase;
    color: var(--accent-text); margin-bottom: 10px; font-weight: 700;
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
  }
  h1 { font-size: 2.15rem; line-height: 1.12; margin: 0 0 12px; font-weight: 800; color: var(--strong); }
  .rule { width: 62px; height: 4px; border-radius: 2px; background: var(--accent); margin-bottom: 20px; }
  .content { font-size: 1.02rem; line-height: 1.58; }
  ul { padding-left: 20px; margin: 0 0 12px; }
  ul.tight li { margin-bottom: 5px; }
  li { margin-bottom: 8px; }
  li::marker { color: var(--accent); }
  b { color: var(--accent-text); font-weight: 700; }
  .lead { font-size: 1.3rem; color: var(--text); margin: 0 0 14px; }
  .team { font-size: 1.02rem; color: var(--muted); margin: 16px 0 0; }
  .note { font-size: .93rem; color: var(--muted); margin: 6px 0 10px; }
  .note.center { text-align: center; }
  .illus { width: 100%; height: auto; margin: 2px 0 8px; color: var(--text); }

  .callout {
    margin-top: 12px; padding: 12px 17px; background: var(--surface-alt);
    border-left: 4px solid var(--accent); border-radius: 0 9px 9px 0; font-size: .98rem;
  }

  table { width: 100%; border-collapse: collapse; font-size: .98rem; margin: 4px 0 10px; }
  th {
    text-align: left; padding: 8px 11px; color: var(--accent-text); font-size: .74rem;
    letter-spacing: .1em; text-transform: uppercase; border-bottom: 2px solid var(--accent);
  }
  td { padding: 8px 11px; border-bottom: 1px solid var(--border); }
  th.num, td.num { text-align: right; font-variant-numeric: tabular-nums; }
  tr.highlight td { background: var(--surface-alt); font-weight: 700; }
  .up { color: var(--pos); font-weight: 700; }
  .down { color: var(--neg); font-weight: 700; }

  /* Numbered feature cards */
  .cards { display: flex; gap: 13px; margin: 6px 0 12px; align-items: stretch; }
  .card {
    flex: 1; position: relative; background: var(--surface); border: 1px solid var(--border);
    border-radius: 13px; padding: 18px 16px 16px; box-shadow: var(--shadow);
    display: flex; flex-direction: column; gap: 7px;
  }
  .card.featured { border: 2px solid var(--accent); }
  .card-num { font-size: 2rem; font-weight: 800; color: var(--accent-text); line-height: 1; }
  .card-title { font-weight: 800; letter-spacing: .07em; color: var(--strong); font-size: .95rem; }
  .card-desc { font-size: .87rem; color: var(--muted); line-height: 1.45; }
  .badge {
    position: absolute; top: 12px; right: 12px; background: var(--accent);
    color: #fff; font-size: .6rem; font-weight: 800; letter-spacing: .1em;
    padding: 3px 9px; border-radius: 999px;
  }

  /* Horizontal model-history timeline */
  .timeline { position: relative; display: flex; margin: 10px 0 6px; padding-top: 8px; }
  .timeline::before {
    content: ""; position: absolute; left: 4%; right: 4%; top: 27px;
    height: 2px; background: var(--border);
  }
  .tl-item {
    flex: 1; display: flex; flex-direction: column; align-items: center;
    text-align: center; gap: 5px; position: relative; padding: 0 4px;
  }
  .tl-dot {
    width: 15px; height: 15px; border-radius: 50%; background: var(--accent);
    margin-bottom: 2px; position: relative; z-index: 1;
  }
  .tl-item.featured .tl-dot {
    width: 20px; height: 20px; background: var(--strong);
    box-shadow: 0 0 0 3px var(--accent);
  }
  .tl-year { font-size: .72rem; font-weight: 800; letter-spacing: .05em; color: var(--accent-text); }
  .tl-name { font-weight: 800; color: var(--strong); font-size: .93rem; }
  .tl-note { font-size: .78rem; color: var(--muted); line-height: 1.35; }

  /* Numbered process flow */
  .steps { display: flex; flex-direction: column; gap: 0; margin: 4px 0 10px; }
  .step {
    display: flex; align-items: center; gap: 14px; background: var(--surface);
    border: 1px solid var(--border); border-radius: 10px; padding: 9px 15px;
    font-size: .98rem; box-shadow: var(--shadow);
  }
  .step + .step { margin-top: 20px; position: relative; }
  .step + .step::before {
    content: "\\2193"; position: absolute; left: 26px; top: -19px; height: 18px;
    color: var(--accent); font-size: .95rem; line-height: 1;
  }
  .step-num {
    flex: none; width: 24px; height: 24px; border-radius: 7px; background: var(--surface-alt);
    color: var(--accent-text); font-weight: 800; font-size: .82rem;
    display: flex; align-items: center; justify-content: center;
  }

  /* Proportional split bar */
  .splitbar { display: flex; border-radius: 9px; overflow: hidden; margin: 6px 0 12px; font-size: .87rem; font-weight: 700; }
  .seg { padding: 11px 8px; text-align: center; white-space: nowrap; }
  .seg-a { background: var(--accent); color: #fff; }
  .seg-b { background: var(--accent); opacity: .62; color: #fff; }
  .seg-c { background: var(--surface-alt); color: var(--accent-text); }

  /* Comparison rows */
  .rows { display: flex; flex-direction: column; gap: 8px; margin: 4px 0 10px; }
  .row {
    position: relative; display: grid; grid-template-columns: 1.3fr 1.2fr 1.7fr 1.3fr;
    align-items: center; gap: 12px; background: var(--surface); border: 1px solid var(--border);
    border-radius: 11px; padding: 11px 16px; box-shadow: var(--shadow);
  }
  .row.featured { border: 2px solid var(--accent); padding-right: 124px; }
  .row-name { font-weight: 800; color: var(--strong); font-size: 1rem; }
  .row-why { font-size: .87rem; color: var(--muted); }
  .row-role { font-size: .88rem; font-weight: 700; color: var(--accent-text); }
  .pill {
    display: inline-block; background: var(--surface-alt); color: var(--accent-text);
    font-size: .78rem; font-weight: 700; padding: 4px 12px; border-radius: 999px;
    justify-self: start; white-space: nowrap;
  }
  .row.featured .badge { top: 50%; transform: translateY(-50%); right: 14px; }

  /* Architecture columns */
  .arch { display: flex; gap: 14px; align-items: stretch; margin: 2px 0 6px; }
  .arch-col {
    flex: 1; background: var(--surface); border: 1px solid var(--border); border-radius: 13px;
    padding: 15px 15px 13px; box-shadow: var(--shadow); display: flex; flex-direction: column; gap: 8px;
  }
  .arch-name { font-size: 1.15rem; font-weight: 800; color: var(--strong); }
  .arch-cfg {
    font-size: .78rem; color: var(--accent-text); background: var(--surface-alt);
    border-radius: 8px; padding: 7px 10px; font-family: ui-monospace, Menlo, monospace;
  }
  .arch-role { font-size: .85rem; font-weight: 700; color: var(--strong); margin-top: auto; }
  .flow { display: flex; flex-direction: column; align-items: stretch; gap: 2px; }
  .fbox {
    background: var(--surface-alt); border-radius: 8px; padding: 7px 11px;
    font-size: .84rem; text-align: center; color: var(--text);
  }
  .fbox.sm { padding: 4px 9px; font-size: .78rem; display: inline-block; }
  .farrow { color: var(--accent); text-align: center; font-size: .9rem; line-height: 1.1; }
  .farrow.inline { display: inline-block; margin: 0 3px; }

  /* Fusion diagram */
  .probe-strip {
    display: flex; align-items: center; gap: 5px; flex-wrap: wrap;
    background: var(--surface-alt); border: 1px solid var(--border); border-radius: 10px;
    padding: 9px 14px; font-size: .85rem; margin-bottom: 10px; box-shadow: var(--shadow);
  }
  .probe-note {
    margin-left: auto; background: var(--accent); color: #fff; font-size: .75rem;
    font-weight: 700; padding: 4px 11px; border-radius: 999px;
  }
  .fusion { display: flex; flex-direction: column; align-items: stretch; gap: 4px; }
  .fnode { text-align: center; font-weight: 700; border-radius: 10px; padding: 9px; }
  .fnode.top {
    background: var(--strong); color: #fff; align-self: center; padding: 9px 26px;
    border: 2px solid var(--accent);
  }
  .fnode.join { background: var(--accent); color: #fff; font-size: 1.05rem; }
  .fsplit { display: flex; gap: 14px; }
  .fsplit.arrows { justify-content: space-around; }
  .fsplit.arrows .farrow { flex: 1; }
  .fbranch { flex: 1; display: flex; flex-direction: column; }
  .fcard {
    background: var(--surface); border: 1px solid var(--border); border-radius: 11px;
    padding: 11px 14px; box-shadow: var(--shadow); flex: 1;
  }
  .fcard-title { display: block; font-weight: 800; color: var(--strong); margin-bottom: 7px; font-size: .95rem; }
  .tag {
    font-size: .62rem; font-weight: 800; letter-spacing: .08em; padding: 3px 8px;
    border-radius: 999px; background: var(--surface-alt); color: var(--accent-text);
  }
  .tag.lock { background: var(--strong); color: #fff; }
  .fhead {
    display: flex; align-items: center; gap: 5px; flex-wrap: wrap; font-size: .85rem;
    background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 9px 14px;
  }
  .foot-notes { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 8px; }
  .fnote {
    font-size: .8rem; color: var(--muted); background: var(--surface-alt);
    border-radius: 8px; padding: 6px 12px;
  }

  /* Three-column conclusion */
  .tri { display: flex; gap: 14px; align-items: stretch; margin: 2px 0 12px; }
  .tri-col {
    flex: 1; background: var(--surface); border: 1px solid var(--border);
    border-radius: 13px; padding: 15px 17px; box-shadow: var(--shadow); border-top: 4px solid;
  }
  .tri-col ul { padding-left: 17px; margin: 0; }
  .tri-col li { font-size: .89rem; margin-bottom: 8px; line-height: 1.42; }
  .tri-head { display: block; font-weight: 800; letter-spacing: .09em; font-size: .82rem; margin-bottom: 11px; }
  .col-good { border-top-color: var(--glass); }
  .col-good .tri-head, .col-good li::marker { color: var(--pos); }
  .col-warn { border-top-color: var(--plastic); }
  .col-warn .tri-head, .col-warn li::marker { color: #96600a; }
  .col-next { border-top-color: var(--metal); }
  .col-next .tri-head, .col-next li::marker { color: #1c5f8f; }

  .banner {
    background: var(--strong); color: #fff; text-align: center; font-weight: 700;
    font-size: 1.02rem; padding: 14px; border-radius: 11px;
  }

  .chips { display: flex; gap: 9px; flex-wrap: wrap; margin: 16px 0; }
  .chips-center { justify-content: center; }
  .chip { padding: 6px 18px; border-radius: 999px; font-weight: 700; font-size: .9rem; color: #11201b; }
  .chip.sm { padding: 3px 11px; font-size: .76rem; }
  .chip-glass { background: var(--glass); }
  .chip-metal { background: var(--metal); }
  .chip-paper { background: var(--paper); color: #fff; }
  .chip-plastic { background: var(--plastic); }

  .bins { display: flex; gap: 11px; flex-wrap: wrap; margin: 8px 0; }
  .bin {
    flex: 1; min-width: 130px; border-radius: 11px; padding: 12px 15px;
    background: var(--surface); border: 1px solid var(--border);
    border-top: 4px solid; box-shadow: var(--shadow);
  }
  .bin-glass { border-top-color: var(--glass); }
  .bin-metal { border-top-color: var(--metal); }
  .bin-paper { border-top-color: var(--paper); }
  .bin-plastic { border-top-color: var(--plastic); }
  .bin-name { display: block; font-weight: 800; color: var(--strong); }
  .bin-count { display: block; font-size: 1.3rem; font-weight: 800; color: var(--accent-text); }
  .bin-where { display: block; font-size: .8rem; color: var(--muted); }

  .tiers { display: flex; flex-direction: column; gap: 8px; margin: 8px 0 12px; }
  .tier {
    display: flex; align-items: baseline; gap: 15px; padding: 10px 15px; border-radius: 10px;
    background: var(--surface); border: 1px solid var(--border); border-left: 4px solid var(--accent);
  }
  .tier-score { font-size: 1.12rem; font-weight: 800; color: var(--accent-text); min-width: 98px; font-variant-numeric: tabular-nums; }
  .tier-body { flex: 1; }
  .tier-name { font-weight: 700; color: var(--strong); }
  .tier-note { font-size: .87rem; color: var(--muted); }

  .figure.missing {
    padding: 22px; border: 1px dashed var(--accent); border-radius: 12px;
    color: var(--muted); font-size: .92rem; text-align: left;
  }
  code { background: var(--surface-alt); padding: 2px 6px; border-radius: 4px; font-size: .88em; }

  /* Fullscreen: scale type up for projector distance. */
  .deck:fullscreen .slide { padding: 52px 82px 82px; }
  .deck:fullscreen .slide-inner { max-width: 1320px; }
  .deck:fullscreen h1 { font-size: 2.9rem; }
  .deck:fullscreen .slide-title h1 { font-size: 4.5rem; }
  .deck:fullscreen .content { font-size: 1.24rem; }
  .deck:fullscreen .note { font-size: 1.1rem; }
  .deck:fullscreen .kicker { font-size: .92rem; }
  .deck:fullscreen .card-desc, .deck:fullscreen .row-why { font-size: 1rem; }
  .deck:fullscreen .tri-col li { font-size: 1.02rem; }
  .deck:fullscreen .slide.has-figure .content { font-size: 1.14rem; }
  .deck:fullscreen .slide.has-figure h1 { font-size: 2.4rem; }

  /* Click zones */
  .zone { position: absolute; top: 0; bottom: 56px; width: 19%; cursor: pointer; z-index: 2; }
  .zone-prev { left: 0; }
  .zone-next { right: 0; }

  .bar {
    position: absolute; left: 0; right: 0; bottom: 0; height: 56px; z-index: 5;
    display: flex; align-items: center; justify-content: space-between; padding: 0 22px; gap: 16px;
  }
  .dots { display: flex; gap: 6px; flex-wrap: wrap; }
  .dot {
    width: 8px; height: 8px; border-radius: 50%; cursor: pointer; background: var(--border);
    border: none; padding: 0; transition: all .2s ease;
  }
  .dot:hover { transform: scale(1.3); opacity: .75; }
  .dot.active { width: 24px; border-radius: 4px; }
  .dot-glass.active { background: var(--glass); }
  .dot-metal.active { background: var(--metal); }
  .dot-paper.active { background: var(--paper); }
  .dot-plastic.active { background: var(--plastic); }
  .bar-right { display: flex; align-items: center; gap: 13px; }
  .counter { font-size: .84rem; color: var(--muted); font-variant-numeric: tabular-nums; }
  .fs-btn {
    background: var(--surface); border: 1px solid var(--border); color: var(--muted);
    border-radius: 7px; padding: 5px 11px; font-size: .79rem; cursor: pointer;
  }
  .fs-btn:hover { color: var(--text); }
  .progress { position: absolute; top: 0; left: 0; height: 3px; z-index: 6; background: var(--glass); transition: width .3s ease, background .3s ease; }

  @media (max-width: 980px) {
    .cards, .arch, .tri, .fsplit { flex-direction: column; }
    .row { grid-template-columns: 1fr; gap: 5px; }
    .slide.has-figure { overflow-y: auto; }
    .slide.has-figure .slide-inner { flex-direction: column; height: auto; margin: auto; }
    .split-fig img { max-height: 26vh; }
  }
"""


def _build_css(theme):
    t = THEMES[theme]
    return f"""
<style>
  .deck {{
    --text: {t['text']};
    --muted: {t['muted']};
    --strong: {t['strong']};
    --surface: {t['surface']};
    --surface-alt: {t['surface_alt']};
    --border: {t['border']};
    --watermark: {t['watermark']};
    --img-bg: {t['img_bg']};
    --shadow: {t['shadow']};
    --pos: {t['pos']};
    --neg: {t['neg']};
    --glass: {BIN_COLORS['glass']};
    --metal: {BIN_COLORS['metal']};
    --paper: {BIN_COLORS['paper']};
    --plastic: {BIN_COLORS['plastic']};
    background: {t['bg']};
  }}
{STATIC_CSS}

  /* ── Fit-to-height scaling ───────────────────────────────────────────────
     Everything above sizes type in rem, which is measured against the page
     root and so ignores how much room the deck actually has. Under browser
     zoom the iframe keeps its physical size but loses CSS pixels, so
     rem-sized content overflows and the slide starts scrolling — which is
     what clipped the architecture cards mid-presentation.

     These overrides re-express the main type and spacing in vh, clamped at
     both ends so nothing becomes unreadable or absurd. Because the deck is a
     fixed-height box, 1vh tracks the space actually available, so slides now
     shrink to fit at any zoom level and grow in fullscreen from the same
     rules. They are declared last so they win over the earlier fixed sizes.  */
  .slide {{ padding: clamp(8px, 4.4vh, 46px) clamp(12px, 3.6vw, 60px) clamp(34px, 7.6vh, 78px); }}
  h1 {{
    font-size: clamp(.78rem, 3.5vh, 2.3rem);
    margin: 0 0 clamp(3px, 1.7vh, 20px);
    padding-bottom: clamp(2px, 1vh, 13px);
  }}
  .slide-title h1 {{ font-size: clamp(1.1rem, 6.8vh, 4rem); }}
  .kicker {{ font-size: clamp(.4rem, 1.3vh, .78rem); margin-bottom: clamp(2px, 1.2vh, 13px); }}
  .content {{ font-size: clamp(.48rem, 1.92vh, 1.06rem); }}
  .slide.has-figure .content {{ font-size: clamp(.46rem, 1.75vh, 1rem); }}
  li {{ margin-bottom: clamp(1px, .85vh, 10px); }}
  .note, .caption, .fnote, .foot-notes, .probe-note {{ font-size: clamp(.42rem, 1.55vh, .95rem); margin: clamp(2px,.9vh,12px) 0; }}
  .cards, .rows, .arch, .tri, .bins, .steps, .stats, .tiers, .flow, .fusion {{ gap: clamp(2px, 1.05vh, 13px); }}
  .card, .row, .arch-col, .tri-col, .bin, .step, .fbox, .fnode, .tier, .stat, .callout, .banner {{
    padding: clamp(3px, 1.35vh, 16px) clamp(5px, 1.5vh, 18px);
  }}
  .card-num {{ font-size: clamp(.7rem, 3vh, 1.9rem); }}
  .card-title, .arch-name, .row-name {{ font-size: clamp(.44rem, 1.6vh, .92rem); }}
  .card-desc, .row-why, .row-role, .arch-role, .tri-col li, .bin-where {{
    font-size: clamp(.42rem, 1.55vh, .92rem);
  }}
  .tier-score, .stat-num {{ font-size: clamp(.58rem, 2.2vh, 1.35rem); }}
  .banner {{ font-size: clamp(.5rem, 1.9vh, 1.05rem); }}
  .chip, .pill, .tag, .seg, .fbox, .fnode, .arch-cfg {{ font-size: clamp(.42rem, 1.5vh, .92rem); }}
  .illus {{ max-height: 32vh; }}
  .arrows, .farrow, .step-num {{ font-size: clamp(.5rem, 1.4vh, 1rem); }}
  /* Vertical connectors carry the flow between stages, so make them read as
     arrows rather than stray punctuation. Inline (&rarr;) ones inside a chain
     stay small so they don't crowd the boxes they sit between. */
  .fsplit .farrow, .fbranch > .farrow {{
    font-size: clamp(.85rem, 2.1vh, 1.4rem);
    font-weight: 700;
    color: var(--accent);
    line-height: 1;
  }}
  .farrow.inline {{ font-size: clamp(.55rem, 1.4vh, .95rem); opacity: .85; }}
  table {{ font-size: clamp(.45rem, 1.6vh, 1rem); }}
  td, th {{ padding: clamp(2px, .8vh, 9px) clamp(4px, 1vh, 12px); }}
  .splitbar .seg {{ padding: clamp(4px, 1.4vh, 13px) clamp(4px, 1vh, 10px); }}

  /* Fullscreen simply sits at the upper end of the same clamps. */
  .deck:fullscreen h1 {{ font-size: clamp(1.6rem, 4.3vh, 3rem); }}
  .deck:fullscreen .slide-title h1 {{ font-size: clamp(2.4rem, 8vh, 4.8rem); }}
  .deck:fullscreen .content {{ font-size: clamp(.9rem, 2.2vh, 1.35rem); }}
  .deck:fullscreen .slide.has-figure .content {{ font-size: clamp(.85rem, 2vh, 1.2rem); }}
  .deck:fullscreen .note {{ font-size: clamp(.8rem, 1.8vh, 1.1rem); }}
  .deck:fullscreen .kicker {{ font-size: clamp(.65rem, 1.5vh, .92rem); }}
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
      progress.style.background = getComputedStyle(slides[current]).getPropertyValue('--accent');
      fitSlide(slides[current]);
    }

    // Auto-fit: shrink a slide until it fits the deck.
    //
    // The CSS clamps already scale type with deck height, but content varies a
    // lot from slide to slide -- the architecture slide stacks far more boxes
    // than a bullet slide -- so no single set of clamps fits every slide at
    // every zoom level. This is the backstop: measure the slide, and if it
    // still overflows, step the CSS `zoom` down until it doesn't.
    //
    // `zoom` is used rather than `transform: scale()` on purpose: zoom
    // reflows, so the scrollbar and the flex layout agree with what's on
    // screen, whereas a transform would shrink the pixels but leave the
    // layout box (and the scrollbar) at the old size. Browsers without zoom
    // support simply keep the current behaviour and scroll.
    function fitSlide(slide) {
      var outer = slide.querySelector('.slide-inner');
      var textInner = slide.querySelector('.split-inner');
      var text = slide.querySelector('.split-text');
      if (!outer) { return; }
      outer.style.zoom = '';
      if (textInner) { textInner.style.zoom = ''; }

      function overflowing() {
        if (slide.scrollHeight > slide.clientHeight + 1) { return true; }
        return !!text && text.scrollHeight > text.clientHeight + 1;
      }
      // Floor at 0.42: below that it's unreadable, and scrolling is the
      // better failure mode than microscopic text.
      function shrink(el) {
        for (var z = 0.97; z >= 0.42; z -= 0.025) {
          el.style.zoom = z;
          if (!overflowing()) { return true; }
        }
        return false;
      }

      if (!overflowing()) { return; }
      // On a figure slide, shrink the text column first: the chart is the
      // point of the slide and should stay as large as possible.
      if (textInner && shrink(textInner)) { return; }
      // Not enough on its own -- e.g. once the columns stack on a narrow or
      // heavily zoomed viewport, the figure adds height that shrinking the
      // text can't offset. Scale the whole slide instead.
      // Keep the text column at its floor rather than resetting it, then take
      // the rest out of the slide as a whole.
      shrink(outer);
    }

    // Re-fit on resize, on zoom changes, and when entering/leaving fullscreen.
    var refit = function () { fitSlide(slides[current]); };
    window.addEventListener('resize', refit);
    document.addEventListener('fullscreenchange', function () {
      // Wait for the fullscreen layout to settle before measuring.
      setTimeout(refit, 80);
    });
    if (window.ResizeObserver) { new ResizeObserver(refit).observe(deck); }

    deck.querySelector('.zone-next').addEventListener('click', function () { go(current + 1); });
    deck.querySelector('.zone-prev').addEventListener('click', function () { go(current - 1); });
    dots.forEach(function (dot, i) { dot.addEventListener('click', function () { go(i); }); });

    // Keyboard. The deck has tabindex so it can hold focus inside the iframe;
    // click it once and arrow keys / space / a presenter clicker all work.
    deck.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight' || e.key === 'PageDown' || e.key === ' ') { go(current + 1); e.preventDefault(); }
      else if (e.key === 'ArrowLeft' || e.key === 'PageUp') { go(current - 1); e.preventDefault(); }
      else if (e.key === 'Home') { go(0); e.preventDefault(); }
      else if (e.key === 'End') { go(slides.length - 1); e.preventDefault(); }
      else if (e.key === 'f' || e.key === 'F') { toggleFullscreen(); }
    });
    deck.focus();

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
    slides_html = "".join(_build_slide_html(s, i, theme) for i, s in enumerate(SLIDES))

    dots_html = ""
    for i, slide in enumerate(SLIDES):
        dots_html += (
            '<button class="dot dot-' + slide.get("accent", "glass")
            + (" active" if i == 0 else "")
            + '" title="Slide ' + str(i + 1) + '"></button>'
        )

    return (
        _build_css(theme)
        + '<div class="deck" id="deck" tabindex="0">'
        + '<div class="progress" style="width:0%"></div>'
        + slides_html
        + '<div class="zone zone-prev"></div><div class="zone zone-next"></div>'
        + '<div class="bar"><div class="dots">' + dots_html + "</div>"
        + '<div class="bar-right"><span class="counter">1 / ' + str(len(SLIDES)) + "</span>"
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
