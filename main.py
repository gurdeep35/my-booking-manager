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

        # --- एकदम सटीक फ़िल्टर्स ---
        city_a = r"\b(chandigarh|chd|mohali|kharar|zirakpur|panchkula|punchkula|kurali|ropar|roper|morinda|kharad|chamkaur)\b"
        city_b = r"\b(delhi|delhi\s*airport|noida|gurgaon|gurugram|faridabad|ghaziabad|janakpuri|mahipalpur)\b"
        cars = r"(?i)\b(sedan|ertiga|innova|crysta|etios|Artiga|dzire|ertica|dzier|crista|eartiga|suv|Ertika|aura|rumion|dsire|small\s*car|kia\s*carens)\b"
        need_words = r"(?i)\b(need|pickup|picup|drop|pick|pik|pikup|pic|updown|duty|up\s*down)\b"
        # junk_words में 'available' और 'required' दोनों शामिल हैं
        junk_words = r"(?i)\b(free|khali|available|available\s*now|खाली|any\s*drop|any\s*pickup|any\s*drop/pickup|required)\b"

        # 1. क्लीनिंग
        clean_text = re.sub(r'[^\w\s,]', ' ', text)
        clean_text = re.sub(r'\b(\w+)(?:\s+\1\b)+', r'\1', clean_text, flags=re.IGNORECASE)
        clean_text = " ".join(clean_text.split())

        # 2. फर्स्ट हाफ निकालना
        msg_length = len(clean_text)
        half_point = msg_length // 2
        first_half = clean_text[:half_point]

        # --- स्मार्ट कंबो चेक ---
        thirty_limit = int(msg_length * 0.30)
        first_30_text = clean_text[:thirty_limit]
        valid_words_pattern = r"(need|pickup|picup|drop|pick|pik|pikup|pic|updown|duty|up\s*down)"
        status_words_pattern = r"(available|avail)" 
        is_valid_combo = re.search(fr"(?i)\b{valid_words_pattern}\b\s*\b{status_words_pattern}\b", first_30_text)

        # --- मुख्य स्मार्ट कंडीशन ---
        # पहले चेक करें कि क्या शहर मौजूद हैं
        has_route = re.search(f"(?i)(?=.*{city_a})(?=.*{city_b})", text, re.DOTALL)
        # फिर चेक करें कि क्या फर्स्ट हाफ में गाड़ी और ज़रूरत है
        is_booking_confirmed = re.search(cars, first_half, re.IGNORECASE) and re.search(need_words, first_half, re.IGNORECASE)

        # 3. जंक फिल्टर (सुधरा हुआ)
        if re.search(junk_words, first_half, re.DOTALL):
            # अगर बुकिंग की शर्तें फर्स्ट हाफ में मिल गई हैं या कॉम्बो मिल गया है, तो इग्नोर न करें (Pass होने दें)
            if is_booking_confirmed or is_valid_combo:
                pass
            else:
                return jsonify({"status": "starting_junk_ignored"}), 200

        # 4. फाइनल रूट और बुकिंग सेंडिंग
        if has_route and is_booking_confirmed:
            
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
        "message": f"🔔 *NEW BOOKING ALERT* 🚖\n\n{message_text}\n\n_Taxi Deal Hub Chandigarh_"
    }
    
    response = requests.post(url, json=payload)
    print(f"DEBUG: Sent to group. Response Code: {response.status_code}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
