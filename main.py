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
        city_a = r"(chandigarh|chd|mohali|kharar|zirakpur|panchkula|kurali|ropar|chamkaur)"
        city_b = r"(delhi|delhi\s*airport|noida|gurgaon|gurugram|faridabad|ghaziabad|janakpuri|mahipalpur)"
        cars = r"(sedan|ertiga|innova|crysta|etios|Artiga|dzire|ertica|crista|suv|Ertika|aura|rumion|dsire|smallcar|kiacarens)"
        
        need_words = r"(?i)(need|pickup|picup|drop|pick|pik|pikup|pic|updown|duty|up down)"
        junk_words = r"(?i)(free|khali|available|available now|खाली|any drop|any pickup|any drop/pickup)"

        # --- स्मार्ट डायनामिक हाफ-एरिया लॉजिक ---
        msg_length = len(text)
        half_point = msg_length // 2
        first_half = text[:half_point]

        # 1. सबसे पहले चेक करें: क्या शुरुआती आधे हिस्से में कचरा है?
        if re.search(junk_words, first_half, re.DOTALL):
            return jsonify({"status": "starting_junk_ignored"}), 200

        # 2. रूट चेकिंग (LINE-BY-LINE): 
        # यह चेक करेगा कि क्या शहर A और शहर B का आपस में तालमेल है
        if re.search(f"(?i)(?=.*{city_a})(?=.*{city_b})", text, re.DOTALL):
            
            # 3. अब गाड़ी और ज़रूरत (Need) को फर्स्ट हाफ में चेक करें
            if re.search(cars, text, re.IGNORECASE) and re.search(need_words, first_half, re.DOTALL):
                
                current_time = time.time()
                message_key = text.strip().lower()

                if message_key in sent_messages_cache:
                    if (current_time - sent_messages_cache[message_key]) < 600:
                        return jsonify({"status": "duplicate_ignored"}), 200
                
                sent_messages_cache[message_key] = current_time
                
                print("Clean booking found! Forwarding...")
                time.sleep(3) 
                
                sender_name = data.get('senderData', {}).get('senderName', 'Unknown')
                send_to_my_group(text, sender_name)

    return jsonify({"status": "success"}), 200

def send_to_my_group(message_text, sender_name):
    url = f"https://api.green-api.com/waInstance{ID_INSTANCE}/sendMessage/{API_TOKEN_INSTANCE}"
    
    payload = {
        "chatId": TARGET_GROUP_ID,
        "message": f"🔔 *NEW BOOKING ALERT* 🚖\n\n{message_text}\n\n_King Travel Chandigarh_"
    }
    
    response = requests.post(url, json=payload)
    print(f"DEBUG: Sent to group. Response Code: {response.status_code}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
