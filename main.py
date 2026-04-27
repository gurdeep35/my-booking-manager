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
        route_pattern = r"(?i)(?=.*(chandigarh|chd|mohali|kharar|zirakpur|panchkula|kurali|ropar|chamkaur))(?=.*(delhi|delhi\s*airport|noida|gurgaon|gurugram|faridabad|ghaziabad|janakpuri|mahipalpur))(?=.*(sedan|ertiga|innova|crysta|etios|Artiga|dzire|ertica|crista|suv|Ertika|aura|rumion|dsire|smallcar|kiacarens))"
        
        # आपके द्वारा दिए गए अनिवार्य शब्द
        need_words = r"(?i)(need|pickup|picup|drop|pick|pik|pikup|pic|updown)"

        # विज्ञापन (कचरा) वाले शब्द
        junk_words = r"(?i)(free|khali|available|available now|खाली|any drop|any pickup|any drop/pickup)"

        # --- स्मार्ट डायनामिक हाफ-एरिया लॉजिक ---
        msg_length = len(text)
        half_point = msg_length // 2
        first_half = text[:half_point] # यह मैसेज का शुरुआती आधा हिस्सा है

        # 1. सबसे पहले चेक करें: क्या शुरुआती आधे हिस्से (First Half) में कचरा शब्द है?
        if re.search(junk_words, first_half, re.DOTALL):
            print("Junk found in the first half. Rejecting immediately.")
            return jsonify({"status": "starting_junk_ignored"}), 200

        # 2. अगर शुरुआत साफ है, तो मुख्य फ़िल्टर चेक करें
        if re.search(route_pattern, text, re.DOTALL):
            
            # बुकिंग तभी मानी जाएगी जब शुरुआती आधे हिस्से (First Half) में 'Need/Drop' शब्द हो
            if re.search(need_words, first_half, re.DOTALL):
                
                current_time = time.time()
                message_key = text.strip().lower()

                if message_key in sent_messages_cache:
                    if (current_time - sent_messages_cache[message_key]) < 600:
                        return jsonify({"status": "duplicate_ignored"}), 200
                
                sent_messages_cache[message_key] = current_time
                
                print("Clean booking found in first half! Forwarding...")
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
