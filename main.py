from flask import Flask, request, jsonify
import requests
import re

app = Flask(__name__)

# --- अपनी असली डिटेल्स यहाँ भरें (पक्का करें कि ' ' लगे हैं) ---
ID_INSTANCE = '7107598578' 
API_TOKEN_INSTANCE = '8699796b89a048468a0c22ac1c6f3ac2c834805e647a4c779c' 
TARGET_GROUP_ID = '120363424995994566@g.us'
# --------------------------------------------------------

@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    data = request.get_json()
    
    if data.get('typeWebhook') in ['incomingMessageReceived', 'incomingGroupMessageReceived']:
        message_data = data.get('messageData', {})
        text = ""
        
        if 'textMessageData' in message_data:
            text = message_data['textMessageData'].get('textMessage', '')
        elif 'extendedTextMessageData' in message_data:
            text = message_data['extendedTextMessageData'].get('text', '')

        # लूप रोकने के लिए
        sender_chat_id = data.get('senderData', {}).get('chatId', '')
        if sender_chat_id == TARGET_GROUP_ID:
            return jsonify({"status": "ignored"}), 200

                # 1. रूट और गाड़ी के शब्द (चंडीगढ़ + दिल्ली + गाड़ी)
        route_pattern = r"(?i)(?=.*(chandigarh|chd|mohali|kharar|zirakpur|panchkula))(?=.*(delhi|dl|airport|noida|gurgaon|gurugram|faridabaad|ghaziabaad|janakpuri|mahipalpur))(?=.*(sedan|ertiga|innova|crysta|dzire|ertica|suv|aura|rumion|dsire|smallcar|kiacarens))"
        
        # 2. ज़रूरत वाले शब्द (इनका होना सबसे ज़रूरी है)
        need_words = r"(?i)(need|pickup|drop)"

        # 3. लॉजिक: रूट/गाड़ी सही हो AND ज़रूरत वाला शब्द भी ज़रूर हो
        if re.search(route_pattern, text) and re.search(need_words, text):
            # अगर ये दोनों शर्तें पूरी होती हैं, तो मैसेज फॉरवर्ड होगा (चाहे उसमें 'Free' लिखा हो या नहीं)
            sender_name = data.get('senderData', {}).get('senderName', 'Unknown')
            send_to_my_group(text, sender_name)


        if re.search(pattern, text):
            sender_name = data.get('senderData', {}).get('senderName', 'Unknown')
            send_to_my_group(text, sender_name)

    return jsonify({"status": "success"}), 200

def send_to_my_group(message_text, sender_name):
    # एकदम सही URL
    url = f"https://api.green-api.com/waInstance{ID_INSTANCE}/sendMessage/{API_TOKEN_INSTANCE}"
    
    payload = {
        "chatId": TARGET_GROUP_ID,
        "message": f"🔔 *New Booking Alert*\n\n👤 From: {sender_name}\n💬 Message: {message_text}"
    }
    
    # मैसेज भेजने की कोशिश और रिजल्ट चेक करना
    response = requests.post(url, json=payload)
    print(f"DEBUG: Green-API Response Code: {response.status_code}")
    print(f"DEBUG: Green-API Response Body: {response.text}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
