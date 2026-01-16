import os
from google import genai
from dotenv import load_dotenv


# --- 1. Setup & Configuration ---
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("Error: GOOGLE_API_KEY not found in .env file.")
    exit(1)

client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="analyse this url https://www.youtube.com/watch?v=E20clulzE5E and tell summary",
)

print(response.text)