#!/bin/bash

# Configuration
INPUT_DIR="docs/assets/frames"
OUTPUT_DIR="docs/assets"
OUTPUT_FILE="workflow.gif"

echo "--- Building Hero Storyboard ---"

# Check if frames exist
if [ ! -d "$INPUT_DIR" ]; then
    echo "Error: Directory $INPUT_DIR not found. Please place frame1.png, frame2.png, frame3.png there."
    exit 1
fi

# Generate the GIF using ImageMagick
# -delay 100 = 1 second per frame
# -loop 0 = infinite loop
convert -delay 100 -loop 0 \
    "$INPUT_DIR/frame1.png" \
    "$INPUT_DIR/frame2.png" \
    "$INPUT_DIR/frame3.png" \
    "$OUTPUT_DIR/$OUTPUT_FILE"

echo "Done! Generated: $OUTPUT_DIR/$OUTPUT_FILE"


# Configuration
INPUT_DIR="docs/assets/frames"
OUTPUT_DIR="docs/assets"
OUTPUT_FILE="workflow.gif"
