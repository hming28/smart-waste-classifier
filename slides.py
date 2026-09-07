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

# Darker versions of the same four hues, for TEXT on a light background. The
# bright colours above are tuned for shapes and bars against a dark surface;
# used as body text on beige they'd be too low-contrast to read from the back
# of a room (amber especially). Each theme picks which set its accent text uses.
BIN_TEXT_DARK = {
    "glass": "#1a7a45",
    "metal": "#1c5f8f",
    "paper": "#7333a0",
    "plastic": "#a1650a",
}

THEMES = {
    # Default. Warm beige "recycled paper" surface — easy on the eyes, and it
    # survives a washed-out projector far better than a dark background does.
    # "accent_mode" picks which of the two colour sets above is used for TEXT.
    "beige": {
        "bg": "linear-gradient(155deg, #faf6ed 0%, #f4eee0 55%, #efe8da 100%)",
        "text": "#33302a",
        "muted": "#777064",
        "strong": "#1a1814",
        "surface": "rgba(90, 72, 42, .065)",
        "border": "rgba(90, 72, 42, .16)",
        "watermark": "rgba(90, 72, 42, .05)",
        "img_bg": "#ffffff",
        "accent_mode": "dark",
        "pos": "#1a7a45",
        "neg": "#c0392b",
    },
    # Cooler light option, if beige reads too warm on your projector.
    "recycle_light": {
        "bg": "linear-gradient(155deg, #f8fbf9 0%, #eff4f1 55%, #eaf0f4 100%)",
        "text": "#1d2b26",
        "muted": "#5d7169",
        "strong": "#0f1a16",
        "surface": "rgba(0, 0, 0, .04)",
        "border": "rgba(0, 0, 0, .11)",
        "watermark": "rgba(0, 0, 0, .045)",
        "img_bg": "#ffffff",
        "accent_mode": "dark",
        "pos": "#1a7a45",
        "neg": "#c0392b",
    },
    # Original dark slate version, kept as an option.
    "recycle": {
        "bg": "linear-gradient(155deg, #14231f 0%, #10201c 40%, #131d26 100%)",
        "text": "#eef4f0",
        "muted": "#93aaa1",
        "strong": "#ffffff",
        "surface": "rgba(255, 255, 255, .055)",
        "border": "rgba(255, 255, 255, .10)",
        "watermark": "rgba(255, 255, 255, .028)",
        "img_bg": "#ffffff",
        "accent_mode": "bright",
        "pos": "#4ade80",
        "neg": "#f87171",
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
        "accent_mode": "bright",
        "pos": "#4ade80",
        "neg": "#f87171",
    },
}

ACTIVE_THEME = "beige"


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
            <ul>
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
              <div class="bin bin-glass"><span class="bin-icon">&#127870;</span><span class="bin-name">Glass</span><span class="bin-where">Green bin &middot; 1,147 imgs</span></div>
              <div class="bin bin-metal"><span class="bin-icon">&#129387;</span><span class="bin-name">Metal</span><span class="bin-where">Metal recycling &middot; 1,210</span></div>
              <div class="bin bin-paper"><span class="bin-icon">&#128196;</span><span class="bin-name">Paper</span><span class="bin-where">Blue bin &middot; 1,726</span></div>
              <div class="bin bin-plastic"><span class="bin-icon">&#129508;</span><span class="bin-name">Plastic</span><span class="bin-where">Yellow bin &middot; 1,546</span></div>
            </div>
            <p class="note">Stratified <b>70 / 15 / 15</b> split across <b>5,629 images</b>, fixed once as
            CSV files and reused by every model &mdash; so all five are judged on identical data:</p>
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
            <p class="note">The five models fall into <b>three tiers</b>, not a clean five-way ranking:</p>
            <div class="tiers">
              <div class="tier">
                <span class="tier-score">97.16 / 96.80%</span>
                <span class="tier-body">
                  <span class="tier-name">ResNet50 &amp; Feature Fusion</span>
                  <span class="tier-note">Separated by 0.36 pp &mdash; that's 3 images out of 845.</span>
                </span>
              </div>
              <div class="tier">
                <span class="tier-score">92.66%</span>
                <span class="tier-body">
                  <span class="tier-name">MobileNetV2</span>
                  <span class="tier-note">Clearly behind the top pair, but far smaller and faster.</span>
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
            <ul>
              <li><b>Pretraining is what matters most.</b> ResNet50 beats our from-scratch CNN by
                  <b>6.75 pp</b> &mdash; the single biggest gap in the whole study.</li>
              <li><b>CLIP never saw a waste image</b> during training, yet its frozen features match
                  a CNN trained directly on our data.</li>
              <li>Gaps inside a tier are <b>too small to rank</b> on 845 images &mdash; we report them
                  as an observed advantage on this split, not a verdict.</li>
            </ul>
        """,
        "figure": "fig1_overall_accuracy.png",
    },
    {
        "kicker": "Results",
        "accent": "plastic",
        "title": "The Errors Are Not Random",
        "body": """
            <p class="note">The diagonal is correct predictions. What's off it turns out to be the
            same mistake in every model:</p>
            <ul>
              <li><b>Paper is easiest</b> for every model &mdash; matte, opaque, printed texture gives
                  stable visual features.</li>
              <li><b>Glass and Plastic are hardest</b>, in <b>every</b> architecture. They're
                  transparent and reflective, so what the model sees depends on the background and
                  lighting behind the item.</li>
              <li>The biggest single error is <b>directional</b>, not a symmetric mix-up:
                  <b>Glass predicted as Plastic</b> &mdash; from 6 images in ResNet50 up to 25 in the
                  CLIP Linear Probe. The reverse error is always smaller.</li>
              <li>Half of ResNet50's <b>most confident</b> errors come from Glass alone &mdash; so it
                  isn't just uncertainty, the model is sometimes <b>confidently wrong</b>.</li>
            </ul>
            <div class="callout">
              Because the pattern shows up in the weakest and the strongest model alike, it points at
              the <b>materials</b>, not the architecture.
            </div>
        """,
        "figure": "fig3_confusion_matrices.png",
    },
    {
        "kicker": "Results",
        "accent": "paper",
        "title": "Does CLIP Verify Actually Help?",
        "body": """
            <p class="note">When the primary model's confidence falls below 90%, the prediction is
            handed to the CLIP Linear Probe instead. The effect <b>depends entirely on which model
            you start from</b>:</p>
            <table>
              <tr>
                <th>Primary model</th>
                <th class="num">Standalone</th>
                <th class="num">Gated</th>
                <th class="num">Change</th>
              </tr>
              <tr>
                <td>CNN</td><td class="num">90.41%</td><td class="num">92.43%</td>
                <td class="num"><span class="up">+2.02 pp</span></td>
              </tr>
              <tr>
                <td>MobileNetV2</td><td class="num">92.66%</td><td class="num">94.32%</td>
                <td class="num"><span class="up">+1.66 pp</span></td>
              </tr>
              <tr class="highlight">
                <td>ResNet50</td><td class="num">97.16%</td><td class="num">96.21%</td>
                <td class="num"><span class="down">&minus;0.95 pp</span></td>
              </tr>
            </table>
            <ul>
              <li>It <b>helps the weaker models</b> &mdash; their low-confidence predictions really were
                  often wrong, so CLIP had room to correct them.</li>
              <li>It <b>hurts the strongest model</b>. ResNet50 unsure is still usually more right than
                  CLIP, so replacing those predictions loses accuracy.</li>
              <li>Crucially, <b>no gated combination beats ResNet50 alone</b> (97.16%) &mdash; verification
                  raises the weak models, but never the ceiling.</li>
            </ul>
            <div class="callout">
              <b>The lesson:</b> adding a second model is not automatically an improvement. It has to be
              better <i>precisely where the first one is unsure</i>.
            </div>
        """,
        "figure": "fig8_clip_verify_effect.png",
    },
    {
        "kicker": "Results",
        "accent": "metal",
        "title": "Is the Fusion Model Actually Better?",
        "body": """
            <p class="note">Our proposed approach came second on raw accuracy. But accuracy at one
            fixed threshold isn't the whole picture:</p>
            <ul>
              <li>On <b>ROC / AUC</b>, fusion is the <b>strongest overall</b>: highest for Paper
                  (<b>1.000</b>) and Plastic (<b>0.997</b>), tied on Glass (0.994), and behind on Metal
                  by just 0.001.</li>
              <li>It beat ResNet50's <b>Paper F1</b> (0.990 vs 0.987) while losing on Glass, Metal and
                  Plastic &mdash; <b>complementary</b> behaviour, not uniformly better or worse.</li>
              <li>Why? CLIP was trained on general internet images, so it helps for classes with a
                  strong everyday visual concept like paper, and helps less where the decision needs
                  <b>fine-grained material texture</b> &mdash; exactly what ResNet50's filters already learn.</li>
            </ul>
            <div class="callout">
              <b>Our honest conclusion:</b> feature-level fusion is <b>technically feasible and trains
              stably</b>, and it produces genuinely different error patterns &mdash; but on this dataset it
              is a <b>trade-off, not a clear win</b>.
            </div>
        """,
        "figure": "fig4_roc_curves.png",
    },
    {
        "kicker": "Conclusion",
        "accent": "glass",
        "title": "Achievements",
        "body": """
            <ul>
              <li>Built a <b>working end-to-end prototype</b>, deployed on Streamlit Community Cloud.</li>
              <li>Implemented and fairly compared <b>five approaches</b> on one shared test set &mdash;
                  same split, same preprocessing, same evaluation.</li>
              <li>Went beyond headline accuracy: <b>per-class F1, confusion matrices, ROC/AUC</b> and
                  a confident-error analysis.</li>
              <li>Identified a <b>reproducible failure mode</b> (Glass &rarr; Plastic) present in every
                  architecture, and explained <b>why</b> it happens.</li>
              <li>Showed feature-level fusion is <b>feasible</b>, and reported the trade-off honestly
                  rather than claiming a win.</li>
            </ul>
            <div class="stats">
              <div class="stat"><span class="stat-num">97.16%</span><span class="stat-label">ResNet50 &mdash; best</span></div>
              <div class="stat"><span class="stat-num">96.80%</span><span class="stat-label">Feature Fusion</span></div>
              <div class="stat"><span class="stat-num">5</span><span class="stat-label">Models compared</span></div>
              <div class="stat"><span class="stat-num">845</span><span class="stat-label">Shared test images</span></div>
            </div>
        """,
    },
    {
        "kicker": "Conclusion",
        "accent": "plastic",
        "title": "Limitations",
        "body": """
            <ul>
              <li>The 90% threshold was a <b>design choice, not tuned</b> on the validation set &mdash;
                  a different cutoff could change the CLIP Verify result entirely.</li>
              <li><b>845 test images</b> is small: the 0.36 pp top-pair gap is 3 images, so we can't
                  claim one model is definitively better.</li>
              <li>Only <b>4 categories under controlled conditions</b>; real waste is dirty, damaged,
                  overlapping and mixed with non-recyclables.</li>
              <li>Classification runs on a <b>single snapshot</b>, not a continuous video stream.</li>
              <li>CLIP Verify was measured on the <b>same test set</b> as the base models &mdash; an
                  exploratory secondary analysis, not a clean holdout result.</li>
              <li><b>Seeds fixed only for ResNet50 and Fusion</b>, so CNN, MobileNetV2 and CLIP Linear
                  Probe figures are single runs and not exactly reproducible.</li>
            </ul>
        """,
    },
    {
        "kicker": "Conclusion",
        "accent": "metal",
        "title": "Future Work",
        "body": """
            <ul>
              <li><b>Tune the confidence threshold</b> empirically on the validation set.</li>
              <li><b>Expand the dataset</b> &mdash; more images, more categories, and more real-world
                  lighting and backgrounds, targeting the <b>Glass / Plastic confusion</b> directly.</li>
              <li>Re-test CLIP Verify on a genuinely <b>independent holdout set</b>.</li>
              <li><b>Standardise random seeds</b> across all five models, and report mean &plusmn; std over repeated runs.</li>
              <li><b>Close the loop back to IoT</b> &mdash; put this model on the bin itself, classifying
                  items continuously instead of one snapshot at a time.</li>
              <li>Compare against <b>other fusion strategies</b> &mdash; late fusion, attention-based fusion.</li>
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


def _build_slide_html(slide, index, theme):
    """Render one slide dict into its <section> markup.

    Two accent vars are set: --accent for shapes/rules/borders (always the
    bright bin colour) and --accent-text for bold text, which switches to a
    darker shade on light themes so it stays readable."""
    accent_name = slide.get("accent", "glass")
    accent = BIN_COLORS.get(accent_name, BIN_COLORS["glass"])
    if THEMES[theme].get("accent_mode") == "dark":
        accent_text = BIN_TEXT_DARK.get(accent_name, BIN_TEXT_DARK["glass"])
    else:
        accent_text = accent

    has_figure = bool(slide.get("figure"))

    classes = "slide"
    if slide.get("layout") == "title":
        classes += " slide-title"
    if has_figure:
        classes += " has-figure"
    if index == 0:
        classes += " active"

    parts = [
        '<section class="' + classes + '" data-index="' + str(index)
        + '" style="--accent:' + accent + ';--accent-text:' + accent_text + '">'
    ]
    parts.append('<div class="slide-inner">')

    # With a figure the slide splits into two columns, so the heading and body
    # get wrapped in their own column rather than sitting above the chart.
    if has_figure:
        parts.append('<div class="split-text">')

    if slide.get("kicker"):
        parts.append('<div class="kicker"><span class="kicker-dot"></span>' + slide["kicker"] + "</div>")
    parts.append("<h1>" + slide["title"] + "</h1>")
    parts.append('<div class="content">' + slide.get("body", "") + "</div>")

    if has_figure:
        parts.append("</div>")  # /split-text
        uri = _figure_data_uri(slide["figure"])
        if uri:
            parts.append(
                '<div class="split-fig"><img src="' + uri
                + '" alt="' + slide["figure"] + '"></div>'
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
    --pos: {t['pos']};
    --neg: {t['neg']};
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

  /* Four-colour ribbon removed — the per-slide accent carries the recycling
     identity on its own, without eating horizontal space. */

  /* Flex column with auto margins on the inner block: content sits centred
     vertically at any deck height. This is what fixes fullscreen — the deck
     grows to 100vh, and without centring everything stayed pinned to the top
     with a large dead area underneath. Auto margins (rather than
     justify-content: center) also mean a slide taller than the viewport still
     scrolls from its top instead of having the top clipped off. */
  .slide {{
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    padding: 42px 58px 74px;
    opacity: 0;
    visibility: hidden;
    transform: translateY(14px);
    transition: opacity .32s ease, transform .32s ease;
    overflow-y: auto;
    z-index: 1;
  }}
  .slide.active {{ opacity: 1; visibility: visible; transform: none; }}
  .slide-inner {{ max-width: 1000px; width: 100%; margin: auto; }}

  /* Slides that carry a chart use a two-column layout: text on the left,
     figure on the right, both sized to the slide instead of stacking. Stacked
     vertically these slides overflowed and forced scrolling to reach the
     chart, which is useless mid-presentation. min-height: 0 on the flex
     children is what lets them actually shrink to fit rather than pushing
     past the bottom edge. */
  .slide.has-figure {{ overflow: hidden; }}
  .slide.has-figure .slide-inner {{
    display: flex; flex-direction: row; align-items: stretch;
    gap: 30px; max-width: 1440px; height: 100%; margin: 0 auto;
  }}
  .split-text {{
    flex: 1 1 50%; min-height: 0; overflow-y: auto;
    display: flex; flex-direction: column;
    /* "safe" centring: centres when there's room, but falls back to top
       alignment when the column overflows, instead of clipping the heading
       off the top. Browsers without support drop this and default to
       flex-start, which is the same safe behaviour. */
    justify-content: safe center;
  }}
  .split-fig {{
    flex: 1 1 50%; min-height: 0;
    display: flex; align-items: center; justify-content: center;
  }}
  .split-fig img {{
    max-width: 100%; max-height: 100%;
    width: auto; height: auto; object-fit: contain;
    border-radius: 10px; background: {t['img_bg']}; padding: 10px;
  }}
  /* Figure slides run a little tighter so the text column fits without scrolling. */
  .slide.has-figure .content {{ font-size: 1rem; line-height: 1.52; }}
  .slide.has-figure h1 {{ font-size: 1.95rem; margin-bottom: 14px; }}
  .slide.has-figure li {{ margin-bottom: 7px; }}
  .slide.has-figure .tier {{ padding: 8px 14px; }}
  .slide.has-figure table {{ font-size: .93rem; }}
  .slide.has-figure td, .slide.has-figure th {{ padding: 6px 9px; }}
  .deck:fullscreen .slide.has-figure .content {{ font-size: 1.2rem; }}
  .deck:fullscreen .slide.has-figure h1 {{ font-size: 2.5rem; }}

  /* Narrow viewport (phone / small window): stack instead of squeezing. */
  @media (max-width: 900px) {{
    .slide.has-figure {{ overflow-y: auto; }}
    .slide.has-figure .slide-inner {{ flex-direction: column; height: auto; margin: auto; }}
    .split-fig img {{ max-height: 300px; }}
  }}

  /* Fullscreen: scale type up for projector distance. */
  .deck:fullscreen .slide {{ padding: 54px 84px 84px; }}
  .deck:fullscreen .slide-inner {{ max-width: 1240px; }}
  .deck:fullscreen h1 {{ font-size: 3rem; }}
  .deck:fullscreen .slide-title h1 {{ font-size: 4.6rem; }}
  .deck:fullscreen .content {{ font-size: 1.35rem; }}
  .deck:fullscreen .note {{ font-size: 1.15rem; }}
  .deck:fullscreen .kicker {{ font-size: .95rem; }}
  .deck:fullscreen .figure img {{ max-height: 56vh; }}

  .slide-title {{ text-align: center; }}
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
  /* Bold takes the slide's accent colour — key terms read as highlights
     rather than just heavier text, which is much easier to scan. */
  b {{ color: var(--accent-text); font-weight: 700; }}
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

  table {{ width: 100%; border-collapse: collapse; font-size: 1rem; margin: 6px 0 10px; }}
  th {{
    text-align: left; padding: 9px 12px;
    color: var(--accent-text); font-size: .76rem;
    letter-spacing: .1em; text-transform: uppercase;
    border-bottom: 2px solid var(--accent);
  }}
  td {{ padding: 9px 12px; border-bottom: 1px solid var(--border); }}
  th.num, td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  tr.highlight td {{ background: var(--surface); font-weight: 700; }}
  .up {{ color: var(--pos); font-weight: 700; }}
  .down {{ color: var(--neg); font-weight: 700; }}

  /* Grouped result bands — the three performance tiers. */
  .tiers {{ display: flex; flex-direction: column; gap: 9px; margin: 12px 0; }}
  .tier {{
    display: flex; align-items: baseline; gap: 16px;
    padding: 11px 17px; border-radius: 10px;
    background: var(--surface); border-left: 4px solid var(--accent);
  }}
  .tier-score {{
    font-size: 1.2rem; font-weight: 700; color: var(--accent-text);
    min-width: 104px; font-variant-numeric: tabular-nums;
  }}
  .tier-body {{ flex: 1; }}
  .tier-name {{ font-weight: 700; color: var(--strong); }}
  .tier-note {{ font-size: .9rem; color: var(--muted); }}

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
  .zone-prev {{ left: 0; }}
  .zone-next {{ right: 0; }}

  .bar {{
    position: absolute; left: 0; right: 0; bottom: 0; height: 58px; z-index: 5;
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 22px; gap: 16px;
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
    slides_html = "".join(_build_slide_html(s, i, theme) for i, s in enumerate(SLIDES))

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
