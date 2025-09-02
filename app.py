import os
import requests
from flask import Flask, request

app = Flask(__name__)

# --- Configuration ---
# Load environment variables. These are kept secret and set on your hosting platform.
# NEVER write these values directly in your code.
PAGE_ACCESS_TOKEN = os.environ.get('PAGE_ACCESS_TOKEN')
VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# URLs for the APIs we will be calling
MESSENGER_API_URL = f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

@app.route('/', methods=['GET'])
def home():
    """A simple route to check if the server is running."""
    return "Hello! Your Burmese Chatbot server is running."

@app.route('/webhook', methods=['GET'])
def webhook_verify():
    """
    This is the initial verification step from Meta.
    It checks if the VERIFY_TOKEN we set in the Meta App Dashboard matches.
    """
    if request.args.get('hub.mode') == 'subscribe' and request.args.get('hub.challenge'):
        if not request.args.get('hub.verify_token') == VERIFY_TOKEN:
            return 'Verification token mismatch', 403
        return request.args['hub.challenge'], 200
    return 'Hello world', 200

@app.route('/webhook', methods=['POST'])
def webhook_handle():
    """
    This is the main endpoint that receives messages from Messenger.
    """
    data = request.get_json()
    if data['object'] == 'page':
        for entry in data['entry']:
            for messaging_event in entry['messaging']:
                # Check if the event is a message and not an echo
                if messaging_event.get('message') and not messaging_event['message'].get('is_echo'):
                    sender_id = messaging_event['sender']['id']
                    message_text = messaging_event['message']['text']
                    
                    # Get the bot's response from Gemini
                    bot_response = get_gemini_response(message_text)
                    
                    # Send the response back to the user
                    send_message(sender_id, bot_response)

    return 'ok', 200

def get_gemini_response(user_message):
    """
    Calls the Google Gemini API to get a fluent Burmese response.
    """
    # This is the "prompt". You can change it to give your bot a different personality.
    # We instruct it to act as a helpful assistant and always reply in Burmese.
    system_prompt = (
        "You are a friendly and helpful assistant for a Facebook page. "
        "Your main goal is to answer user questions accurately. "
        "You MUST always respond in natural, fluent Burmese (Myanmar language), "
        "regardless of the language of the user's question. Do not use English unless "
        "it is a brand name."
    )
    
    payload = {
        "contents": [{
            "parts": [{"text": f"{system_prompt}\n\nUser Question: {user_message}"}]
        }]
    }
    
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(GEMINI_API_URL, json=payload, headers=headers)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        
        # Extract the text from the Gemini response
        result = response.json()
        candidate = result.get("candidates", [{}])[0]
        content_part = candidate.get("content", {}).get("parts", [{}])[0]
        generated_text = content_part.get("text", "တောင်းပန်ပါတယ်၊ အဆင်မပြေဖြစ်သွားလို့ပါ။").strip()
        
        return generated_text
        
    except requests.exceptions.RequestException as e:
        print(f"Error calling Gemini API: {e}")
        return "တောင်းပန်ပါတယ်၊ ကျွန်တော့်မှာ အမှားအယွင်းတစ်ခုဖြစ်နေလို့ပါ။ ခဏနေ ပြန်ကြိုးစားပေးပါနော်။" # Default error message in Burmese
    except (KeyError, IndexError) as e:
        print(f"Error parsing Gemini response: {e}")
        print(f"Full Gemini Response: {response.text}")
        return "တောင်းပန်ပါတယ်၊ အဖြေရှာမတွေ့လို့ပါ။" # Default error message for parsing issues

def send_message(recipient_id, message_text):
    """
    Sends a text message back to the user via the Messenger Send API.
    """
    payload = {
        'messaging_type': 'RESPONSE',
        'recipient': {'id': recipient_id},
        'message': {'text': message_text}
    }
    
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(MESSENGER_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        print(f"Successfully sent message to {recipient_id}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending message to {recipient_id}: {e}")
        print(f"Response: {response.text}")

if __name__ == '__main__':
    # This allows the app to be run locally for testing
    app.run(debug=True)
