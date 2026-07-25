import os
import cv2
import streamlit as st
import numpy as np
from PIL import Image
import tensorflow as tf
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input as mobilenet_preprocess
from tensorflow.keras.applications.resnet50 import preprocess_input as resnet_preprocess

# Page config
st.set_page_config(
    page_title="Smart Waste AI",
    page_icon="♻️",
    layout="wide"
)

# Class names — all models output in alphabetical order: glass, metal, paper, plastic
CLASS_NAMES = ["glass", "metal", "paper", "plastic"]

# Model config
MODELS = {
    "CNN": "AdvancedCNN_none_classweight.keras",
    "MobileNetV2": "mobilenetv2_garbage_classifier_4class.keras",
    "ResNet50": "resnet50_model_quantized.tflite",
}

# Each model was trained with a different input normalization
PREPROCESS_FUNCS = {
    "CNN": lambda arr: arr / 255.0,              # AdvancedCNN: rescale=1./255
    "MobileNetV2": mobilenet_preprocess,          # scales to [-1, 1]
    "ResNet50": resnet_preprocess,                # ImageNet mean-subtraction
}

# ---------------------------------------------------------------------------
# Image treatment pipeline (A = original, B = object crop, C = background removal).
#
# CRITICAL: this must match whatever pipeline actually produced the model file
# listed in MODELS above — not what you *wish* it were trained with. Applying
# crop/background-removal to a model that was trained on plain Method-A images
# creates a NEW train/inference mismatch, the same bug this config exists to fix.
#
# Update the value here ONLY when you swap in a model file that was actually
# retrained on that treatment's processed images.
# ---------------------------------------------------------------------------
IMAGE_PROCESSING = {
    "CNN": "A",
    "MobileNetV2": "A",   # change to "B" only once the .keras file above is the Method-B-trained checkpoint
    "ResNet50": "A",
}


def crop_with_margin(img_array: np.ndarray, margin_ratio: float = 0.1) -> np.ndarray:
    """Crop tightly around the main object (Otsu threshold + largest contour),
    with a margin so the object edge isn't cut off. Falls back to the original
    image if no contour is found, so a bad photo never crashes the app."""
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return img_array

    largest = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(largest)

    mx, my = int(w * margin_ratio), int(h * margin_ratio)
    x1, y1 = max(0, x - mx), max(0, y - my)
    x2, y2 = min(img_array.shape[1], x + w + mx), min(img_array.shape[0], y + h + my)

    cropped = img_array[y1:y2, x1:x2]
    return cropped if cropped.size > 0 else img_array


def apply_image_processing(img_array: np.ndarray, mode: str) -> np.ndarray:
    """Route to the treatment this specific model was actually trained with."""
    if mode == "B":
        return crop_with_margin(img_array)
    if mode == "C":
        # Not wired up yet — implement once a Method-C-trained model file exists,
        # using the same rembg + neutral-background logic as the training notebook.
        raise NotImplementedError("Method C (background removal) isn't available yet.")
    return img_array  # Method A — no change

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
    # .tflite files use TFLite interpreter
    if path.endswith(".tflite"):
        interpreter = tf.lite.Interpreter(model_path=path)
        interpreter.allocate_tensors()
        return interpreter

    # .keras files load directly
    if path.endswith(".keras"):
        return tf.keras.models.load_model(path, compile=False)

    # .h5 files need quantization_config fix
    import h5py, json, shutil, tempfile

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


def predict_with_model(model, img_array):
    # TFLite interpreter
    if isinstance(model, tf.lite.Interpreter):
        input_details = model.get_input_details()
        output_details = model.get_output_details()
        # Cast to whatever dtype this specific .tflite file actually expects.
        # NOTE: if this file was created with full-integer quantization, it may expect
        # raw uint8 [0,255] input instead of the preprocessed float array — check the
        # conversion script that produced resnet50_model_quantized.tflite to confirm.
        input_dtype = input_details[0]['dtype']
        model.set_tensor(input_details[0]['index'], img_array.astype(input_dtype))
        model.invoke()
        return model.get_tensor(output_details[0]['index'])
    # Keras model
    return model.predict(img_array, verbose=0)


@st.cache_resource
def load_model(path):
    return load_model_compat(path)


# Custom CSS
st.markdown("""
<style>
    .stMainBlockContainer {
        padding-top: 30px !important;
    }
    .prediction-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 16px;
        padding: 2rem;
        color: white;
        text-align: center;
        margin: 1rem 0;
    }
    [data-theme="dark"] .prediction-card {
        background: linear-gradient(135deg, #4a5acf 0%, #5a3d8a 100%);
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
        background: var(--secondary-background-color);
        color: var(--text-color);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 0.5rem 0;
        border-left: 4px solid;
    }
    .model-unavailable {
        color: #e74c3c;
        font-size: 0.8rem;
    }
    [data-theme="dark"] .stProgress > div > div > div > div {
        background-color: var(--text-color);
    }
</style>
""", unsafe_allow_html=True)

# Tabs
tab_home, tab_about = st.tabs(["🏠 Home", "ℹ️ About"])

with tab_home:
    # Left-right layout
    col_left, col_right = st.columns([1, 1])

    with col_left:
        # Model selector (segmented control)
        st.markdown("**Select Model**")
        model_labels = []
        model_files = {}
        for name, filename in MODELS.items():
            available = os.path.exists(filename)
            model_files[name] = available
            if available:
                model_labels.append(name)
            else:
                model_labels.append(f"{name} (Not trained)")

        selected_model_label = st.segmented_control(
            "Model",
            model_labels,
            label_visibility="collapsed",
            default="ResNet50",
        )

        selected_model = selected_model_label.replace(" (Not trained)", "") if selected_model_label else "ResNet50"
        model_available = model_files.get(selected_model, False)

        # Upload photo
        uploaded_file = st.file_uploader(
            "Upload a photo of waste",
            type=["jpg", "jpeg", "png", "webp"],
        )

        # Camera input (toggle)
        use_camera = st.toggle("📷 Camera Mode")
        camera_file = st.camera_input("Take a photo") if use_camera else None

        # Use camera if available, otherwise use uploaded file
        if camera_file is not None:
            image = Image.open(camera_file).convert("RGB")
        elif uploaded_file is not None:
            image = Image.open(uploaded_file).convert("RGB")
            st.image(image, caption="Uploaded Image", width=200)
        else:
            image = None

        # Start Detection button
        detect_clicked = st.button("🔍 Start Detection", use_container_width=True)

    with col_right:
        if not model_available:
            st.warning(f"⚠️ {selected_model} model is not trained yet. Please select CNN model.")
        elif image is None:
            st.info("📷 Please upload an image or take a photo")
        elif not detect_clicked:
            st.info("⬆️ Upload/take a photo and click Start Detection")
        else:
            # Run prediction
            model = load_model(MODELS[selected_model])

            # Step 1: apply whichever image treatment this model was actually trained with
            img_array = np.array(image.convert("RGB"))
            mode = IMAGE_PROCESSING.get(selected_model, "A")
            img_array = apply_image_processing(img_array, mode)

            # Step 2: resize to model input size
            img_array = cv2.resize(img_array, (224, 224)).astype(np.float32)
            img_array = np.expand_dims(img_array, axis=0)

            # Step 3: use this model's own normalization — not a shared /255.0 for everything
            img_array = PREPROCESS_FUNCS[selected_model](img_array)

            with st.spinner(f"AI Detecting with {selected_model}..."):
                predictions = predict_with_model(model, img_array)
                pred_index = np.argmax(predictions[0])
                pred_class = CLASS_NAMES[pred_index]
                confidence = float(predictions[0][pred_index]) * 100

            info = RECYCLE_INFO[pred_class]

            # Prediction card
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

            # All probabilities
            st.markdown("**📊 All Probabilities**")
            probs = {CLASS_NAMES[i]: float(predictions[0][i]) * 100 for i in range(len(CLASS_NAMES))}
            sorted_probs = dict(sorted(probs.items(), key=lambda x: x[1], reverse=True))
            for cls, prob in sorted_probs.items():
                st.progress(prob / 100, text=f"{cls.title()}: {prob:.1f}%")

            # Recycling guide
            st.markdown("**♻️ Recycling Guide**")
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

with tab_about:
    st.markdown("## About Smart Waste AI")
    st.markdown("""
    ### What is this?
    AI-powered waste classification system. Upload a photo, and the AI identifies the waste type and guides proper disposal.

    ### How does it work?
    - Multiple AI models trained on waste images
    - Classifies into 4 categories: **Glass, Metal, Paper, Plastic**
    - Provides confidence scores for each category

    ### Supported Models
    | Model | Status |
    |-------|--------|
    | CNN | ✅ Available |
    | MobileNetV2 | ✅ Available |
    | ResNet50 | ✅ Available |

    ### Supported Waste Types
    | Category | Examples |
    |----------|----------|
    | 🍾 Glass | Bottles, jars, windows |
    | 🥫 Metal | Cans, foil, containers |
    | 📄 Paper | Newspapers, cardboard, books |
    | 🧴 Plastic | Bottles, containers, packaging |

    ### Team
    Built for AI Course Assignment
    """)
