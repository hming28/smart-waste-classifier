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

# CLIP is zero-shot (no local checkpoint file) — it's downloaded from the
# HuggingFace Hub by name, matching 01_CLIP_ZeroShot.ipynb exactly.
CLIP_MODEL_NAME = "openai/clip-vit-base-patch32"

# Feature Fusion needs a local .tflite file (converted from 03_Feature_Fusion.ipynb's
# .keras output) — place it in the same directory as this app. It's a dual-input
# model (image + CLIP feature), so it ALSO needs CLIP loaded live at inference time
# (see FUSION_MODELS handling below).
FUSION_MODEL_FILENAME = "resnet50_clip_fusion_final.tflite"

# Model config
# NOTE: CLIP's "path" is a Hub model name, not a local file — it is handled as a
# special case everywhere MODELS is used for file existence / os.path.exists.
MODELS = {
    "CNN": "AdvancedCNN_none_classweight.keras",
    "MobileNetV2": "mobilenetv2_garbage_classifier_4class.keras",
    "ResNet50": "resnet50_model_quantized.tflite",
    "CLIP (zero-shot)": CLIP_MODEL_NAME,
    "Feature Fusion (ResNet50+CLIP)": FUSION_MODEL_FILENAME,
}

# Models that are downloaded from the HuggingFace Hub rather than loaded from a
# local checkpoint file. Used to skip the os.path.exists() file check.
HUB_MODELS = {"CLIP (zero-shot)"}

# CLIP Verify: an optional per-model toggle for CNN/MobileNetV2/ResNet50 that
# double-checks low-confidence predictions using CLIP Linear Probe (needs the
# small trained head saved from 02_CLIP_LinearProbe.ipynb, NOT zero-shot —
# Linear Probe is meaningfully more accurate, 90.65% vs 86.86%).
CLIP_LINEAR_PROBE_FILENAME = "clip_linear_probe.pt"
CLIP_VERIFY_MODELS = {"CNN", "MobileNetV2", "ResNet50"}
CLIP_VERIFY_DEFAULT_THRESHOLD = 0.90

# Models that need a local .keras/.tflite file AND CLIP loaded live (both frameworks
# resident in memory at once — the heaviest combination in this app by far).
FUSION_MODELS = {"Feature Fusion (ResNet50+CLIP)"}

# Each model was trained with a different input normalization
PREPROCESS_FUNCS = {
    "CNN": lambda arr: arr / 255.0,              # AdvancedCNN: rescale=1./255
    "MobileNetV2": mobilenet_preprocess,          # scales to [-1, 1]
    "ResNet50": resnet_preprocess,                # ImageNet mean-subtraction
    # CLIP has no entry here — CLIPProcessor does its own resize/normalize
    # internally (see predict_clip below), so none of this pipeline applies.
}

# Descriptive zero-shot prompts — exact match to 01_CLIP_ZeroShot.ipynb Section 5.
# CLIP is prompt-sensitive; plain class names score noticeably worse than these.
CLIP_PROMPTS = {
    "glass":   "a photo of a glass bottle or glass container",
    "metal":   "a photo of a metal can or aluminum can",
    "paper":   "a photo of paper or cardboard",
    "plastic": "a photo of a plastic bottle or plastic container",
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
    "MobileNetV2": "A",   # confirmed: mobilenetv2_garbage_classifier_4class.keras on this
                           # branch is the Method-B (object-crop) checkpoint from
                           # v2_5_mobilenetv2_object_crop.ipynb — test accuracy 92.90%
    "ResNet50": "A",
    # CLIP (zero-shot): intentionally NOT listed here. CLIPProcessor does its own
    # resize + normalization from the raw PIL image, so applying Method A/B crop
    # logic before it would just be an unnecessary extra resize, not a training-
    # pipeline match (there is no CLIP training pipeline — it's zero-shot).
}


def crop_with_margin_array(img_arr: np.ndarray, margin_ratio: float = 0.10) -> np.ndarray:
    """Exact port of crop_with_margin_array() from
    v2_5_mobilenetv2_object_crop.ipynb (the function actually wired into
    crop_then_preprocess_input / the training ImageDataGenerator — NOT the
    simpler demo-only crop shown in that notebook's Step 4b visualization cell).

    Do not simplify this — the morphology open/close and the min-size guard
    are part of what the deployed .keras file was actually trained on."""
    if img_arr.dtype != np.uint8:
        img_arr = np.clip(img_arr, 0, 255).astype(np.uint8)

    gray = cv2.cvtColor(img_arr, cv2.COLOR_RGB2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    kernel = np.ones((5, 5), np.uint8)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return img_arr

    largest = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(largest)

    if w < 5 or h < 5:
        return img_arr

    mx, my = int(w * margin_ratio), int(h * margin_ratio)
    x1, y1 = max(0, x - mx), max(0, y - my)
    x2, y2 = min(img_arr.shape[1], x + w + mx), min(img_arr.shape[0], y + h + my)

    if x2 <= x1 or y2 <= y1:
        return img_arr

    return img_arr[y1:y2, x1:x2]


def preprocess_image(pil_image: Image.Image, mode: str) -> np.ndarray:
    """Reproduce, pixel-pipeline-for-pixel-pipeline, whatever this model's
    checkpoint was actually trained with. Returns a float32 (224, 224, 3)
    array — normalization (preprocess_input) is applied separately afterward.

    Method A (no treatment) — matches ImageDataGenerator's default
    target_size loading used for CNN / ResNet50 / MobileNetV2-A:
        resize original photo -> 224x224 (nearest)

    Method B (object crop) — matches crop_then_preprocess_input() in
    v2_5_mobilenetv2_object_crop.ipynb EXACTLY, including the order:
        1) resize original photo -> 224x224 (nearest)   <- this is the array
           Keras' target_size loading actually handed to the
           preprocessing_function during training, NOT the original
           full-resolution photo. Cropping the original-resolution photo
           directly (the old bug) is a different pipeline than training saw.
        2) crop_with_margin_array() on THAT 224x224 image (Otsu + morphology)
        3) resize the (usually smaller) crop back up to 224x224 (INTER_AREA,
           matching cv2.resize(..., interpolation=cv2.INTER_AREA) in training)
    """
    arr = np.array(pil_image.convert("RGB"))
    arr = cv2.resize(arr, (224, 224), interpolation=cv2.INTER_NEAREST)

    if mode == "B":
        arr = crop_with_margin_array(arr, margin_ratio=0.10)
        arr = cv2.resize(arr, (224, 224), interpolation=cv2.INTER_AREA)
    elif mode == "C":
        # Not wired up yet — implement once a Method-C-trained model file exists,
        # using the same rembg + neutral-background logic as the training notebook.
        raise NotImplementedError("Method C (background removal) isn't available yet.")
    # mode == "A": no further change beyond the initial resize

    return arr.astype(np.float32)

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
    # CLIP: Hub model name, not a local file — route to the CLIP loader
    if path == CLIP_MODEL_NAME:
        return load_clip_model()

    # Feature Fusion: needs the local .keras file AND a live CLIP encoder
    if path == FUSION_MODEL_FILENAME:
        return load_fusion_model()

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


def load_clip_model():
    """Load CLIP exactly as in 01_CLIP_ZeroShot.ipynb Section 4 — same model name,
    same eval() mode, same device selection. Returns a small bundle dict instead of
    a bare model since predict_clip() also needs the processor + device."""
    import torch
    from transformers import CLIPModel, CLIPProcessor

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = CLIPModel.from_pretrained(CLIP_MODEL_NAME).to(device)
    processor = CLIPProcessor.from_pretrained(CLIP_MODEL_NAME)
    model.eval()
    return {"model": model, "processor": processor, "device": device}


def predict_clip(clip_bundle: dict, pil_image: Image.Image) -> np.ndarray:
    """Zero-shot CLIP inference — mirrors 01_CLIP_ZeroShot.ipynb Section 6 exactly:
    same descriptive prompts, same logits_per_image softmax. Takes the raw PIL
    image directly; CLIPProcessor handles its own resize/normalize, so none of
    preprocess_image() / PREPROCESS_FUNCS applies here.

    Returns an array shaped (1, 4) in CLASS_NAMES order, so it drops straight into
    the same argmax / confidence / progress-bar code the TF models already use."""
    import torch

    model = clip_bundle["model"]
    processor = clip_bundle["processor"]
    device = clip_bundle["device"]

    text_labels = [CLIP_PROMPTS[c] for c in CLASS_NAMES]

    with torch.no_grad():
        inputs = processor(
            text=text_labels, images=[pil_image], return_tensors="pt", padding=True
        ).to(device)
        outputs = model(**inputs)
        probs = outputs.logits_per_image.softmax(dim=1).cpu().numpy()

    return probs


def load_fusion_model():
    """Load BOTH halves the Feature Fusion model needs: the trained dual-input
    TFLite interpreter (quantized, ~24MB vs the original 200MB .keras — same
    dynamic-range quantization used for the standalone ResNet50 model), and a
    frozen CLIP encoder (to compute the 512-d feature its second input branch
    expects). Mirrors 03_Feature_Fusion.ipynb Section 6.

    This is still the heaviest load in the app — full ResNet50 backbone (via the
    fusion model) + full CLIP (PyTorch) resident in memory at the same time, for
    as long as this model stays selected — quantizing the .tflite only shrinks
    the on-disk/weight footprint, not the fact that two frameworks run together."""
    interpreter = tf.lite.Interpreter(model_path=FUSION_MODEL_FILENAME)
    interpreter.allocate_tensors()
    clip_bundle = load_clip_model()
    return {"interpreter": interpreter, "clip": clip_bundle}


def get_clip_feature(clip_bundle: dict, pil_image: Image.Image) -> np.ndarray:
    """Frozen CLIP image EMBEDDING (512-d, L2-normalized) — NOT zero-shot
    classification against text prompts. Same extraction used to build the
    training features in 02_CLIP_LinearProbe.ipynb / 03_Feature_Fusion.ipynb:
    vision_model -> visual_projection -> L2 normalize (bypasses the
    get_image_features() wrapper — see those notebooks for why)."""
    import torch

    model = clip_bundle["model"]
    processor = clip_bundle["processor"]
    device = clip_bundle["device"]

    with torch.no_grad():
        inputs = processor(images=[pil_image], return_tensors="pt").to(device)
        vision_outputs = model.vision_model(pixel_values=inputs["pixel_values"])
        pooled_output = vision_outputs.pooler_output
        feats = model.visual_projection(pooled_output)
        feats = feats / feats.norm(dim=-1, keepdim=True)

    return feats.cpu().numpy()  # shape (1, 512)


def predict_fusion(bundle: dict, pil_image: Image.Image) -> np.ndarray:
    """Dual-branch inference, mirroring 03_Feature_Fusion.ipynb exactly:
    - ResNet50 branch: plain resize (Method A) + resnet50.preprocess_input,
      same pipeline as the standalone ResNet50 model above.
    - CLIP branch: frozen 512-d feature from get_clip_feature() above.
    Both feed into the trained fusion head via the TFLite interpreter. Tensors
    are matched by NAME, not fixed index — TFLite conversion doesn't guarantee
    input_details order matches the original Keras model's input list order
    (confirmed: this file lists clip_feature at index 0, image at index 1).
    Returns (1, 4) in CLASS_NAMES order, same as every other model's predictions."""
    interpreter = bundle["interpreter"]
    clip_bundle = bundle["clip"]

    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    img_array = preprocess_image(pil_image, "A")
    img_array = np.expand_dims(img_array, axis=0)
    img_array = resnet_preprocess(img_array).astype(np.float32)

    clip_feature = get_clip_feature(clip_bundle, pil_image).astype(np.float32)

    for detail in input_details:
        if "image" in detail["name"]:
            interpreter.set_tensor(detail["index"], img_array)
        elif "clip_feature" in detail["name"]:
            interpreter.set_tensor(detail["index"], clip_feature)

    interpreter.invoke()
    predictions = interpreter.get_tensor(output_details[0]["index"])
    return predictions


def load_clip_verify_bundle():
    """CLIP Verify helper: frozen CLIP encoder + a small trained Linear Probe
    head (512 -> 4), used to double-check CNN/MobileNetV2/ResNet50 predictions
    when their own confidence is low. Mirrors 02_CLIP_LinearProbe.ipynb.

    ⚠️ Be upfront about this, including in the UI: a threshold-gated version of
    this was tested empirically on the 845-image shared test split and did NOT
    beat ResNet50 alone (best test-set-searched threshold got 96.80%, vs.
    96.92% for ResNet50 alone — worse, not better). ResNet50's confidence is
    often still high even when wrong (mean 0.86 even on wrong predictions), so
    a simple confidence cutoff can't cleanly separate "trust me" from "ask
    CLIP" on these clean, studio-style dataset photos. This toggle exists for
    experimentation and for real-world / out-of-distribution photos, where the
    effect is untested and may differ — not because it's confirmed to help on
    the benchmark images the model was graded on."""
    import torch
    import torch.nn as nn

    class LinearProbeHead(nn.Module):
        def __init__(self, in_dim=512, n_classes=4):
            super().__init__()
            self.fc = nn.Linear(in_dim, n_classes)

        def forward(self, x):
            return self.fc(x)

    clip_bundle = load_clip_model()
    device = clip_bundle["device"]

    probe = LinearProbeHead().to(device)
    probe.load_state_dict(torch.load(CLIP_LINEAR_PROBE_FILENAME, map_location=device))
    probe.eval()

    return {"clip": clip_bundle, "probe": probe}


def predict_clip_verify(bundle: dict, pil_image: Image.Image) -> np.ndarray:
    """CLIP Linear Probe inference — frozen CLIP feature -> trained Linear
    layer -> softmax. Same math as 02_CLIP_LinearProbe.ipynb Section 7.
    Returns (1, 4) in CLASS_NAMES order."""
    import torch

    clip_bundle = bundle["clip"]
    probe = bundle["probe"]
    device = clip_bundle["device"]

    clip_feature = get_clip_feature(clip_bundle, pil_image)  # (1, 512) numpy, frozen CLIP

    with torch.no_grad():
        feat_tensor = torch.tensor(clip_feature, dtype=torch.float32).to(device)
        logits = probe(feat_tensor)
        probs = torch.softmax(logits, dim=1).cpu().numpy()

    return probs


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


@st.cache_resource
def get_clip_verify_bundle():
    return load_clip_verify_bundle()


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
            if name in HUB_MODELS:
                # CLIP has no local checkpoint — it's "available" if the
                # torch/transformers packages are installed, not a file check.
                try:
                    import torch as _torch_check  # noqa: F401
                    import transformers as _transformers_check  # noqa: F401
                    available = True
                except ImportError:
                    available = False
            elif name in FUSION_MODELS:
                # Needs BOTH the local .keras file AND torch/transformers installed.
                try:
                    import torch as _torch_check  # noqa: F401
                    import transformers as _transformers_check  # noqa: F401
                    available = os.path.exists(filename)
                except ImportError:
                    available = False
            else:
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

        # CLIP Verify toggle — only offered for CNN/MobileNetV2/ResNet50 (CLIP
        # zero-shot and Feature Fusion already are/include CLIP, no point toggling)
        use_clip_verify = False
        clip_verify_threshold = CLIP_VERIFY_DEFAULT_THRESHOLD
        clip_verify_available = os.path.exists(CLIP_LINEAR_PROBE_FILENAME) and model_files.get("CLIP (zero-shot)", False)

        if selected_model in CLIP_VERIFY_MODELS:
            if clip_verify_available:
                use_clip_verify = st.toggle(
                    "🔍 CLIP Verify",
                    help="When ON, low-confidence predictions get double-checked by CLIP "
                         "Linear Probe. Tested on the benchmark test set this did NOT "
                         "improve accuracy (confidence isn't a reliable signal for this "
                         "model) — provided for experimentation, especially on real-world "
                         "photos the model wasn't trained on.",
                )
                if use_clip_verify:
                    clip_verify_threshold = st.slider(
                        "Verify below this confidence",
                        min_value=0.50, max_value=1.00,
                        value=CLIP_VERIFY_DEFAULT_THRESHOLD, step=0.01,
                    )
            else:
                st.caption("⚠️ CLIP Verify unavailable — missing `clip_linear_probe.pt` or CLIP dependencies.")

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

            if selected_model in HUB_MODELS:
                # CLIP (zero-shot): no crop/resize pipeline, no train-time
                # normalization — CLIPProcessor takes the raw image directly and
                # scores it against text prompts (see predict_clip above).
                with st.spinner(f"AI Detecting with {selected_model}..."):
                    predictions = predict_clip(model, image)
                    pred_index = np.argmax(predictions[0])
                    pred_class = CLASS_NAMES[pred_index]
                    confidence = float(predictions[0][pred_index]) * 100
            elif selected_model in FUSION_MODELS:
                # Dual-branch: ResNet50-style preprocessing for the image input,
                # plus a live CLIP feature for the second input (see predict_fusion).
                with st.spinner(f"AI Detecting with {selected_model}..."):
                    predictions = predict_fusion(model, image)
                    pred_index = np.argmax(predictions[0])
                    pred_class = CLASS_NAMES[pred_index]
                    confidence = float(predictions[0][pred_index]) * 100
            else:
                # Step 1+2: reproduce this model's exact training-time pipeline
                # (resize -> [crop for Method B] -> resize), NOT resize-then-crop-once.
                mode = IMAGE_PROCESSING.get(selected_model, "A")
                img_array = preprocess_image(image, mode)
                img_array = np.expand_dims(img_array, axis=0)

                # Step 3: use this model's own normalization — not a shared /255.0 for everything
                img_array = PREPROCESS_FUNCS[selected_model](img_array)

                with st.spinner(f"AI Detecting with {selected_model}..."):
                    predictions = predict_with_model(model, img_array)
                    pred_index = np.argmax(predictions[0])
                    pred_class = CLASS_NAMES[pred_index]
                    confidence = float(predictions[0][pred_index]) * 100

                # CLIP Verify: only kicks in if the toggle is on AND this
                # prediction's own confidence fell below the chosen threshold.
                # See load_clip_verify_bundle()'s docstring — this is NOT
                # confirmed to improve accuracy on the benchmark test images.
                if use_clip_verify and (confidence / 100.0) < clip_verify_threshold:
                    verify_bundle = get_clip_verify_bundle()
                    with st.spinner("Confidence low — verifying with CLIP..."):
                        clip_predictions = predict_clip_verify(verify_bundle, image)
                        predictions = clip_predictions
                        pred_index = np.argmax(predictions[0])
                        pred_class = CLASS_NAMES[pred_index]
                        confidence = float(predictions[0][pred_index]) * 100
                    st.caption(f"🔍 {selected_model}'s confidence was below "
                               f"{clip_verify_threshold*100:.0f}% — final answer verified/overridden by CLIP.")
                elif use_clip_verify:
                    st.caption(f"✅ {selected_model} was confident enough — used directly, CLIP not consulted.")

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
    | CLIP (zero-shot) | ✅ Available — no training, baseline comparison |
    | Feature Fusion (ResNet50+CLIP) | ✅ Available — dual-branch trained framework, 97.04% test accuracy |

    **CLIP Verify** (optional toggle for CNN/MobileNetV2/ResNet50): double-checks
    low-confidence predictions using CLIP Linear Probe. ⚠️ Tested on the benchmark
    test set, this did *not* improve accuracy — provided for experimentation on
    real-world photos instead.

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
