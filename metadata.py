import os
import time
import json
import yt_dlp
from google import genai
from dotenv import load_dotenv
from urllib.parse import urlparse
from newspaper import Article  # New library for articles
# /Users/geu/PycharmProjects/TagsGenerator
# --- 1. Setup & Configuration ---
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("Error: GOOGLE_API_KEY not found in .env file.")
    exit(1)

client = genai.Client(api_key=api_key)
MODEL_ID = "gemini-2.5-flash"  # Optimized for speed and multimodal tasks
TEMP_VIDEO_FILE = "temp_downloaded_content.mp4"


# --- 2. Helper Functions ---

def get_app_type(url):
    """Detects the platform from the URL domain."""
    domain = urlparse(url).netloc.lower()
    if any(x in domain for x in ['youtube.com', 'youtu.be']):
        return 'youtube'
    elif 'instagram.com' in domain:
        return 'instagram'
    else:
        return 'article'


from newspaper import Article, Config

from newspaper import Article, Config


def extract_article_text(url):
    """Downloads and parses an article using stealth headers to bypass 403 blocks."""
    try:
        # 1. Create a Browser-like Configuration
        config = Config()

        # This tells the server you are a real Chrome browser
        config.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

        # Some sites check where you 'came from'; setting a referer helps
        config.headers = {
            'Referer': 'https://www.google.com/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }

        config.request_timeout = 20  # Give slow news sites extra time

        # 2. Process the Article
        article = Article(url, config=config)
        article.download()

        # Check if download actually worked
        if article.download_state == 2:  # 2 means SUCCESS in newspaper3k
            article.parse()
            return f"Title: {article.title}\n\nContent: {article.text}"
        else:
            return "Error: Download failed or was blocked by the website's security."

    except Exception as e:
        return f"Error scraping article: {str(e)}"



# --- 3. Core Processing Logic ---

def process_content(url):
    app_type = get_app_type(url)
    print(f"\n[Detected Platform]: {app_type.upper()}")

    prompt = """
    Analyze the content provided. Generate a JSON object 
    containing a list of 10-15 highly relevant and searchable tags and a brief summary.

    Format:
    {
        "summary": "...",
        "tags": ["tag1", "tag2", "..."]
    }
    Return ONLY the JSON.
    """

    # --- ROUTING LOGIC ---

    # CASE 1: YOUTUBE
    if app_type == 'youtube':
        print("[1/1] Sending YouTube link directly to Gemini...")
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=[
                f"I am providing a specific YouTube link: {url}. Please access the actual content, transcript, and visual data for this specific video",
                prompt])
        return response.text

    # CASE 2: INSTAGRAM
    elif app_type == 'instagram':
        print(f"[1/3] Downloading {app_type} reel...")
        ydl_opts = {'format': 'mp4', 'outtmpl': TEMP_VIDEO_FILE, 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        print("[2/3] Uploading video to Gemini...")
        video_file = client.files.upload(
            file=TEMP_VIDEO_FILE,
            config={'mime_type': 'video/mp4'}
        )

        while video_file.state == "PROCESSING":
            print(".", end="", flush=True)
            time.sleep(2)
            video_file = client.files.get(name=video_file.name)

        print("\n[3/3] Generating tags...")
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=[prompt, video_file]
        )

        # Cleanup
        client.files.delete(name=video_file.name)
        if os.path.exists(TEMP_VIDEO_FILE):
            os.remove(TEMP_VIDEO_FILE)

        return response.text

    # CASE 3: ARTICLES (New logic)
    else:
        print("[1/2] Scraping article text...")
        article_content = extract_article_text(url)
        print(article_content)

        print("[2/2] Analyzing article with Gemini...")
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=[prompt, f"Please analyze this article content:\n\n{article_content}"]
        )
        return response.text


# --- 4. Execution ---
if __name__ == "__main__":
    link = input("Paste your link (YouTube/Instagram/Article): ")
    try:
        result = process_content(link)
        print("\n--- FINAL AI ANALYSIS ---")
        print(result)
    except Exception as e:
        print(f"Process failed: {e}")