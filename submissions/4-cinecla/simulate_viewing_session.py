#!/usr/bin/env python3
"""
Simulate a complete viewing session with two Nicla devices
Generates test impressions with frame data for testing the dashboard
"""
import argparse
import base64
import time
import requests
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from PIL import Image

# Backend configuration
BACKEND_URL = "http://localhost:3002"
DEVICE_1 = "192.168.1.100"
DEVICE_2 = "192.168.1.101"

# Available emotions
EMOTIONS = [
    "happy", "sad", "surprised", "neutral", 
    "angry", "disgusted", "fearful", 
    "impressed", "not impressed"
]

def generate_test_frame(device_id: str, timestamp: int) -> str:
    """
    Generate a 96x96 test pattern PNG and encode to Base64
    Creates different patterns for different devices
    """
    # Create a new 96x96 grayscale image
    img = Image.new('L', (96, 96))
    pixels = img.load()
    
    for y in range(96):
        for x in range(96):
            # Different pattern for each device
            if device_id == DEVICE_1:
                # Horizontal gradient
                value = int((x / 96) * 255)
            else:
                # Vertical gradient
                value = int((y / 96) * 255)
            
            # Add some variation based on timestamp to show time progression
            variation = int((timestamp % 10) * 25)
            value = min(255, value + variation)
            
            pixels[x, y] = value
    
    # Convert to PNG and encode to Base64
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    png_bytes = buffer.getvalue()
    
    return base64.b64encode(png_bytes).decode('utf-8')


def get_emotion_timeline(duration_seconds: int):
    """
    Generate realistic emotion timeline for both viewers
    Returns dict of {second: (person1_emotion, person2_emotion)}
    """
    timeline = {}
    
    # Define story beats
    for second in range(duration_seconds):
        if second < 10:
            # Opening - neutral/mildly interested
            p1 = "neutral"
            p2 = "happy" if second > 5 else "neutral"
        
        elif 10 <= second < 30:
            # Exciting action scene
            p1 = "impressed" if second > 15 else "surprised"
            p2 = "impressed"
        
        elif 30 <= second < 50:
            # Emotional moment
            p1 = "sad" if second > 35 else "neutral"
            p2 = "sad"
        
        elif 50 <= second < 70:
            # Plot twist
            p1 = "surprised" if second < 55 else "impressed"
            p2 = "surprised"
        
        elif 70 <= second < 90:
            # Boring exposition
            p1 = "not impressed" if second > 80 else "neutral"
            p2 = "neutral"
        
        else:
            # Epic finale
            p1 = "impressed" if second > 100 else "happy"
            p2 = "impressed"
        
        timeline[second] = (p1, p2)
    
    return timeline


def get_video_duration(video_url: str) -> int:
    """
    Get the duration of a YouTube video in seconds using yt-dlp
    """
    try:
        import yt_dlp
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            duration = int(info.get('duration', 0))
            
            if duration > 0:
                minutes = duration // 60
                seconds = duration % 60
                print(f"📏 Video duration: {minutes}m {seconds}s ({duration} seconds)")
                return duration
            else:
                print("⚠️  Could not determine video duration, using default 120s")
                return 120
    except ImportError:
        print("⚠️  yt-dlp not installed, using default duration of 120s")
        print("   Install with: pip install yt-dlp")
        return 120
    except Exception as e:
        print(f"⚠️  Failed to get video duration: {e}")
        print("   Using default duration of 120s")
        return 120


def start_job(video_url: str) -> bool:
    """Start a new viewing session"""
    print(f"🎬 Starting new session with video: {video_url}")
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/jobs/start",
            json={"video_url": video_url},
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        print("✅ Session started successfully")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to start session: {e}")
        return False


def send_impression(device_id: str, emotion: str, frame_data: str) -> bool:
    """Send a single impression to the backend"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/impressions",
            json={
                "device_id": device_id,
                "emotion": emotion,
                "frame_data": frame_data
            },
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to send impression: {e}")
        return False


def simulate_session(video_url: str, duration_seconds: int = None):
    """
    Simulate a complete viewing session in real-time
    
    Args:
        video_url: YouTube URL to use for the session
        duration_seconds: Length of video in seconds (auto-detected if None)
    """
    # Get video duration if not provided
    if duration_seconds is None:
        duration_seconds = get_video_duration(video_url)
    
    # Start the job
    if not start_job(video_url):
        return
    
    print(f"\n📹 Simulating {duration_seconds} seconds of viewing in real-time...")
    print(f"⏱️  Sending 1 impression per second from each device (parallel)")
    print(f"⏱️  Total runtime: ~{duration_seconds} seconds")
    print()
    
    # Get emotion timeline
    timeline = get_emotion_timeline(duration_seconds)
    
    total_impressions = duration_seconds * 2  # 2 devices
    sent_count = 0
    sent_count_lock = threading.Lock()
    
    start_time = time.time()
    
    # Send impressions for each second
    for second in range(duration_seconds):
        tick_start = time.time()
        
        p1_emotion, p2_emotion = timeline[second]
        
        # Generate frames
        p1_frame = generate_test_frame(DEVICE_1, second)
        p2_frame = generate_test_frame(DEVICE_2, second)
        
        # Send both impressions in parallel using threads
        def send_p1():
            nonlocal sent_count
            if send_impression(DEVICE_1, p1_emotion, p1_frame):
                with sent_count_lock:
                    sent_count += 1
        
        def send_p2():
            nonlocal sent_count
            if send_impression(DEVICE_2, p2_emotion, p2_frame):
                with sent_count_lock:
                    sent_count += 1
        
        # Execute both sends in parallel
        with ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(send_p1)
            future2 = executor.submit(send_p2)
            # Wait for both to complete
            future1.result()
            future2.result()
        
        # Progress indicator
        if (second + 1) % 10 == 0 or second == duration_seconds - 1:
            progress = ((second + 1) / duration_seconds) * 100
            elapsed = time.time() - start_time
            print(f"  [{elapsed:6.1f}s elapsed] {second + 1}s / {duration_seconds}s ({progress:.0f}%) - "
                  f"P1: {p1_emotion}, P2: {p2_emotion}")
        
        # Wait for the remainder of the second to maintain 1 call per second rate
        if second < duration_seconds - 1:
            tick_elapsed = time.time() - tick_start
            sleep_time = max(0, 1.0 - tick_elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    total_elapsed = time.time() - start_time
    print(f"\n✅ Session complete!")
    print(f"📊 Sent {sent_count} impressions ({sent_count // 2} per device)")
    print(f"⏱️  Total time: {total_elapsed:.1f}s")
    print(f"🌐 Open dashboard: http://localhost:5173/dashboard")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Simulate a viewing session with test data in real-time (1 call/second/device)"
    )
    parser.add_argument(
        "--video",
        default="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        help="YouTube video URL (default: test video)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=None,
        help="Override video duration in seconds (default: auto-detect from YouTube)"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("  🎥 Cinema Impressions - Real-time Session Simulator")
    print("=" * 60)
    print()
    
    simulate_session(args.video, args.duration)


if __name__ == "__main__":
    main()
