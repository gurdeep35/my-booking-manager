from flask import Flask, request, jsonify
import requests
import re

app = Flask(__name__)

# --- अपनी डिटेल्स यहाँ भरें (Single Quotes ' ' के अंदर) ---
ID_INSTANCE = '7107598578'  # आपका Green-API Instance ID
API_TOKEN_INSTANCE = '8699796b89a048468a0c22ac1c6f3ac2c834805e647a4c779c' 
TARGET_GROUP_ID = '120363424995994566@g.us'
# ---------------------------------------------------

@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    data = request.get_json()
    
    # चेक करना कि मैसेज आया है (Group या Personal)
    if data.get('typeWebhook') in ['incomingMessageReceived', 'incomingGroupMessageReceived']:
        
        # मैसेज का टेक्स्ट निकालना
        message_data = data.get('messageData', {})
        text = ""
        
        # Normal Text Message
        if 'textMessageData' in message_data:
            text = message_data['textMessageData'].get('textMessage', '')
        # Extended Text Message (Reply or Link)
        elif 'extendedTextMessageData' in message_data:
            text = message_data['extendedTextMessageData'].get('text', '')

        # 1. LOOP PREVENTION: अगर मैसेज आपके अपने टारगेट ग्रुप से आ रहा है, तो उसे छोड़ दो
        sender_chat_id = data.get('senderData', {}).get('chatId', '')
        if sender_chat_id == TARGET_GROUP_ID:
            return jsonify({"status": "ignored"}), 200

        # 2. MASTER FILTER (सारे कीवर्ड्स जो आपने बोले थे):
        # इसमें चंडीगढ़/मोहाली + दिल्ली + गाड़ी के नाम + जरूरत/ड्रॉप सब कवर हैं
        pattern = r"(?i)(chandigarh|chd|delhi|dl|गाड़ी|need)"

        # अगर मैसेज में सारे कीवर्ड्स मिल जाते हैं
        if re.search(pattern, text):
            sender_name = data.get('senderData', {}).get('senderName', 'Unknown Sender')
            send_to_my_group(text, sender_name)

    return jsonify({"status": "success"}), 200

def send_to_my_group(message_text, sender_name):
    # मैसेज भेजने के लिए Green-API का URL
    url = f"https://green-api.com{ID_INSTANCE}/sendMessage/{API_TOKEN_INSTANCE}"
    
    payload = {
        "chatId": TARGET_GROUP_ID,
        "message": f"🔔 *New Booking Alert*\n\n👤 *From:* {sender_name}\n💬 *Details:* {message_text}"
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("Message forwarded successfully!")
        else:
            print(f"Failed to forward. Status: {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    # Render पर चलाने के लिए पोर्ट 5000 ज़रूरी है
    app.run(host='0.0.0.0', port=5000)
