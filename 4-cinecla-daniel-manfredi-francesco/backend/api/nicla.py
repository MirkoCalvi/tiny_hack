from flask import request, jsonify
from app import app, socketio, impressions, devices, get_timestamp_ms, current_session
import logging


# See api/models.py for expected request format for the Nicla !!
from api.models import ImpressionRequest, ImpressionResponse

logger = logging.getLogger(__name__)


@app.route('/api/impressions', methods=['POST'])
def add_impression():
    """
    Receive impression data from Nicla device (emotion + optional frame)
    
    See ImpressionRequest in api/models.py for detailed documentation.
    
    Expected JSON payload:
    {
        "device_id": "1",
        "emotion": "happy",
        "frame_data": "base64_string" (optional)
    }
    """
    data = request.get_json()
    
    device_id = data.get('device_id')
    emotion = data.get('emotion')
    frame_data = data.get('frame_data')  # Optional: Base64 encoded frame
    
    # Validate required fields
    if not device_id or not emotion:
        return jsonify({'error': 'Missing required fields (device_id, emotion)'}), 400
    
    # Validate device is one of our known Nicla
    if device_id not in devices:
        return jsonify({'error': f'Unknown device: {device_id}'}), 403
    
    # Store impression with server timestamp
    impression = {
        'device_id': device_id,
        'emotion': emotion,
        'timestamp': get_timestamp_ms()
    }
    
    # Add frame data in the impression array if provided
    if frame_data:
        impression['frame_data'] = frame_data
    
    # Format timestamp for logging - calculate relative time from session start
    session_start = current_session.get('start_time', impression['timestamp'])
    relative_ms = impression['timestamp'] - session_start
    relative_seconds = relative_ms / 1000
    minutes = int(relative_seconds // 60)
    seconds = int(relative_seconds % 60)
    formatted_time = f"{minutes}:{seconds:02d}"
    
    # Log with frame info
    has_frame = 'frame_data' in impression
    frame_size = len(impression.get('frame_data', '')) if has_frame else 0
    logger.info(f"Storing impression at {formatted_time} (absolute timestamp: {impression['timestamp']}, relative: {relative_ms}ms, emotion: {emotion}, device: {device_id}, frame: {has_frame}, frame_size: {frame_size} bytes)")
    
    impressions.append(impression)
    
    # Broadcast to all connected clients via WebSocket
    socketio.emit('new_impression', impression)
    
    return jsonify({
        'status': 'received',
        'impression_count': len(impressions),
        'has_frame': has_frame
    }), 201

