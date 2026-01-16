import os
import time
import json
import yt_dlp
import google.generativeai as genai
from dotenv import load_dotenv

# --- 1. Setup & Configuration ---
# Load the GOOGLE_API_KEY from your .env file
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("Error: GOOGLE_API_KEY not found in .env file.")
    exit(1)

genai.configure(api_key=api_key)

# Using gemini-1.5-flash as it's fast and cost-effective for video tasks
model = genai.GenerativeModel(model_name="gemini-2.5-flash")

TEMP_VIDEO_FILE = "temp_instagram_reel.mp4"


# --- 2. Functions ---

def get_metadata(url):
    """Fetches metadata without downloading the video."""
    print("\n[1/3] Fetching metadata...")
    ydl_opts = {
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        # 'extract_flat' gets metadata quickly without detailed analysis
        'extract_flat': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            # Filter for the most useful fields
            metadata = {
                "title": info.get('title'),
                "description": info.get('description'),
                "uploader": info.get('uploader'),
                "upload_date": info.get('upload_date'),
                "view_count": info.get('view_count'),
                "like_count": info.get('like_count'),
                "thumbnail_url": info.get('thumbnail'),
                "original_url": url
            }
            return metadata
    except Exception as e:
        print(f"Error fetching metadata: {e}")
        return None


def download_video(url):
    """Downloads the video to a temporary file."""
    print("\n[2/3] Downloading video file...")
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': TEMP_VIDEO_FILE,
        'quiet': True,
        'no_warnings': True,
    }
    try:
        # Delete temp file if it already exists from a previous run
        if os.path.exists(TEMP_VIDEO_FILE):
            os.remove(TEMP_VIDEO_FILE)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print("Download complete.")
        return TEMP_VIDEO_FILE
    except Exception as e:
        print(f"Error downloading video: {e}")
        return None


def generate_tags_with_gemini(video_path):
    """Uploads video to Gemini and generates tags."""
    print("\n[3/3] Processing with Gemini AI...")

    # 1. Upload the video file to Gemini
    print("Uploading file to Google AI Studio...")
    video_file = genai.upload_file(path=video_path)
    print(f"Upload complete. File URI: {video_file.uri}")

    # 2. Wait for the file to be processed
    print("Waiting for video processing to complete...")
    while video_file.state.name == "PROCESSING":
        print(".", end="", flush=True)
        time.sleep(2)
        video_file = genai.get_file(video_file.name)
    print(f"\nProcessing complete. State: {video_file.state.name}")

    if video_file.state.name == "FAILED":
        print("Video processing failed.")
        return None

    # 3. Send the prompt to the model
    prompt = """
    You are an expert content tagger. Watch this Instagram Reel and generate a JSON object containing a list of 10-15 highly relevant and searchable tags.

    The tags should describe:
    - The main topic or subject.
    - Key objects or visual elements visible in the video.
    - The general mood or vibe.
    - The specific niche or category (e.g., "coding tutorial", "fitness motivation", "travel vlog").

    Return ONLY the JSON object.
    Example format:
    {
        "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
    }
    """
    print("Generating tags...")
    response = model.generate_content([prompt, video_file])

    # 4. Cleanup: Delete the file from Gemini and local storage
    print("Cleaning up temporary files...")
    genai.delete_file(video_file.name)
    if os.path.exists(video_path):
        os.remove(video_path)

    return response.text


# --- 3. Main Execution Loop ---
if __name__ == "__main__":
    # Use the URL that was giving you issues
    url = "https://www.instagram.com/reel/DQrPM6jEkAd/?igsh=MWtkem1iamVoaTN3"

    # A. Get and print metadata
    metadata = get_metadata(url)
    if metadata:
        print("\n--- EXTRACTED METADATA ---")
        # Pretty-print the dictionary
        print(json.dumps(metadata, indent=2))

    # B. Download video
    video_path = download_video(url)

    # C. Generate and print tags if download was successful
    if video_path:
        gemini_response = generate_tags_with_gemini(video_path)
        if gemini_response:
            print("\n--- GEMINI GENERATED TAGS ---")
            try:
                # Clean up the response text to ensure it's valid JSON
                cleaned_text = gemini_response.strip().removeprefix("```json").removesuffix("```").strip()
                tags_json = json.loads(cleaned_text)
                print(json.dumps(tags_json, indent=2))
            except json.JSONDecodeError:
                print("Could not parse JSON response directly. Here is the raw output:")
                print(gemini_response)