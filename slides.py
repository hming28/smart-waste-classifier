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

To edit the deck, edit SLIDES below. Each slide is a dict:
    "title"    — heading shown at the top of the slide
    "kicker"   — optional small label above the title (section marker)
    "body"     — HTML for the slide content
    "figure"   — optional PNG filename inside FIGURES_DIR, embedded as base64
    "layout"   — optional; "title" for the big centred cover/closing slides
"""

import base64
import os

import streamlit as st
import streamlit.components.v1 as components

# Same folder the Compare tab reads its exported Colab charts from.
FIGURES_DIR = "figures"

# Height of the deck component in pixels. Raise this if your slides get taller.
DECK_HEIGHT = 720


SLIDES = [
    {
        "layout": "title",
        "title": "Smart Waste AI",
        "kicker": "BMCS2074 Artificial Intelligence · 202605 Session",
        "body": """
            <p class="lead">AI-Based Smart Waste Classification Using Computer Vision</p>
            <p class="team">Lee Hao Ming &nbsp;·&nbsp; Goh Jian Hao &nbsp;·&nbsp; Kyra Aerin Leong</p>
        """,
    },
    {
        "kicker": "Introduction",
        "title": "The Problem",
        "body": """
            <ul>
              <li>Recycling is one of the most effective ways to cut pollution &mdash; but it only works if waste is <b>sorted correctly</b>.</li>
              <li>Sorting today relies on manual identification and public knowledge, both inconsistent and error-prone.</li>
              <li>Misclassified recyclables get contaminated, and end up in landfill anyway.</li>
            </ul>
            <div class="callout">
              <b>Our approach:</b> use computer vision to classify a waste photo automatically
              and tell the user which bin it belongs in.
            </div>
        """,
    },
    {
        "kicker": "Introduction",
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
        "title": "Dataset",
        "body": """
            <ul>
              <li>Combined <b>two public Kaggle datasets</b> (Garbage Classification + Garbage
                  Classification 12-Classes) for more images and more visual variation.</li>
              <li>Kept only the 4 recyclable categories, and removed exact duplicates found
                  across the merged sets.</li>
            </ul>
            <div class="chips">
              <span class="chip chip-glass">Glass</span>
              <span class="chip chip-metal">Metal</span>
              <span class="chip chip-paper">Paper</span>
              <span class="chip chip-plastic">Plastic</span>
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
        "title": "Five Approaches, One Test Set",
        "body": """
            <table>
              <tr><th>Approach</th><th>Idea</th></tr>
              <tr><td><b>CNN</b></td><td>Custom convolutional network trained from scratch &mdash; our baseline</td></tr>
              <tr><td><b>MobileNetV2</b></td><td>Lightweight pretrained backbone, fine-tuned</td></tr>
              <tr><td><b>ResNet50</b></td><td>Deeper pretrained backbone, fine-tuned</td></tr>
              <tr><td><b>CLIP (Linear Probe)</b></td><td>Frozen CLIP visual features + a small trained classifier head</td></tr>
              <tr><td><b>Feature Fusion</b></td><td>ResNet50 features combined with general-purpose CLIP features</td></tr>
            </table>
            <div class="callout">
              Every model is evaluated on the <b>same fixed 845-image test split</b>, so the
              comparison is like-for-like.
            </div>
        """,
    },
    {
        "kicker": "Results",
        "title": "Overall Test Accuracy",
        "body": """
            <p class="note">Every number comes from evaluating each model's <i>actual deployed file</i>
            on the shared 845-image test set.</p>
        """,
        "figure": "fig1_overall_accuracy.png",
    },
    {
        "kicker": "Results",
        "title": "Where Each Model Struggles",
        "body": """
            <p class="note">The diagonal is correct predictions &mdash; everything off it is a specific
            error mode, which tells us far more than a single accuracy number.</p>
        """,
        "figure": "fig3_confusion_matrices.png",
    },
    {
        "kicker": "Results",
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
        "title": "Future Work",
        "body": """
            <ul>
              <li>Tune the confidence threshold empirically on the validation set.</li>
              <li>Expand the dataset &mdash; more images, more categories, more real-world lighting and backgrounds.</li>
              <li>Re-test CLIP Verify on a genuinely independent holdout set.</li>
              <li>Standardise random seeds across all five models, and report mean &plusmn; std over repeated runs.</li>
              <li>Extend toward continuous real-time deployment, e.g. a smart bin on a conveyor belt.</li>
              <li>Compare against other fusion strategies &mdash; late fusion, attention-based fusion.</li>
            </ul>
        """,
    },
    {
        "kicker": "Demo",
        "title": "Live Demo",
        "body": """
            <p class="lead">Switching to the app itself &mdash;</p>
            <ul>
              <li><b>🏠 Home</b> &mdash; upload a photo or use Camera Mode, pick a model, see the
                  prediction, confidence breakdown and recycling guidance.</li>
              <li><b>📊 Compare</b> &mdash; the full set of metrics behind the charts you just saw.</li>
            </ul>
            <div class="callout">Please switch to the <b>Home</b> tab now.</div>
        """,
    },
    {
        "layout": "title",
        "title": "Thank You",
        "kicker": "Questions?",
        "body": """
            <p class="team">Lee Hao Ming &nbsp;·&nbsp; Goh Jian Hao &nbsp;·&nbsp; Kyra Aerin Leong</p>
            <p class="note">github.com/hming28/smart-waste-classifier</p>
        """,
    },
]


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
    classes = "slide"
    if slide.get("layout") == "title":
        classes += " slide-title"
    if index == 0:
        classes += " active"

    parts = ['<section class="' + classes + '" data-index="' + str(index) + '">']
    parts.append('<div class="slide-inner">')

    if slide.get("kicker"):
        parts.append('<div class="kicker">' + slide["kicker"] + "</div>")
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
                "<code>04_Visualize_result_model.ipynb</code> and commit it to the repo.</div>"
            )

    parts.append("</div></section>")
    return "".join(parts)


_DECK_CSS = """
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: "Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }
  .deck {
    position: relative;
    height: 700px;
    border-radius: 18px;
    overflow: hidden;
    background: linear-gradient(150deg, #0f2f24 0%, #14432f 45%, #0b2b3a 100%);
    color: #eaf5ef;
    box-shadow: 0 18px 46px rgba(0, 0, 0, 0.28);
    user-select: none;
  }
  .deck:fullscreen { height: 100vh; border-radius: 0; }

  .slide {
    position: absolute;
    inset: 0;
    padding: 46px 62px 74px;
    opacity: 0;
    visibility: hidden;
    transform: translateY(14px);
    transition: opacity .32s ease, transform .32s ease;
    overflow-y: auto;
  }
  .slide.active { opacity: 1; visibility: visible; transform: none; }
  .slide-inner { max-width: 1000px; margin: 0 auto; }

  .slide-title { display: flex; align-items: center; justify-content: center; text-align: center; }
  .slide-title h1 { font-size: 3.4rem; border: none; padding: 0; margin-bottom: .3rem; }
  .slide-title .kicker { justify-content: center; }

  .kicker {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: .78rem;
    letter-spacing: .16em;
    text-transform: uppercase;
    color: #7ee0b0;
    margin-bottom: 14px;
    font-weight: 600;
  }
  h1 {
    font-size: 2.3rem;
    line-height: 1.15;
    margin: 0 0 22px;
    padding-bottom: 14px;
    border-bottom: 2px solid rgba(126, 224, 176, .28);
    font-weight: 700;
  }
  .content { font-size: 1.08rem; line-height: 1.62; }
  ul { padding-left: 20px; margin: 0 0 16px; }
  li { margin-bottom: 11px; }
  b { color: #b9f4d5; font-weight: 700; }
  i { color: #cfe8dc; }
  .lead { font-size: 1.35rem; color: #d6f2e4; margin: 0 0 14px; }
  .team { font-size: 1.05rem; color: #a8cfbd; margin: 10px 0; }
  .note { font-size: .95rem; color: #9fc4b4; margin: 10px 0; }

  .callout {
    margin-top: 18px;
    padding: 15px 20px;
    background: rgba(126, 224, 176, .10);
    border-left: 4px solid #4fd1a1;
    border-radius: 0 10px 10px 0;
    font-size: 1.02rem;
  }

  table { width: 100%; border-collapse: collapse; font-size: 1rem; margin-bottom: 6px; }
  th {
    text-align: left; padding: 9px 12px;
    color: #7ee0b0; font-size: .78rem;
    letter-spacing: .1em; text-transform: uppercase;
    border-bottom: 1px solid rgba(126, 224, 176, .3);
  }
  td { padding: 9px 12px; border-bottom: 1px solid rgba(255, 255, 255, .07); }

  .chips { display: flex; gap: 10px; flex-wrap: wrap; margin: 16px 0; }
  .chip {
    padding: 7px 18px; border-radius: 999px;
    font-weight: 600; font-size: .95rem; color: #0d2a1f;
  }
  .chip-glass { background: #2ecc71; }
  .chip-metal { background: #3498db; }
  .chip-paper { background: #9b59b6; color: #fff; }
  .chip-plastic { background: #f39c12; }

  .stats { display: flex; gap: 14px; flex-wrap: wrap; margin-top: 14px; }
  .stat {
    flex: 1; min-width: 130px;
    background: rgba(255, 255, 255, .06);
    border: 1px solid rgba(126, 224, 176, .18);
    border-radius: 12px; padding: 14px 18px;
  }
  .stat-num { display: block; font-size: 1.7rem; font-weight: 700; color: #7ee0b0; }
  .stat-label { display: block; font-size: .82rem; color: #9fc4b4; margin-top: 2px; }

  .figure { margin-top: 14px; text-align: center; }
  .figure img {
    max-width: 100%; max-height: 400px;
    border-radius: 10px; background: #fff; padding: 10px;
  }
  .figure.missing {
    padding: 26px; border: 1px dashed rgba(126, 224, 176, .4);
    border-radius: 12px; color: #9fc4b4; font-size: .95rem; text-align: left;
  }
  code { background: rgba(0, 0, 0, .3); padding: 2px 6px; border-radius: 4px; font-size: .88em; }

  /* Click zones — left third goes back, right third goes forward. */
  .zone { position: absolute; top: 0; bottom: 58px; width: 22%; cursor: pointer; z-index: 2; }
  .zone-prev { left: 0; }
  .zone-next { right: 0; }

  .bar {
    position: absolute; left: 0; right: 0; bottom: 0; height: 58px; z-index: 3;
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 22px; gap: 16px;
    background: linear-gradient(to top, rgba(0, 0, 0, .34), transparent);
  }
  .dots { display: flex; gap: 7px; flex-wrap: wrap; }
  .dot {
    width: 9px; height: 9px; border-radius: 50%; cursor: pointer;
    background: rgba(255, 255, 255, .26); border: none; padding: 0;
    transition: all .2s ease;
  }
  .dot:hover { background: rgba(255, 255, 255, .55); transform: scale(1.25); }
  .dot.active { background: #4fd1a1; width: 24px; border-radius: 5px; }
  .bar-right { display: flex; align-items: center; gap: 14px; }
  .counter { font-size: .85rem; color: #9fc4b4; font-variant-numeric: tabular-nums; }
  .fs-btn {
    background: rgba(255, 255, 255, .1); border: 1px solid rgba(255, 255, 255, .16);
    color: #cfe8dc; border-radius: 7px; padding: 5px 11px;
    font-size: .8rem; cursor: pointer;
  }
  .fs-btn:hover { background: rgba(255, 255, 255, .2); }

  .progress {
    position: absolute; top: 0; left: 0; height: 3px; z-index: 4;
    background: linear-gradient(90deg, #4fd1a1, #7ee0b0);
    transition: width .3s ease;
  }
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


def build_deck_html():
    """Assemble the whole deck into one HTML string."""
    slides_html = "".join(_build_slide_html(s, i) for i, s in enumerate(SLIDES))
    dots_html = "".join(
        '<button class="dot' + (" active" if i == 0 else "") + '" title="Slide '
        + str(i + 1) + '"></button>'
        for i in range(len(SLIDES))
    )

    return (
        _DECK_CSS
        + '<div class="deck" id="deck" tabindex="0">'
        + '<div class="progress" style="width:0%"></div>'
        + slides_html
        + '<div class="zone zone-prev"></div><div class="zone zone-next"></div>'
        + '<div class="bar">'
        + '<div class="dots">' + dots_html + "</div>"
        + '<div class="bar-right">'
        + '<span class="counter">1 / ' + str(len(SLIDES)) + "</span>"
        + '<button class="fs-btn">⛶ Fullscreen</button>'
        + "</div></div></div>"
        + _DECK_JS
    )


def render_slides():
    """Drop the deck into the current Streamlit container."""
    st.caption(
        "Click the deck, then use ← / → (or a presenter clicker) to navigate. "
        "You can also click the left/right edges, jump with the dots, or press F for fullscreen."
    )
    components.html(build_deck_html(), height=DECK_HEIGHT, scrolling=False)
