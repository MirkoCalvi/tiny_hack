"""Flask server that receives alerts from Nicla Vision and stores incoming images.

Run with:
    python app.py --host 110.100.15.27 --port 8000
"""
from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import signal
import sys
import time
import uuid
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from flask import Flask, Response, jsonify, render_template, render_template_string, request
from werkzeug.utils import secure_filename

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

from classifier import BaseClassifier, MockLesionClassifier, load_classifier

LOGGER = logging.getLogger("nicla.server")
app = Flask(__name__)

DEFAULT_UPLOAD_DIR = Path(__file__).resolve().parent / "incoming"
DEFAULT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

LESION_PROFILES = [
    {
        "type": "Melanoma",
        "category": "malignant",
        "risk": "critical",
        "priority": 1,
        "description": "Melanoma maligno - tumore della pelle più aggressivo",
    },
    {
        "type": "Basal_cell_carcinoma",
        "category": "malignant",
        "risk": "critical",
        "priority": 1,
        "description": "Carcinoma basocellulare - tumore cutaneo maligno",
    },
    {
        "type": "Actinic_keratoses",
        "category": "premalignant",
        "risk": "high",
        "priority": 2,
        "description": "Cheratosi attinica - lesione precancerosa",
    },
    {
        "type": "Melanocytic_nevi",
        "category": "benign",
        "risk": "medium",
        "priority": 3,
        "description": "Nevi melanocitici - nei benigni da monitorare",
    },
    {
        "type": "Vascular_lesions",
        "category": "benign",
        "risk": "low",
        "priority": 4,
        "description": "Lesioni vascolari benigne",
    },
    {
        "type": "Benign_keratosis-like_lesions",
        "category": "benign",
        "risk": "low",
        "priority": 4,
        "description": "Cheratosi seborroica - lesione benigna",
    },
    {
        "type": "Dermatofibroma",
        "category": "benign",
        "risk": "low",
        "priority": 5,
        "description": "Dermatofibroma - nodulo cutaneo benigno",
    },
]

LESION_PROFILE_BY_NAME = {profile["type"].lower(): profile for profile in LESION_PROFILES}
CLASS_LABELS = [profile["type"] for profile in LESION_PROFILES]
CLASSIFIER: BaseClassifier = load_classifier(class_labels=CLASS_LABELS)


# Custom Jinja2 filter for risk level translation
@app.template_filter('risk_label')
def risk_label_filter(risk_level: str) -> str:
    """Convert risk level to Italian medical category label."""
    mapping = {
        'critical': 'Maligno',
        'high': 'Premaligno',
        'medium': 'Benigno',
        'low': 'Benigno',
        'unknown': 'Sconosciuto'
    }
    return mapping.get(risk_level.lower() if risk_level else '', 'Sconosciuto')


def _print_image_to_terminal(image_path: Path, width: int = 80) -> None:
    """Stampa una preview ASCII dell'immagine nel terminale."""
    if not HAS_PIL:
        print("📷 [Immagine ricevuta - installa Pillow per vedere la preview]")
        return
    
    try:
        img = Image.open(image_path)
        
        # Ridimensiona mantenendo aspect ratio
        aspect_ratio = img.height / img.width
        height = int(width * aspect_ratio * 0.5)  # 0.5 perché i caratteri sono più alti che larghi
        img_resized = img.resize((width, height), Image.Resampling.LANCZOS)
        
        # Converti in grayscale
        img_gray = img_resized.convert('L')
        
        # Caratteri ASCII dal più scuro al più chiaro
        ascii_chars = ' .:-=+*#%@'
        
        print("\n📷 PREVIEW IMMAGINE:")
        print("┌" + "─" * width + "┐")
        
        for y in range(height):
            row = "│"
            for x in range(width):
                pixel_value = img_gray.getpixel((x, y))
                # Mappa il valore del pixel (0-255) a un carattere ASCII
                char_index = int((pixel_value / 255) * (len(ascii_chars) - 1))
                row += ascii_chars[char_index]
            row += "│"
            print(row)
        
        print("└" + "─" * width + "┘")
        print(f"Dimensioni originali: {img.width}x{img.height} px\n")
        
    except Exception as e:
        print(f"⚠️  Impossibile mostrare preview: {e}")


def _load_capture_metadata(meta_file: Path) -> Dict[str, Any]:
    try:
        data = json.loads(meta_file.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive
        raise ValueError(f"invalid metadata file {meta_file.name}: {exc}") from exc

    stored_filename = data.get("stored_filename") or meta_file.stem
    data["stored_filename"] = stored_filename
    capture_id = data.get("capture_id")
    if not capture_id:
        capture_id = stored_filename.split(".")[0]
        data["capture_id"] = capture_id
    data["_meta_path"] = meta_file
    return data


def _list_recent_captures(upload_dir: Path, limit: int = 10) -> List[Dict[str, Any]]:
    json_files = sorted(upload_dir.glob("*.json"), key=os.path.getmtime, reverse=True)
    captures: List[Dict[str, Any]] = []
    for meta_file in json_files[:limit]:
        try:
            data = _load_capture_metadata(meta_file)
        except ValueError as exc:
            LOGGER.warning("Skipping metadata %s: %s", meta_file.name, exc)
            continue
        captures.append(
            {
                "capture_id": data["capture_id"],
                "stored_filename": data["stored_filename"],
                "received_at_utc": data.get("received_at_utc"),
                "image_format": data.get("image_format"),
                "metadata": data,
            }
        )
    return captures


def _find_capture_by_id(upload_dir: Path, capture_id: str) -> Optional[Dict[str, Any]]:
    for meta_file in upload_dir.glob(f"{capture_id}*.json"):
        try:
            data = _load_capture_metadata(meta_file)
        except ValueError as exc:
            LOGGER.warning("Invalid metadata for capture %s: %s", capture_id, exc)
            continue
        return {
            "capture_id": data["capture_id"],
            "stored_filename": data["stored_filename"],
            "received_at_utc": data.get("received_at_utc"),
            "image_format": data.get("image_format"),
            "metadata": data,
        }
    return None


def _rgb565_to_image(data: bytes, width: int, height: int) -> Image.Image:
    if not HAS_PIL:
        raise RuntimeError("Pillow non installato: impossibile convertire RGB565")

    expected = width * height * 2
    if len(data) < expected:
        raise ValueError(
            f"RGB565 payload troppo corto: attesi {expected} bytes, ricevuti {len(data)}"
        )
    data = data[:expected]

    if HAS_NUMPY:
        rgb565 = np.frombuffer(data, dtype="<u2").reshape((height, width))
        r = ((rgb565 >> 11) & 0x1F).astype(np.uint16)
        g = ((rgb565 >> 5) & 0x3F).astype(np.uint16)
        b = (rgb565 & 0x1F).astype(np.uint16)
        r = (r * 255 + 15) // 31
        g = (g * 255 + 31) // 63
        b = (b * 255 + 15) // 31
        rgb = np.dstack((r, g, b)).astype(np.uint8)
        return Image.fromarray(rgb, mode="RGB")

    pixels = []
    for i in range(0, expected, 2):
        value = data[i] | (data[i + 1] << 8)
        r = ((value >> 11) & 0x1F) * 255 // 31
        g = ((value >> 5) & 0x3F) * 255 // 63
        b = (value & 0x1F) * 255 // 31
        pixels.append((r, g, b))

    image = Image.new("RGB", (width, height))
    image.putdata(pixels)
    return image


def _build_image_bytes(metadata: Dict[str, Any], upload_dir: Path) -> Tuple[bytes, str]:
    stored_filename = metadata["stored_filename"]
    image_path = upload_dir / stored_filename
    if not image_path.exists():
        raise FileNotFoundError(f"file immagine mancante: {stored_filename}")

    image_format = str(metadata.get("image_format", "")).upper()
    suffix = image_path.suffix.lower()
    is_rgb565 = image_format == "RGB565" or suffix in {".rgb565", ".raw", ".bin"}

    if is_rgb565:
        width = int(
            metadata.get("width")
            or metadata.get("image_width")
            or metadata.get("cols")
            or 320
        )
        height = int(
            metadata.get("height")
            or metadata.get("image_height")
            or metadata.get("rows")
            or 240
        )
        rgb_image = _rgb565_to_image(image_path.read_bytes(), width, height)
        buffer = BytesIO()
        rgb_image.save(buffer, format="PNG")
        return buffer.getvalue(), "image/png"

    # Per JPEG/PNG e simili restituiamo direttamente i byte originali
    data = image_path.read_bytes()
    mime = metadata.get("content_type")
    if mime:
        return data, mime

    if suffix in {".jpg", ".jpeg"}:
        return data, "image/jpeg"
    if suffix == ".png":
        return data, "image/png"

    # fallback: convertiamo in PNG se possibile
    if HAS_PIL:
        try:
            with Image.open(BytesIO(data)) as img:
                buffer = BytesIO()
                img.save(buffer, format="PNG")
                return buffer.getvalue(), "image/png"
        except Exception:
            pass

    return data, "application/octet-stream"


def _build_classification_result(
    label: str,
    confidence: float,
    provider: str,
    *,
    model_version: Optional[str] = None,
    raw_predictions: Optional[List[Dict[str, Any]]] = None,
    latency_ms: Optional[float] = None,
) -> Dict[str, Any]:
    profile = LESION_PROFILE_BY_NAME.get(label.lower())

    result = {
        "classification": label,
        "category": profile["category"] if profile else "unknown",
        "description": profile["description"] if profile else "Classe non presente nel profilo di rischio.",
        "confidence": round(float(confidence), 3),
        "risk_level": profile["risk"] if profile else "unknown",
        "priority": profile["priority"] if profile else 5,
        "model_version": model_version or "unknown",
        "classified_at": datetime.utcnow().isoformat() + "Z",
        "inference_provider": provider,
    }

    if latency_ms is not None:
        result["inference_latency_ms"] = round(latency_ms, 2)

    if raw_predictions is not None:
        # Manteniamo solo i primi 3 risultati per evitare metadata troppo pesanti
        result["raw_predictions"] = raw_predictions[:3]

    return result


def _ensure_classifier() -> BaseClassifier:
    global CLASSIFIER
    if not isinstance(CLASSIFIER, BaseClassifier):
        CLASSIFIER = load_classifier(class_labels=CLASS_LABELS)
    return CLASSIFIER


def classify_lesion(image_path: Path, suspicious_score: float = None) -> Dict[str, Any]:
    classifier = _ensure_classifier()
    try:
        prediction = classifier.predict(image_path, suspicious_score)
    except Exception as exc:  # pragma: no cover - defensive
        LOGGER.error("Classifier failure: %s", exc)
        # fallback to mock classifier for robustness
        fallback = MockLesionClassifier(CLASS_LABELS)
        prediction = fallback.predict(image_path, suspicious_score)
        # Keep reference to fallback to avoid repeated failures
        global CLASSIFIER
        CLASSIFIER = fallback

    return _build_classification_result(
        prediction.label,
        prediction.confidence,
        provider=prediction.provider,
        model_version=prediction.model_version,
        raw_predictions=prediction.raw_predictions,
        latency_ms=prediction.latency_ms,
    )


VIEWER_TEMPLATE = """
<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"utf-8\" />
    <title>Nicla Vision Capture Viewer</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 0; background: #0b0b0b; color: #f0f0f0; }
        header { padding: 1.2rem 1.5rem; background: #121212; border-bottom: 1px solid #222; display: flex; flex-wrap: wrap; align-items: center; gap: 1rem; }
        h1 { margin: 0; font-size: 1.3rem; letter-spacing: 0.05em; text-transform: uppercase; color: #76ff03; }
        main { display: grid; grid-template-columns: 320px 1fr; gap: 1.5rem; padding: 1.5rem; }
        aside { background: #141414; border: 1px solid #222; border-radius: 10px; overflow: hidden; }
        aside h2 { font-size: 0.95rem; text-transform: uppercase; letter-spacing: 0.08em; background: #1c1c1c; padding: 0.75rem 1rem; margin: 0; border-bottom: 1px solid #222; }
        ul.capture-list { list-style: none; margin: 0; padding: 0; max-height: calc(100vh - 220px); overflow-y: auto; }
        ul.capture-list li { border-bottom: 1px solid #1f1f1f; }
        ul.capture-list a { display: block; padding: 0.8rem 1rem; color: inherit; text-decoration: none; transition: background 0.2s ease; }
        ul.capture-list a:hover { background: #1f1f1f; }
        ul.capture-list a.active { background: #2b2b2b; border-left: 3px solid #76ff03; padding-left: calc(1rem - 3px); }
        .capture-meta { font-size: 0.75rem; line-height: 1.4; color: #bbb; }
        section.viewer { background: #0f0f0f; border-radius: 12px; border: 1px solid #222; padding: 1.5rem; display: flex; flex-direction: column; gap: 1rem; align-items: center; }
        .frame { background: #000; border: 1px solid #111; border-radius: 10px; padding: 1rem; box-shadow: 0 20px 50px rgba(0,0,0,0.35); }
        .frame img { max-width: 100%; border-radius: 6px; }
        table.meta { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
        table.meta th { text-align: left; padding: 0.4rem 0.6rem; width: 35%; color: #aaa; font-weight: 600; }
        table.meta td { padding: 0.4rem 0.6rem; color: #f5f5f5; }
        .message { padding: 1rem; border-radius: 8px; background: #1e1e1e; border: 1px solid #2a2a2a; }
        .error { background: rgba(244,67,54,0.08); border-color: rgba(244,67,54,0.4); color: #ff8a80; }
        footer { padding: 1rem 1.5rem; text-align: center; font-size: 0.75rem; color: #666; border-top: 1px solid #111; }
        @media (max-width: 1024px) { main { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <header>
        <h1>Nicla Vision Capture Viewer</h1>
        <div>Totale acquisizioni: {{ captures|length }}</div>
    </header>
    <main>
        <aside>
            <h2>Acquisizioni recenti</h2>
            {% if captures %}
            <ul class="capture-list">
                {% for item in captures %}
                <li>
                    <a href="{{ url_for('viewer') }}?capture_id={{ item.capture_id }}"
                       class="{% if item.capture_id == selected_capture %}active{% endif %}">
                        <strong>{{ item.capture_id }}</strong>
                        <div class="capture-meta">
                            {{ item.image_format or 'N/A' }} · {{ item.received_at_utc or 'unknown time' }}
                        </div>
                    </a>
                </li>
                {% endfor %}
            </ul>
            {% else %}
            <div class="message">Nessuna acquisizione presente.</div>
            {% endif %}
        </aside>
        <section class="viewer">
            {% if error %}
            <div class="message error">{{ error }}</div>
            {% elif image_data %}
            <div class="frame">
                <img src="data:image/png;base64,{{ image_data }}" alt="Capture preview" />
            </div>
            {% else %}
            <div class="message">Seleziona un'acquisizione per visualizzare l'immagine.</div>
            {% endif %}

            {% if metadata %}
            <table class="meta">
                {% for key, value in metadata.items() %}
                <tr>
                    <th>{{ key }}</th>
                    <td>{{ value }}</td>
                </tr>
                {% endfor %}
            </table>
            {% endif %}
        </section>
    </main>
    <footer>Nicla Vision ingestion server · {{ datetime.utcnow().isoformat() }}Z</footer>
</body>
</html>
"""

def _parse_metadata(metadata_raw: str | None) -> Dict[str, Any]:
    if not metadata_raw:
        return {}
    try:
        metadata = json.loads(metadata_raw)
        if not isinstance(metadata, dict):
            raise ValueError("metadata must be a JSON object")
        return metadata
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise ValueError(f"invalid metadata JSON: {exc}") from exc


def _save_image(image_stream, original_filename: str, upload_dir: Path) -> Tuple[Path, str]:
    sanitized_name = secure_filename(original_filename) or "capture.jpg"
    suffix = Path(sanitized_name).suffix or ".jpg"
    capture_id = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"
    destination = upload_dir / f"{capture_id}{suffix}"
    image_stream.save(destination)
    return destination, capture_id


@app.post("/ingest")
def ingest():
    print("\nRicevuta nuova richiesta di ingestione...")
    upload_dir = Path(app.config.get("UPLOAD_DIR", DEFAULT_UPLOAD_DIR))
    upload_dir.mkdir(parents=True, exist_ok=True)

    received_at = datetime.utcnow().isoformat() + "Z"

    if "image" not in request.files:
        return jsonify({"status": "error", "message": "missing 'image' field"}), 400

    image_file = request.files["image"]
    metadata_raw = request.form.get("metadata")

    try:
        metadata = _parse_metadata(metadata_raw)
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400

    destination, capture_id = _save_image(image_file, image_file.filename, upload_dir)

    metadata.update(
        {
            "capture_id": capture_id,
            "received_at_utc": received_at,
            "original_filename": image_file.filename,
            "content_type": image_file.content_type,
            "content_length": request.content_length,
        }
    )

    metadata["stored_filename"] = destination.name

    suffix = destination.suffix.lower()
    inferred_format = metadata.get("image_format") or metadata.get("pixel_format")
    if not inferred_format:
        if suffix in {".jpg", ".jpeg"}:
            inferred_format = "JPEG"
        elif suffix == ".png":
            inferred_format = "PNG"
        elif suffix in {".rgb565", ".raw", ".bin"} or (
            image_file.content_type in {"application/octet-stream", "binary/octet-stream"}
        ):
            inferred_format = "RGB565"
        else:
            inferred_format = suffix.lstrip(".").upper() if suffix else "UNKNOWN"
    metadata["image_format"] = inferred_format

    if HAS_PIL and suffix not in {".rgb565", ".raw", ".bin"}:
        try:
            with Image.open(destination) as img:
                metadata.setdefault("width", img.width)
                metadata.setdefault("height", img.height)
        except Exception as exc:
            LOGGER.debug("Impossibile leggere dimensioni immagine %s: %s", destination.name, exc)

    # Classifica l'immagine con il classificatore mock (per ora)
    suspicious_score = metadata.get("score")
    classification = classify_lesion(destination, suspicious_score)
    metadata.update(classification)

    metadata_path = destination.with_suffix(destination.suffix + ".json")
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    # Log dettagliato per verificare la comunicazione
    print("\n" + "=" * 80)
    print("📸 NUOVA IMMAGINE RICEVUTA!")
    print("=" * 80)
    print(f"🆔 Capture ID:       {capture_id}")
    print(f"📁 File salvato:     {destination.name}")
    print(f"📊 Dimensione:       {request.content_length:,} bytes ({request.content_length / 1024:.2f} KB)")
    print(f"🎨 Tipo contenuto:   {image_file.content_type}")
    print(f"📝 Nome originale:   {image_file.filename}")
    print(f"⏰ Ricevuto alle:    {received_at}")
    
    if metadata.get("device_id"):
        print(f"🔧 Device ID:        {metadata['device_id']}")
    if metadata.get("score") is not None:
        print(f"⚠️  Score sospetto:   {metadata['score']:.3f}")
    if metadata.get("timestamp"):
        print(f"⏱️  Timestamp device: {metadata['timestamp']} ms")
    
    # Mostra risultato classificazione
    if metadata.get("classification"):
        risk_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
        risk = metadata.get("risk_level", "unknown")
        print(f"\n🏥 CLASSIFICAZIONE ML:")
        print(f"   {risk_emoji.get(risk, '⚪')} Tipo:       {metadata['classification']}")
        print(f"   📊 Confidence: {metadata['confidence']:.1%}")
        print(f"   ⚠️  Risk Level: {risk.upper()}")
        provider = metadata.get("inference_provider")
        if provider:
            print(f"   🤖 Provider:   {provider}")
        model_version = metadata.get("model_version")
        if model_version:
            print(f"   🧠 Modello:    {model_version}")
        if metadata.get("inference_error"):
            print(f"   ⚠️  Fallback:   {metadata['inference_error']}")
    
    print(f"\n💾 Metadata salvati: {metadata_path.name}")
    print("=" * 80 + "\n")
    
    # Stampa preview dell'immagine a terminale
    _print_image_to_terminal(destination, width=60)

    LOGGER.info("Stored capture %s -> %s", capture_id, destination.name)

    return (
        jsonify(
            {
                "status": "ok",
                "capture_id": capture_id,
                "stored_filename": destination.name,
                "metadata_path": metadata_path.name,
            }
        ),
        201,
    )


@app.get("/")
@app.get("/dashboard")
def dashboard():
    """Medical dashboard view with case list and detailed analysis."""
    upload_dir = Path(app.config.get("UPLOAD_DIR", DEFAULT_UPLOAD_DIR))
    
    # Get all recent captures
    all_captures = _list_recent_captures(upload_dir, limit=100)
    
    # Calculate summary statistics by category (malignant, premalignant, benign)
    summary = {
        "malignant": 0,
        "premalignant": 0,
        "benign": 0
    }
    for capture in all_captures:
        category = capture["metadata"].get("category", "benign")
        if category in summary:
            summary[category] += 1
    
    # Get selected case
    capture_id = request.args.get("capture_id")
    if not capture_id and all_captures:
        capture_id = all_captures[0]["capture_id"]
    
    # Prepare case data for list view
    cases = []
    for capture in all_captures:
        cases.append({
            "capture_id": capture["capture_id"],
            "stored_filename": capture["stored_filename"],
            "received_at_utc": capture.get("received_at_utc"),
            "image_format": capture.get("image_format"),
            "metadata": capture["metadata"],
        })
    
    # Get detailed metadata and image for selected case
    selected_metadata: Optional[Dict[str, Any]] = None
    image_data: Optional[str] = None
    selected_entry: Optional[Dict[str, Any]] = None
    image_error: Optional[str] = None
    
    if capture_id:
        selected_entry = next((c for c in all_captures if c["capture_id"] == capture_id), None)
        if selected_entry is None:
            selected_entry = _find_capture_by_id(upload_dir, capture_id)
        
        if selected_entry:
            # Always set metadata even if image fails to load
            selected_metadata = {
                k: v
                for k, v in selected_entry["metadata"].items()
                if not k.startswith("_")
            }
            
            # Try to load the image
            try:
                image_bytes, mimetype = _build_image_bytes(selected_entry["metadata"], upload_dir)
                
                # Check if image is empty
                if len(image_bytes) == 0:
                    raise ValueError("Image file is empty (0 bytes). Arduino may not be sending image data correctly.")
                
                image_data = base64.b64encode(image_bytes).decode("ascii")
                LOGGER.info("Successfully loaded image for %s (%d bytes)", capture_id, len(image_bytes))
            except Exception as exc:
                error_msg = str(exc)
                LOGGER.error("Failed to load image for %s: %s", capture_id, error_msg)
                image_error = error_msg
                # Keep metadata but set image_data to None so template shows placeholder
    
    return render_template(
        "dashboard.html",
        summary=summary,
        cases=cases,
        selected_case=capture_id,
        selected_metadata=selected_metadata,
        image_data=image_data,
        image_error=image_error,
    )


@app.get("/captures")
def list_captures():
    upload_dir = Path(app.config.get("UPLOAD_DIR", DEFAULT_UPLOAD_DIR))
    limit = int(request.args.get("limit", 20))
    captures = _list_recent_captures(upload_dir, limit=limit)
    payload = []
    for item in captures:
        meta = item["metadata"]
        payload.append(
            {
                "capture_id": item["capture_id"],
                "stored_filename": item["stored_filename"],
                "received_at_utc": item.get("received_at_utc"),
                "image_format": item.get("image_format"),
                "width": meta.get("width"),
                "height": meta.get("height"),
                "content_length": meta.get("content_length"),
            }
        )
    return jsonify(payload)


@app.get("/captures/<capture_id>")
def capture_metadata(capture_id: str):
    upload_dir = Path(app.config.get("UPLOAD_DIR", DEFAULT_UPLOAD_DIR))
    capture = _find_capture_by_id(upload_dir, capture_id)
    if capture is None:
        return jsonify({"status": "error", "message": "capture not found"}), 404
    metadata = {k: v for k, v in capture["metadata"].items() if not k.startswith("_")}
    return jsonify(metadata)


@app.get("/captures/<capture_id>/image")
def capture_image(capture_id: str):
    upload_dir = Path(app.config.get("UPLOAD_DIR", DEFAULT_UPLOAD_DIR))
    capture = _find_capture_by_id(upload_dir, capture_id)
    if capture is None:
        return jsonify({"status": "error", "message": "capture not found"}), 404
    try:
        image_bytes, mimetype = _build_image_bytes(capture["metadata"], upload_dir)
    except Exception as exc:  # pragma: no cover - defensive
        return jsonify({"status": "error", "message": str(exc)}), 500
    return Response(image_bytes, mimetype=mimetype)


@app.get("/viewer")
def viewer():
    upload_dir = Path(app.config.get("UPLOAD_DIR", DEFAULT_UPLOAD_DIR))
    captures = _list_recent_captures(upload_dir, limit=25)
    capture_id = request.args.get("capture_id")

    if not capture_id and captures:
        capture_id = captures[0]["capture_id"]

    image_data: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    selected_capture = capture_id
    selected_entry: Optional[Dict[str, Any]] = None

    if capture_id:
        selected_entry = next((c for c in captures if c["capture_id"] == capture_id), None)
        if selected_entry is None:
            selected_entry = _find_capture_by_id(upload_dir, capture_id)
            if selected_entry:
                captures.insert(0, selected_entry)

        if selected_entry:
            try:
                image_bytes, mimetype = _build_image_bytes(selected_entry["metadata"], upload_dir)
                image_data = base64.b64encode(image_bytes).decode("ascii")
                metadata = {
                    k: v
                    for k, v in selected_entry["metadata"].items()
                    if not k.startswith("_")
                }
                metadata.setdefault("preview_mimetype", mimetype)
            except Exception as exc:  # pragma: no cover - defensive
                error = f"Impossibile generare la preview: {exc}"
        else:
            error = f"Acquisizione '{capture_id}' non trovata"

    return render_template_string(
        VIEWER_TEMPLATE,
        captures=captures,
        selected_capture=selected_capture,
        image_data=image_data,
        metadata=metadata,
        error=error,
        datetime=datetime,
    )


@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat() + "Z"}


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] %(levelname)s in %(name)s: %(message)s",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Nicla Vision ingestion server")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    parser.add_argument(
        "--upload-dir",
        type=Path,
        default=DEFAULT_UPLOAD_DIR,
        help="Directory where incoming captures will be stored",
    )
    parser.add_argument("--debug", action="store_true", help="Run Flask in debug mode")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args(argv)

    _setup_logging(args.verbose)
    app.config["UPLOAD_DIR"] = args.upload_dir

    LOGGER.info("Starting Nicla ingestion server on %s:%s", args.host, args.port)
    LOGGER.info("Saving captures to %s", args.upload_dir)

    # Ensure upload directory exists ahead of time
    args.upload_dir.mkdir(parents=True, exist_ok=True)

    app.run(host=args.host, port=args.port, debug=args.debug)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        LOGGER.info("Server interrupted; shutting down")
        try:
            # Give Flask a chance to shut down cleanly
            os.kill(os.getpid(), signal.SIGINT)
        except OSError:
            pass
        sys.exit(0)
