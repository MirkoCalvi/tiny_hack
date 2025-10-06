#!/usr/bin/env python3
"""
Nicla Vision Camera API Client
Sends camera feed and inference data from Nicla Vision to backend API
"""

import serial
import numpy as np
import sys
import time
import json
import binascii
import requests
import base64
import argparse
import random
from PIL import Image
import io

# Configuration
SERIAL_PORT = '/dev/cu.usbmodem11301'  # Change to your port
BAUD_RATE = 921600
CAMERA_WIDTH = 96    # Display width (matches neural network input)
CAMERA_HEIGHT = 96   # Display height (matches neural network input)
API_BASE_URL = 'http://localhost:3002'

# Hard-coded sorted impressions for --random mode
SORTED_IMPRESSIONS = [
    "neutral", "impressed", "impressed", "happy", "sad",
    "happy", "happy", "neutral", "neutral",
    "sad", "sad",
    "impressed", "impressed", "impressed", "impressed", "impressed",
    "happy", "happy", "happy", "happy", "happy"
]

# Global variable to track current position in the sorted impressions list
impression_index = 0

def get_next_sorted_impression():
    """Get the next impression from the sorted list, cycling back to start when exhausted"""
    global impression_index
    
    impression = SORTED_IMPRESSIONS[impression_index]
    impression_index = (impression_index + 1) % len(SORTED_IMPRESSIONS)
    
    return impression

def convert_frame_to_base64(frame_bytes):
    """Convert frame bytes to base64 PNG string"""
    # Convert raw grayscale bytes to numpy array
    frame_array = np.frombuffer(frame_bytes, dtype=np.uint8)
    
    # Reshape to 96x96 grayscale image (cropped and scaled top-right quarter)
    frame_array = frame_array.reshape((CAMERA_HEIGHT, CAMERA_WIDTH))
    
    # Create PIL Image from numpy array
    img = Image.fromarray(frame_array, mode='L')
    
    # Convert to PNG bytes
    png_buffer = io.BytesIO()
    img.save(png_buffer, format='PNG')
    png_bytes = png_buffer.getvalue()
    
    # Encode as base64
    return base64.b64encode(png_bytes).decode('utf-8')

def determine_emotion(output):
    """Determine emotion from inference output array"""
    if not output or len(output) == 0:
        return "unknown"
    
    # Simple emotion mapping based on output values
    # This is a placeholder - you may need to adjust based on your model's output format
    max_val = max(output)
    max_idx = output.index(max_val)
    
    # Basic emotion categories (adjust based on your model)
    emotions = ["neutral", "impressed", "happy", "sad"]
    
    if max_idx < len(emotions):
        return emotions[max_idx]
    else:
        return "unknown"

def send_impression_to_api(device_id, emotion, frame_data=None):
    """Send impression data to the backend API"""
    url = f"{API_BASE_URL}/api/impressions"
    
    payload = {
        "device_id": device_id,
        "emotion": emotion
    }
    
    if frame_data:
        payload["frame_data"] = frame_data
    
    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 201:
            print(f"✓ Impression sent successfully: {emotion}")
            return True
        else:
            print(f"✗ API error {response.status_code}: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"✗ API request failed: {e}")
        return False

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Nicla Vision Camera API Client')
    parser.add_argument('--device-id', required=True, help='Device ID to use for this camera')
    parser.add_argument('--serial-port', help='Serial port to use (e.g., /dev/cu.usbmodem11301)')
    parser.add_argument('--random', action='store_true', help='Send random emotions instead of real inference results')
    args = parser.parse_args()
    
    port = args.serial_port
    print(f"Using provided serial port: {port}")
    
    # Use CLI-provided device_id (only for API calls)
    device_id = args.device_id
    
    print(f"Connecting to {port} at {BAUD_RATE} baud...")
    print(f"Using device_id: {device_id}")
    print(f"API endpoint: {API_BASE_URL}/api/impressions")
    
    try:
        ser = serial.Serial(port, BAUD_RATE, timeout=1)
        time.sleep(2)  # Wait for Arduino to reset
        
        print("Connected! Enabling stream mode...")
        print("Press Ctrl+C to quit")
        
        # Enable streaming mode
        ser.write(b'2')
        time.sleep(0.5)
        
        frame_count = 0
        json_buffer = ""
        
        while True:
            # Read data from serial
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                json_buffer += data
                
                # Look for complete JSON objects
                while '\n' in json_buffer:
                    line, json_buffer = json_buffer.split('\n', 1)
                    line = line.strip()
                    
                    if line.startswith('{') and line.endswith('}'):
                        try:
                            # Parse JSON data
                            data = json.loads(line)
                            
                            # Extract inference results
                            inference = data.get('inference', {})
                            rc = inference.get('rc', -1)
                            time_us = inference.get('time_us', 0)
                            output = inference.get('output', [])
                            
                            # Extract and decode frame data
                            frame_hex = data.get('frame_data', '')

                            if frame_hex and rc == 0:  # Only process successful inferences
                                try:
                                    # Convert hex string back to bytes
                                    frame_bytes = binascii.unhexlify(frame_hex)
                                    
                                    # Convert frame to base64
                                    frame_base64 = convert_frame_to_base64(frame_bytes)
                                    
                                    # Determine emotion from output or use sorted impressions
                                    if args.random:
                                        # Use next impression from the sorted list
                                        emotion = get_next_sorted_impression()
                                    else:
                                        emotion = determine_emotion(output)
                                    
                                    # Send to API
                                    success = send_impression_to_api(device_id, emotion, frame_base64)
                                    
                                    frame_count += 1
                                    
                                    # Print inference results to console
                                    print(f"Frame {frame_count}: rc={rc}, time={time_us}us, emotion={emotion}, output_len={len(output)}")
                                    
                                except Exception as e:
                                    print(f"Error processing frame data: {e}")
                            
                        except json.JSONDecodeError as e:
                            print(f"JSON decode error: {e}")
                            print(f"Line: {line}")
            
            time.sleep(0.1)  # Small delay to prevent excessive CPU usage
        
    except serial.SerialException as e:
        print(f"Serial error: {e}")
        print(f"Make sure the Arduino is connected to {port}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        if 'ser' in locals() and ser.is_open:
            ser.write(b'2')  # Turn off streaming
            ser.close()
        print("Disconnected from Arduino")

if __name__ == "__main__":
    main()
