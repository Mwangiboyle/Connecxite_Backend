import os
from dotenv import load_dotenv
import requests
from openai import OpenAI
# Load environment variables
load_dotenv()

# RapidAPI credentials
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST")

# OpenAI API Key
OPENAI_API_KEY = os.getenv("api_key")
BASE_URL=os.getenv("base_url")
client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=BASE_URL
)

def get_profile_data(linkedin_url: str):
    """Fetch LinkedIn profile data using the provided URL."""
    url = "https://linkedin-api8.p.rapidapi.com/get-profile-data-by-url"
    querystring = {"url": linkedin_url}
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST
    }

    response = requests.get(url, headers=headers, params=querystring)
    return response.json()

def get_profile_posts(username: str):
    """Fetch LinkedIn posts using the extracted username."""
    url = "https://linkedin-api8.p.rapidapi.com/get-profile-posts"
    querystring = {"username": username}
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST
    }

    response = requests.get(url, headers=headers, params=querystring)
    return response.json()

def generate_ai_message(user_data,target_data):
    prompt = f"""
You are an AI designed to generate personalized LinkedIn connection messages.  
Your task is to analyze the key attributes of both profiles and create a tailored message that encourages connection.  

### Profiles:  
**Profile 1:**  
{user_data} 

**Profile 2:**  
{target_data}  
Do not mention what you are doing when generating the message just go direct to the message.

Use a friendly and professional tone.  
- Mention mutual connections if available.  
- Highlight shared interests or skills if relevant.  
- Keep the message concise (100-150 characters).  
- End with a clear call to action.  

If mutual connections or shared interests are not found, **skip those parts** rather than leaving placeholders.  

**Format Example:**  
"Hi [Target Name],  
I came across your profile and was impressed by your work in [Target Job Title/Field].  
As a [Your Job Title] in [Your Industry], I’d love to connect and exchange insights on [Relevant Topic].  
Looking forward to connecting,  
[Your Name]  
[Your Job Title] at [Your Company]  
[Your Location]"  

Now, generate the message based on the provided attributes.

"""
    messages= client.completions.create(
    model="deepseek/deepseek-r1-zero:free",
    prompt=prompt
    )
    return messages.choices[0].text