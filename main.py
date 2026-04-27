from flask import Flask, request, jsonify
import requests
import re
import time

app = Flask(__name__)

# --- आपकी डिटेल्स ---
ID_INSTANCE = '7107598578' 
API_TOKEN_INSTANCE = '8699796b89a048468a0c22ac1c6f3ac2c834805e647a4c779c' 
TARGET_GROUP_ID = '120363424995994566@g.us'
# ------------------

sent_messages_cache = {}

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

        sender_chat_id = data.get('senderData', {}).get('chatId', '')
        if sender_chat_id == TARGET_GROUP_ID:
            return jsonify({"status": "ignored"}), 200

        # --- फ़िल्टर्स ---
        route_pattern = r"(?i)(?=.*(chandigarh|chd|mohali|kharar|zirakpur|panchkula))(?=.*(delhi|delhi\s*airport|noida|gurgaon|gurugram|faridabad|ghaziabad|janakpuri|mahipalpur))(?=.*(sedan|ertiga|innova|crysta|etios|Artiga|dzire|ertica|crista|suv|Ertika|aura|rumion|dsire|smallcar|kiacarens))"
        need_words = r"(?i)(need|pickup|picup|drop|pick|pik|pikup|pic|updown)"

        if re.search(route_pattern, text) and re.search(need_words, text):
            current_time = time.time()
            message_key = text.strip().lower()

            if message_key in sent_messages_cache:
                if (current_time - sent_messages_cache[message_key]) < 600:
                    return jsonify({"status": "duplicate_ignored"}), 200
            
            sent_messages_cache[message_key] = current_time
            
            print("Message matched! Waiting 3 seconds before forwarding...")
            time.sleep(3) 
            
            sender_name = data.get('senderData', {}).get('senderName', 'Unknown')
            send_to_my_group(text, sender_name)

    return jsonify({"status": "success"}), 200

def send_to_my_group(message_text, sender_name):
    url = f"https://api.green-api.com/waInstance{ID_INSTANCE}/sendMessage/{API_TOKEN_INSTANCE}"
    
    payload = {
        "chatId": TARGET_GROUP_ID,
        "message": f"🔔 *NEW BOOKING ALERT* 🚕\n\n{message_text}\n\n_By King Travel Chd_"
    }
    
    response = requests.post(url, json=payload)
    print(f"DEBUG: Sent to group. Response Code: {response.status_code}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
