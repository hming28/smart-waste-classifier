import streamlit as st
import numpy as np
from PIL import Image
import tensorflow as tf

# Page config
st.set_page_config(
    page_title="Smart Waste AI",
    page_icon="♻️",
    layout="centered"
)

# Class names
CLASS_NAMES = ["glass", "metal", "paper", "plastic"]

# Recycling info
RECYCLE_INFO = {
    "glass": {
        "bin": "Green Bin",
        "color": "#2ecc71",
        "icon": "🍾",
        "description": "Glass bottles and jars are 100% recyclable. Rinse before recycling.",
        "tip": "Do not break glass before recycling.",
    },
    "metal": {
        "bin": "Metal Recycling Bin",
        "color": "#3498db",
        "icon": "🥫",
        "description": "Aluminum cans, tin cans, and metal containers are recyclable. Rinse clean.",
        "tip": "Crush cans to save space.",
    },
    "paper": {
        "bin": "Blue Bin",
        "color": "#9b59b6",
        "icon": "📄",
        "description": "Newspapers, magazines, cardboard, and office paper are recyclable. Keep dry.",
        "tip": "Remove plastic windows from envelopes.",
    },
    "plastic": {
        "bin": "Yellow Bin",
        "color": "#f39c12",
        "icon": "🧴",
        "description": "Plastic bottles and containers (check recycling number). Rinse before recycling.",
        "tip": "Check the number on the bottom — #1 and #2 are most recyclable.",
    },
}


# Load model with compatibility fix
def load_model_compat(path):
    import h5py, json, shutil, tempfile, os

    def strip_quantization_config(config):
        if isinstance(config, dict):
            config.pop("quantization_config", None)
            for key in list(config.keys()):
                if isinstance(config[key], list):
                    for item in config[key]:
                        strip_quantization_config(item)
                elif isinstance(config[key], dict):
                    strip_quantization_config(config[key])
        return config

    tmp = tempfile.mktemp(suffix=".h5")
    shutil.copy(path, tmp)

    with h5py.File(tmp, "r+") as f:
        model_config = json.loads(f.attrs["model_config"])
        strip_quantization_config(model_config)
        f.attrs["model_config"] = json.dumps(model_config)

    model = tf.keras.models.load_model(tmp, compile=False)
    os.remove(tmp)
    return model


@st.cache_resource
def load_model():
    return load_model_compat("cnn_garbage_classifier_4class.h5")


model = load_model()

# Custom CSS
st.markdown("""
<style>
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        text-align: center;
        color: #2c3e50;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        text-align: center;
        color: #7f8c8d;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    .prediction-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 16px;
        padding: 2rem;
        color: white;
        text-align: center;
        margin: 1rem 0;
    }
    .prediction-label {
        font-size: 1rem;
        opacity: 0.9;
    }
    .prediction-value {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0.5rem 0;
    }
    .confidence-bar {
        background: rgba(255,255,255,0.3);
        border-radius: 10px;
        height: 12px;
        overflow: hidden;
        margin: 0.5rem 0;
    }
    .confidence-fill {
        height: 100%;
        border-radius: 10px;
        background: white;
    }
    .info-card {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 0.5rem 0;
        border-left: 4px solid;
    }
</style>
""", unsafe_allow_html=True)

# Tabs
tab_home, tab_about = st.tabs(["🏠 Home", "ℹ️ About"])

with tab_home:
    st.markdown('<div class="main-title">♻️ Smart Waste Classification</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">AI-Powered Waste Sorting Assistant</div>', unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Upload a photo of waste",
        type=["jpg", "jpeg", "png", "webp"],
        help="Supported formats: JPG, PNG, WebP"
    )

    if uploaded_file is not None:
        image = Image.open(uploaded_file).convert("RGB")
        st.image(image, caption="Uploaded Image", use_container_width=True)

        img_resized = image.resize((224, 224))
        img_array = np.array(img_resized) / 255.0
        img_array = np.expand_dims(img_array, axis=0)

        with st.spinner("AI Detecting..."):
            predictions = model.predict(img_array, verbose=0)
            pred_index = np.argmax(predictions[0])
            pred_class = CLASS_NAMES[pred_index]
            confidence = float(predictions[0][pred_index]) * 100

        info = RECYCLE_INFO[pred_class]

        st.markdown(f"""
        <div class="prediction-card">
            <div class="prediction-label">Prediction</div>
            <div class="prediction-value">{info['icon']} {pred_class.title()}</div>
            <div class="confidence-bar">
                <div class="confidence-fill" style="width: {confidence}%"></div>
            </div>
            <div class="prediction-label">Confidence: {confidence:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)

        st.subheader("📊 All Probabilities")
        probs = {CLASS_NAMES[i]: float(predictions[0][i]) * 100 for i in range(len(CLASS_NAMES))}
        sorted_probs = dict(sorted(probs.items(), key=lambda x: x[1], reverse=True))
        for cls, prob in sorted_probs.items():
            st.progress(prob / 100, text=f"{cls.title()}: {prob:.1f}%")

        st.subheader("♻️ Recycling Guide")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="info-card" style="border-color: {info['color']}">
                <strong>Bin:</strong> {info['bin']}<br>
                <strong>Description:</strong> {info['description']}
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="info-card" style="border-color: {info['color']}">
                <strong>Tip:</strong> {info['tip']}
            </div>
            """, unsafe_allow_html=True)

    else:
        st.info("📷 Upload a photo of waste (glass, metal, paper, or plastic) to get started.")
        st.subheader("Supported Categories")
        cols = st.columns(4)
        for i, (cls, info) in enumerate(RECYCLE_INFO.items()):
            with cols[i]:
                st.markdown(f"""
                <div style="text-align:center; padding:1rem; background:#f8f9fa; border-radius:12px;">
                    <div style="font-size:2rem;">{info['icon']}</div>
                    <div style="font-weight:600; font-size:1.1rem;">{cls.title()}</div>
                </div>
                """, unsafe_allow_html=True)

with tab_about:
    st.markdown("## About Smart Waste AI")
    st.markdown("""
    ### What is this?
    AI-powered waste classification system. Upload a photo, and the AI identifies the waste type and guides proper disposal.

    ### How does it work?
    - **CNN (Convolutional Neural Network)** trained on waste images
    - Classifies into 4 categories: **Glass, Metal, Paper, Plastic**
    - Provides confidence scores for each category

    ### Supported Waste Types
    | Category | Examples |
    |----------|----------|
    | 🍾 Glass | Bottles, jars, windows |
    | 🥫 Metal | Cans, foil, containers |
    | 📄 Paper | Newspapers, cardboard, books |
    | 🧴 Plastic | Bottles, containers, packaging |

    ### Team
    Built for AI Course Assignment 🎓
    """)
