import os
import praw
import requests
from dotenv import load_dotenv

# Load API keys and environment variables
load_dotenv()
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Connect to Reddit using PRAW
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT
)

def extract_username(url):
    """Extracts the Reddit username from a profile URL."""
    parts = url.strip("/").split("/")
    return parts[-1]

def fetch_user_content(username, limit=50):
    """Fetches up to 'limit' posts and comments for the given Reddit username."""
    user = reddit.redditor(username)
    posts = []
    comments = []
    try:
        for submission in user.submissions.new(limit=limit):
            posts.append({
                "title": submission.title,
                "body": submission.selftext,
                "permalink": submission.permalink
            })
        for comment in user.comments.new(limit=limit):
            comments.append({
                "body": comment.body,
                "permalink": comment.permalink
            })
    except Exception as e:
        print(f"Error fetching data: {e}")
    return posts, comments

def build_persona_with_llama3(posts, comments):
    """
    Sends posts and comments to OpenRouter's Llama 3 model and gets back a user persona
    in a structured, visually rich style like the sample image.
    """
    # Prepare sample data for the prompt
    examples = []
    for post in posts[:5]:
        examples.append(f"Post: {post['title']} - {post['body']}\nURL: https://reddit.com{post['permalink']}")
    for comment in comments[:5]:
        examples.append(f"Comment: {comment['body']}\nURL: https://reddit.com{comment['permalink']}")
    content = "\n\n".join(examples)

    # Improved prompt for Llama 3
    prompt = f"""
You are an expert at building detailed, visually clear user personas from Reddit data.

Given the following Reddit posts and comments, create a structured user persona in the following format (mimicking the attached sample):

---
[Persona Name]

AGE: (if available)
OCCUPATION: (if available)
STATUS: (if available)
LOCATION: (if available)
TIER: (if you can infer, e.g. Early Adopter, Mainstream, etc.)
ARCHETYPE: (e.g. The Creator, The Explorer, etc.)

TRAITS:
- Practical / Adaptable / Spontaneous / Active (choose and explain based on evidence)

MOTIVATIONS:
- Convenience: (bar/score and cite evidence from posts/comments)
- Wellness: (bar/score and cite evidence)
- Speed: (bar/score and cite evidence)
- Preferences: (bar/score and cite evidence)
- Comfort: (bar/score and cite evidence)
- Dietary Needs: (bar/score and cite evidence)

PERSONALITY (rate on a scale or bar, and cite evidence):
- Introvert/Extrovert
- Intuition/Sensing
- Feeling/Thinking
- Perceiving/Judging

QUOTE:
A short quote that summarizes the user's attitude, using their own words if possible, or inferred from their writing.

BEHAVIOUR & HABITS:
- Bullet points describing user habits, each with a citation (URL) to the supporting post or comment.

FRUSTRATIONS:
- Bullet points listing user frustrations, each with a citation (URL).

GOALS & NEEDS:
- Bullet points listing user goals/needs, each with a citation (URL).

Cite the specific post or comment (by its URL) for each insight or characteristic.

Data to analyze:
{content}

Format your output clearly with headings and bullet points, as in the sample persona.
---

If any information is missing, leave it blank or mark as "Not specified".
    """

    # OpenRouter API endpoint and headers
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "meta-llama/llama-3-70b-instruct",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1200,
        "temperature": 0.7
    }

    # Make the API call
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        result = response.json()
        return result['choices'][0]['message']['content'].strip()
    else:
        print("Error from OpenRouter API:", response.text)
        return "Could not generate persona due to API error."

def save_persona(username, persona_text):
    """Saves the persona to outputs/username_persona.txt"""
    output_dir = "outputs"
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, f"{username}_persona.txt")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(persona_text)
    print(f"Persona saved to {filename}")

def main():
    url = input("Enter Reddit user profile URL: ").strip()
    username = extract_username(url)
    print(f"Fetching data for user: {username}...")

    posts, comments = fetch_user_content(username)
    print(f"Found {len(posts)} posts and {len(comments)} comments.")

    persona = build_persona_with_llama3(posts, comments)
    print("LLM response:")
    print(persona)

    save_persona(username, persona)
    print("Done!")

if __name__ == "__main__":
    main()
