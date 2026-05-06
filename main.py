from flask import Flask, request, jsonify
import requests
import re
import time

app = Flask(__name__)

# --- आपकी डिटेल्स ---
ID_INSTANCE = '7107598578' 
API_TOKEN_INSTANCE = '6fabd2c755cf46839d41aabff98ac0663222113d6e564126bf' 

# --- दो अलग ग्रुप्स की ID ---
GROUP_CHD = '120363424995994566@g.us' # चंडीगढ़ ग्रुप
GROUP_PUNJAB = '120363410536552316@g.us' # पंजाब ग्रुप ID यहाँ डालें
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

        # --- [BLOCKER: EXCHANGE/XCHANGE] ---
        # Agar msg mein xchange, exchange ya exxx hai toh turant block
        block_keywords = r"(?i)(xchange|exchange|exxx)"
        if re.search(block_keywords, text):
            return jsonify({"status": "blocked_exchange_keyword"}), 200

        sender_chat_id = data.get('senderData', {}).get('chatId', '')
        # अपने ही ग्रुप्स के मैसेज दोबारा फॉरवर्ड न हों
        if sender_chat_id in [GROUP_CHD, GROUP_PUNJAB]:
            return jsonify({"status": "ignored"}), 200

        # --- फ़िल्टर्स ---
        city_chd = r"(chandigarh|chd|mohali|kharar|zirakpur|panchkula|punchkula|kurali|ropar|roper|pkl|morinda|kharad|chamkaur|dera\s*bassi|new\s*chandigarh)"
        city_punjab = r"(patiala|ludhiana|ldh|lud|jagraon|jalandhar|jld|amritsar|asr|khanna|sirhind|phagwara|rajpura|nabha|moga|barnala|kapurthala|phagwara|phillaur|sangrur|samrala|pathankot|jammu)"
        city_b_regex = r"(delhi|delhi\s*airport|noida|gurgaon|gurugram|faridabad|ghaziabad|janakpuri|mahipalpur|manali|shimla)"
        
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

        # --- [2. SMART ROUTE CHECK] ---
        chd_route = re.search(f"(?i)({city_chd}.{{0,50}}{city_b_regex})|({city_b_regex}.{{0,50}}{city_chd})", text, re.DOTALL)
        punjab_route = re.search(f"(?i)({city_punjab}.{{0,50}}{city_b_regex})|({city_b_regex}.{{0,50}}{city_punjab})", text, re.DOTALL)

        clean_text = re.sub(r'[^\w\s,]', ' ', text)
        clean_text = re.sub(r'\b(\w+)(?:\s+\1\b)+', r'\1', clean_text, flags=re.IGNORECASE)
        clean_text = " ".join(clean_text.split())

        msg_length = len(clean_text)
        half_point = msg_length // 2
        first_half = clean_text[:half_point]

        thirty_limit = int(msg_length * 0.30)
        first_30_text = clean_text[:thirty_limit]
        valid_words_pattern = r"(need|pickup|picup|drop|pick|pik|pikup|pic|updown|duty|up\s*down)"
        status_words_pattern = r"(available|avail)" 
        is_valid_combo = re.search(fr"(?i)\b{valid_words_pattern}\b\s*\b{status_words_pattern}\b", first_30_text)

        is_booking_confirmed = re.search(cars, first_half, re.IGNORECASE) and re.search(need_words, first_half, re.IGNORECASE)

        if re.search(junk_words, first_half, re.DOTALL):
            if not (is_booking_confirmed or is_valid_combo):
                return jsonify({"status": "starting_junk_ignored"}), 200

        # Final Decision
        if is_booking_confirmed:
            target_group = None
            signature = ""

            if chd_route:
                target_group = GROUP_CHD
                signature = "_*Taxi Deal Hub Chandigarh*_"
            elif punjab_route:
                target_group = GROUP_PUNJAB
                signature = "_*Taxi Deal Hub Punjab*_"

            if target_group:
                current_time = time.time()
                message_key = text.strip().lower()

                if message_key in sent_messages_cache:
                    if (current_time - sent_messages_cache[message_key]) < 600:
                        return jsonify({"status": "duplicate_ignored"}), 200
                
                sent_messages_cache[message_key] = current_time
                
                # --- [CHECK FOR EXISTING HEADER/FOOTER] ---
                # Agar msg me pehle se Alert aur Signature hai toh extra format nahi lagayenge
                if "NEW BOOKING ALERT" in text.upper() and ("Taxi Deal Hub" in text):
                    final_msg = text
                else:
                    fixed_text = re.sub(r'(\d)\s+(\d)', r'\1\2', text)
                    fixed_text = re.sub(r'(\d)-(\d)', r'\1\2', fixed_text)
                    final_msg = f"🔔 *NEW BOOKING ALERT* 🚖\n\n{fixed_text}\n\n{signature}"

                print(f"Sending to {target_group}...")
                send_raw_to_group(final_msg, target_group)

    return jsonify({"status": "success"}), 200

def send_raw_to_group(final_text, target_group):
    url = f"https://api.green-api.com/waInstance{ID_INSTANCE}/sendMessage/{API_TOKEN_INSTANCE}"
    payload = {
        "chatId": target_group,
        "message": final_text
    }
    response = requests.post(url, json=payload)
    print(f"DEBUG: Response Code: {response.status_code}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
