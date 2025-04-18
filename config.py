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

def clean_data(data):
    #extract basic profile details
    structured_data = {
        "username": data.get("username", "N/A"),
        "First_Name": data.get("firstName", "N/A"),
        "Last_Name": data.get("lastName", "N/A"),
        "Summary": data.get("summary", "N/A"),
        "Headline": data.get("headline", "N/A"),
        "Location": data.get("geo", []).get("country", "city"),
        "Certifications": data.get("certifications", []),
        "Projects": data.get("projects", "N/A")
    }
    #extract education
    education_list = data.get("educations", [])
    structured_data["Education"] =[{
        "fieldOfStudy": education.get("fieldOfStudy", "N/A"),
        "Degree":education.get("degree", "N/A"),
        "University": education.get("schoolName", "N/A"),
        "Start":education.get("start", []).get("year"),
        "End":education.get("end", []).get("year", "N/A")
    }
    for education in education_list                               ]
    #extract experiences
    experience_list = data.get("position", [])
    structured_data["Experience"] = [{
        "Title": exp.get("title", "N/A"),
        "Company": exp.get("companyName", "N/A"),
        "Duration": exp.get("duration", "N/A"),
        "Responsibilities": exp.get("description", [])
    }
    for exp in experience_list                                 ]
    #extract skills
    skill_list = data.get("skills", [])
    structured_data["Skills"] = [skill.get("name", "N/A") for skill in skill_list]
    
    return structured_data
     
def generate_ai_message(user_data,target_data,intent, attributes=None, character_length=200):
    if attributes is None:
        attributes = ['experience', 'skills', 'education', 'location']
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

def generate_voice_script(user_data, target_data, intent):
    prompt2 = f'''
You are an expert at crafting **natural-sounding, conversational LinkedIn connection messages** that can be spoken aloud in **30-40 seconds**.  


Analyze the user profile and the target profile, then generate a **short, engaging voice script** that:  
1. **Sounds natural when spoken** (avoid robotic or overly formal tones).  
2. **Mentions 1-2 key commonalities** (shared industry, skills, interests, or mutual connections).  
3. **Aligns with the user's intent** (e.g., networking, collaboration, job opportunities).  
4. **Ends with a clear call-to-action** (e.g., "Would love to chat!" or "Let’s connect!").  

### **Rules:**  
- **Length:** ~50-80 words (easily spoken in 30-40 sec).  
- **Tone:** Professional but warm (like a quick elevator pitch).  
- **No fluff**—get to the point while sounding human.  

### **Input Data:**  
- **User Profile: {user_data} 
- **Target Profile:** {target_data}  
- **Intent:** {intent}  

Response Format: 
Directly output **only the script** (no intro or explanations). Example:  
> *"Hi [Name], I came across your profile and noticed we both work in [shared field]. Your experience at [Company] really stood out—especially your work on [specific detail]. I’d love to connect and exchange insights. Let me know if you’re open to a quick chat!"*  
'''
    message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1000,
    temperature=1,
    system="You are an expert in professional networking and relationship building.",
    messages=[{
        "role": "user",
        "content": prompt2
    }])

    return message.content[0].text
