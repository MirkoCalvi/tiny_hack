"""
Dashboard and analytics endpoints
"""
from flask import jsonify
from app import app, impressions, get_timestamp_ms, current_session
import logging

logger = logging.getLogger(__name__)


@app.route('/api/summary', methods=['GET'])
def get_summary():
    """Get summary analytics for dashboard"""
    if not impressions:
        return jsonify({
            'impressions': [],
            'total_count': 0,
            'frames_count': 0,
            'duration_ms': 0,
            'start_time': None,
            'video_url': current_session.get('video_url')
        })
    
    # Get the session start time (when job started)
    session_start = current_session.get('start_time')
    
    # If no session start, fall back to first impression (shouldn't happen normally)
    if session_start is None:
        session_start = impressions[0]['timestamp']
        logger.warning("No session start_time found! Using first impression timestamp as fallback.")
    
    first_impression_time = impressions[0]['timestamp']
    last_impression_time = impressions[-1]['timestamp']
    duration_ms = last_impression_time - first_impression_time
    
    # Format timestamps for logging - show relative time from session start
    def format_timestamp(ts_ms):
        relative_ms = ts_ms - session_start
        relative_seconds = relative_ms / 1000
        minutes = int(relative_seconds // 60)
        seconds = int(relative_seconds % 60)
        return f"{minutes}:{seconds:02d}"
    
    # Count impressions with frames
    impressions_with_frames = sum(1 for imp in impressions if 'frame_data' in imp)
    
    logger.info(f"Fetching summary - Total impressions: {len(impressions)}, Duration: {duration_ms}ms")
    logger.info(f"Impressions with frames: {impressions_with_frames}/{len(impressions)}")
    logger.info(f"Session start time: {session_start}")
    logger.info(f"First 3 impression times: {[format_timestamp(imp['timestamp']) for imp in impressions[:3]]} (absolute: {[imp['timestamp'] for imp in impressions[:3]]})")
    logger.info(f"Last 3 impression times: {[format_timestamp(imp['timestamp']) for imp in impressions[-3:]]} (absolute: {[imp['timestamp'] for imp in impressions[-3:]]})")
    
    return jsonify({
        'impressions': impressions,
        'total_count': len(impressions),
        'frames_count': impressions_with_frames,
        'duration_ms': duration_ms,
        'start_time': session_start,  # Return session start, not first impression!
        'video_url': current_session.get('video_url')
    })


@app.route('/api/debug/impressions', methods=['GET'])
def debug_impressions():
    """
    DEBUG ENDPOINT - Get all impressions with human-readable timestamps
    Shows timestamp relative to video start (e.g., "1:23" = 1 minute 23 seconds from start)
    """
    if not impressions:
        return jsonify({
            'message': 'No impressions in memory',
            'impressions': [],
            'total_count': 0,
            'video_url': current_session.get('video_url')
        })
    
    # Get the session start time (when job started)
    session_start = current_session.get('start_time')
    
    # If no session start, fall back to first impression
    if session_start is None:
        session_start = impressions[0]['timestamp']
        logger.warning("No session start_time found! Using first impression timestamp as fallback.")
    
    # Format timestamps - show relative time from session start
    def format_timestamp(ts_ms):
        relative_ms = ts_ms - session_start
        relative_seconds = relative_ms / 1000
        minutes = int(relative_seconds // 60)
        seconds = relative_seconds % 60
        return f"{minutes}:{seconds:06.3f}"
    
    # Create readable impressions with relative timestamps
    readable_impressions = []
    for imp in impressions:
        readable_imp = {
            'device_id': imp.get('device_id'),
            'emotion': imp.get('emotion'),
            'time_from_start': format_timestamp(imp['timestamp']),
            'timestamp_unix': imp['timestamp'],
            'has_frame': 'frame_data' in imp
        }
        readable_impressions.append(readable_imp)
    
    return jsonify({
        'impressions': readable_impressions,
        'total_count': len(impressions),
        'video_url': current_session.get('video_url'),
        'session_start': session_start
    })

