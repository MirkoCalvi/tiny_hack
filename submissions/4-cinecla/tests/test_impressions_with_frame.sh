#!/bin/bash

# Script to test impression with frame data
# Usage: ./test_impressions_with_frame.sh [emotion] [device]

BACKEND_URL="http://localhost:3002"
DEVICE_1="1"
DEVICE_2="2"

# Default values
EMOTION=${1:-"impressed"}
DEVICE_NUM=${2:-1}

# Select device
if [ "$DEVICE_NUM" = "1" ]; then
    DEVICE_ID=$DEVICE_1
else
    DEVICE_ID=$DEVICE_2
fi

# Create a small test frame (96x96 = 9216 bytes of zeros, Base64 encoded)
# This simulates what the Nicla would send
# For testing, we'll create a simple pattern: alternating 0 and 255
TEST_FRAME=$(python3 -c "
import base64
# Create a simple 96x96 test pattern
frame = bytes([i % 256 for i in range(96 * 96)])
print(base64.b64encode(frame).decode('utf-8'))
")

echo "🚀 Sending impression with frame..."
echo "   Device: Device $DEVICE_NUM ($DEVICE_ID)"
echo "   Emotion: $EMOTION"
echo "   Frame size: ${#TEST_FRAME} bytes (Base64)"
echo ""

# Test 1: Send WITH frame
echo "📦 Test 1: Sending impression WITH frame data"
curl -X POST "$BACKEND_URL/api/impressions" \
  -H "Content-Type: application/json" \
  -d "{\"device_id\": \"$DEVICE_ID\", \"emotion\": \"$EMOTION\", \"frame_data\": \"$TEST_FRAME\"}" \
  -w "\n📊 Status: %{http_code}\n\n"

sleep 1

# Test 2: Send WITHOUT frame (should still work)
echo "📦 Test 2: Sending impression WITHOUT frame data (backward compatible)"
curl -X POST "$BACKEND_URL/api/impressions" \
  -H "Content-Type: application/json" \
  -d "{\"device_id\": \"$DEVICE_ID\", \"emotion\": \"happy\"}" \
  -w "\n📊 Status: %{http_code}\n\n"

echo "✅ Tests completed!"
echo ""
echo "💡 Check your backend logs to see frame info"
