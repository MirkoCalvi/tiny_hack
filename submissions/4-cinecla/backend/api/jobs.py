"""
Job management endpoints
"""
from flask import request, jsonify
from app import app, impressions, devices, socketio, current_session, get_timestamp_ms
import logging

logger = logging.getLogger(__name__)


@app.route('/api/jobs/start', methods=['POST'])
def start_job():
    """Start a new session - clears old impressions"""
    global impressions, current_session
    
    data = request.get_json()
    video_url = data.get('video_url')
    
    if not video_url:
        return jsonify({'error': 'Missing video_url'}), 400
    
    # Clear old impressions for fresh session
    impressions.clear()
    
    # Store session data
    current_session['video_url'] = video_url
    current_session['start_time'] = get_timestamp_ms()
    
    logger.info(f"Starting new session - Session start time: {current_session['start_time']}, Video: {video_url}")
    
    # Broadcast to all connected clients that impressions were cleared
    socketio.emit('impressions_cleared')
    
    return jsonify({
        'status': 'started',
        'devices': devices
    }), 201


@app.route('/api/jobs/stop', methods=['POST'])
def stop_job():
    """Stop the current session"""
    return jsonify({
        'status': 'stopped',
        'total_impressions': len(impressions)
    })

