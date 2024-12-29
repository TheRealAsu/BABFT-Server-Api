from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import requests
from io import BytesIO
import time

app = Flask(__name__)
CORS(app)

def process_image(image_url, resolution_factor):
    start_time = time.time()
    try:
        # Download the image from the URL
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()

        # Load the image
        img = Image.open(BytesIO(response.content))
        original_width, original_height = img.size

        # Calculate the new resolution
        new_width = max(1, original_width // resolution_factor)
        new_height = max(1, original_height // resolution_factor)

        # Check if the resulting image is too large
        if new_width * new_height > 1000000:  # Limit to 1 million pixels
            return {"error": "Resulting image too large. Please use a higher resolution factor."}

        # Resize the image
        img_resized = img.resize((new_width, new_height), Image.LANCZOS)

        # Convert the image to RGBA mode to handle transparency
        img_resized = img_resized.convert("RGBA")
        pixels = list(img_resized.getdata())

        # Extract RGB data
        rgb_output = []
        for y in range(new_height):
            if time.time() - start_time > 8:  # Check if we're approaching the 10s limit
                return {"error": "Processing time exceeded. Please use a higher resolution factor."}
            line = []
            for x in range(new_width):
                r, g, b, alpha = pixels[y * new_width + x]
                if alpha == 0:  # Invisible pixel
                    line.extend(["R", "R", "R"])
                else:  # Visible pixel
                    line.extend([r, g, b])
            line.extend(["B", "B", "B"])  # Add B, B, B at the end of the line
            rgb_output.append(", ".join(map(lambda v: str(v) if isinstance(v, int) else v, line)))

        return ", ".join(rgb_output)
    except requests.RequestException as e:
        return {"error": f"Error downloading image: {str(e)}"}
    except Image.UnidentifiedImageError:
        return {"error": "Unable to identify image file"}
    except Exception as e:
        return {"error": f"Error processing image: {str(e)}"}

@app.route('/api/process_image', methods=['GET', 'POST'])
def api():
    try:
        # Check if the method is GET or POST
        if request.method == 'POST':
            data = request.json or {}
        else:  # GET method
            data = request.args

        # Get the URL and resolution
        image_url = data.get('image_url')
        resolution_factor = data.get('resolution', "1")

        if not image_url:
            return jsonify({"error": "Missing image_url parameter"}), 400

        try:
            resolution_factor = int(resolution_factor)
            if resolution_factor <= 0 or resolution_factor > 100:
                raise ValueError
        except ValueError:
            return jsonify({"error": "Invalid resolution value. Use a positive integer between 1 and 100."}), 400

        # Process the image
        result = process_image(image_url, resolution_factor)

        if isinstance(result, dict) and "error" in result:
            return jsonify(result), 400

        return result
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

# Vercel serverless function handler
def handler(request):
    with app.request_context(request.environ):
        return app.full_dispatch_request()

