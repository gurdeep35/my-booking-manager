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
        city_a_regex = r"(chandigarh|chd|mohali|kharar|zirakpur|panchkula|punchkula|kurali|ropar|roper|pkl|morinda|kharad|chamkaur|dera\s*bassi|new\s*chandigarh)"
        city_b_regex = r"(delhi|delhi\s*airport|noida|gurgaon|gurugram|faridabad|ghaziabad|janakpuri|mahipalpur)"
        
        cars = r"(?i)\b(sedan|ertiga|innova|crysta|etios|Artiga|dzire|ertica|dzier|crista|eartiga|suv|Ertika|aura|rumion|dsire|small\s*car|kia\s*carens)\b"
        need_words = r"(?i)\b(need|pickup|picup|drop|pick|pik|pikup|pic|updown|duty|up\s*down)\b"
        junk_words = r"(?i)\b(free|khali|available|available\s*now|खाली|any\s*drop|any\s*pickup|any\s*drop/pickup|required)\b"

        # --- [1. SMART 2-TEXT-LINE 'FREE' BLOCKER] ---
        raw_lines = text.split('\n')
        lines_checked = 0
        for line in raw_lines:
            abc_only = re.sub(r'[^a-zA-Z]', '', line).lower()
            if abc_only:
                lines_checked += 1
                if "free" in abc_only:
                    return jsonify({"status": "blocked_free_in_top_lines"}), 200
                if lines_checked >= 2:
                    break

        # --- [2. SMART ROUTE CHECK (A और B शहर पास होने चाहिए)] ---
        route_pattern = f"(?i)({city_a_regex}.{{0,50}}{city_b_regex})|({city_b_regex}.{{0,50}}{city_a_regex})"
        has_smart_route = re.search(route_pattern, text, re.DOTALL)

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
        is_booking_confirmed = re.search(cars, first_half, re.IGNORECASE) and re.search(need_words, first_half, re.IGNORECASE)

        # 3. जंक फिल्टर (सुधरा हुआ)
        if re.search(junk_words, first_half, re.DOTALL):
            if is_booking_confirmed or is_valid_combo:
                pass
            else:
                return jsonify({"status": "starting_junk_ignored"}), 200

        # 4. फाइनल रूट और बुकिंग सेंडिंग
        if has_smart_route and is_booking_confirmed:
            
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
    
    # [Smart Number Fixer]: यह मैसेज के अंदर से नंबरों के बीच के स्पेस और डैश हटाएगा 
    # (98881 23456 -> 9888123456)
    # यह कोई wa.me लिंक नहीं जोड़ेगा, सिर्फ नंबरों को सटा देगा
    fixed_text = re.sub(r'(\d)\s+(\d)', r'\1\2', message_text)
    fixed_text = re.sub(r'(\d)-(\d)', r'\1\2', fixed_text)
    
    payload = {
        "chatId": TARGET_GROUP_ID,
        "message": f"🔔 *NEW BOOKING ALERT* 🚖\n\n{fixed_text}\n\n_*Taxi Deal Hub Chandigarh*_"
    }
    
    response = requests.post(url, json=payload)
    print(f"DEBUG: Sent to group. Response Code: {response.status_code}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
