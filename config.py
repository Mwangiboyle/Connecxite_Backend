import os
from dotenv import load_dotenv
import requests
from anthropic import Anthropic
# Load environment variables
load_dotenv()

# RapidAPI credentials
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST")

# OpenAI API Key
API_KEY = os.getenv("api_key")
BASE_URL=os.getenv("base_url")

client = Anthropic(api_key=API_KEY
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
attributes = ['experience', 'skills', 'education', 'location']
def generate_ai_message(user_data,target_data,intent, attributes, character_length):
    prompt =f"""  
You are an expert in generating Linkedin connection messages.
your work is to Analyze both profiles and using the key {attributes} from both profiles and the {intent} of the connection, Generate one message with {character_length} characters that will
enhance a better connection. Focus on generating an excellent message and go directly to the message as your response
### Profiles:  
user profile: {user_data} 

Target connection profile: {target_data}  
"""  
    message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1000,
    temperature=1,
    system="You are an expert in professional networking and relationship building.",
    messages=[{
        "role": "user",
        "content": prompt
    }])
    return message.content[0].text
