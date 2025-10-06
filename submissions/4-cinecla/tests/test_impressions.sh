#!/bin/bash

# Script per testare l'invio di impressions al backend
# Usage: ./test_impressions.sh [emotion] [device]
# Example: ./test_impressions.sh impressed 1

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

echo "🚀 Sending impression..."
echo "   Device: Device $DEVICE_NUM ($DEVICE_ID)"
echo "   Emotion: $EMOTION"
echo ""

# Send the request
curl -X POST "$BACKEND_URL/api/impressions" \
  -H "Content-Type: application/json" \
  -d "{\"device_id\": \"$DEVICE_ID\", \"emotion\": \"$EMOTION\"}" \
  -w "\n\n📊 Status: %{http_code}\n"

echo ""
echo "✅ Request sent!"

