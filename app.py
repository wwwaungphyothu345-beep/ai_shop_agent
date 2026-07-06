import os
from flask import Flask, request, jsonify
import requests
import json
import threading

app = Flask(__name__)

PAGE_ACCESS_TOKEN = "EAAWTc0UsYPgBR45NIFxOFGnOPn8ji8WlcseZAF483nv1I8VoRXa3ryPUyBLsclEgEGf3hZBlZASNZAnssvA7PnIBg0paS4zBVu7CmdTrqOS21zTpUSgIXDAVxT8UoF6seZAZB6mtkUeEkAdoSWhfPfJLUdzYnmxBZAynxW1OJvvk78FySknSOZA33MIGRzMLPh45OBH1WKwvIwZDZD"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbw_22BeUhWNShR1K_oGoIRJZ3_uhyLZmlenbghGsSMn1ar3pLtBoHjHvdoV74T5TbJtmQ/exec"

def send_fb_message(recipient_id, text_reply):
    try:
        url = f"https://graph.facebook.com/v21.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
        payload = {"recipient": {"id": str(recipient_id)}, "message": {"text": text_reply}}
        res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
        print(f"📡 FB SEND STATUS: {res.status_code}")
    except Exception as e:
        print(f"❌ FB SEND EXCEPTION: {e}")

def call_google_script(action, extra_data=None):
    try:
        payload = {"action": action}
        if extra_data: payload.update(extra_data)
        res = requests.post(SCRIPT_URL, headers={"Content-Type": "application/json"}, data=json.dumps(payload), timeout=10)
        if res.status_code == 200: return res.json()
    except Exception as e:
        print(f"⚠️ Sheet Sync Warning ({action}): {e}")
    return None

def ask_gemini_agent(system_prompt, user_msg, chat_history):
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key: return "ERROR_API_KEY_MISSING"
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        formatted_contents = []
        for chat in chat_history[-6:]:
            formatted_contents.append({
                "role": "user" if chat["role"] == "user" else "model",
                "parts": [{"text": chat["text"]}]
            })
        formatted_contents.append({"role": "user", "parts": [{"text": user_msg}]})
        
        payload = {
            "contents": formatted_contents,
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "generationConfig": {"temperature": 0.4}
        }
        res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=12)
        if res.status_code == 200:
            return res.json()['candidates'][0]['message']['parts'][0]['text']
    except Exception as e:
        print(f"❌ Gemini Exception: {e}")
    return "ERROR_GEMINI_FAIL"

def process_async_message(sender_id, customer_msg):
    try:
        prod_res = call_google_script("read_products")
        cod_res = call_google_script("read_cod")
        setting_res = call_google_script("read_setting")
        
        products = (prod_res.get("data", []) if prod_res else []) or []
        cod_cities = (cod_res.get("data", []) if cod_res else []) or []
        settings = (setting_res.get("data", {}) if setting_res else {}) or {}

        shop_context = f"သင်သည် ယဉ်ကျေးပျူငှာသော မြန်မာ AI Shop Assistant တစ်ဦးဖြစ်သည်။\nProducts: {json.dumps(products, ensure_ascii=False)}\nCOD Cities: {', '.join(cod_cities)}\nSettings: {json.dumps(settings, ensure_ascii=False)}"

        if sender_id not in app.chat_memory: app.chat_memory[sender_id] = []
        ai_reply = ask_gemini_agent(shop_context, customer_msg, app.chat_memory[sender_id])
        
        if ai_reply == "ERROR_API_KEY_MISSING":
            send_fb_message(sender_id, "⚠️ Render Config Error: GEMINI_API_KEY မတွေ့ပါ။")
            return
        elif ai_reply == "ERROR_GEMINI_FAIL":
            send_fb_message(sender_id, "မင်္ဂလာပါရှင်။ စနစ်ခေတ္တအလုပ်များနေသဖြင့် ခေတ္တစောင့်ဆိုင်းပေးပါရှင်။")
            return

        app.chat_memory[sender_id].append({"role": "user", "text": customer_msg})
        app.chat_memory[sender_id].append({"role": "model", "text": ai_reply})
        send_fb_message(sender_id, ai_reply)
    except Exception as e:
        print(f"❌ Fatal Error: {e}")

@app.route('/', methods=['GET'])
def home():
    return "🚀 Engine v410.0 - Webhook Active!"

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        challenge = request.args.get('hub.challenge')
        if challenge: return challenge, 200
        return "Active", 200
    elif request.method == 'POST':
        try:
            data = request.get_json() or {}
            print(f"📩 RECEIVED WEBHOOK EVENT: {json.dumps(data)}") # Logs ထဲမှာ စာဝင်မဝင် စစ်ရန်
            if data.get("object") == "page":
                for entry in data.get("entry", []):
                    for messaging_event in entry.get("messaging", []):
                        if messaging_event.get("message"):
                            message_data = messaging_event["message"]
                            mid = message_data.get("mid")
                            if mid in app.processed_mid: continue
                            if mid: app.processed_mid.add(mid)
                            sender_id = str(messaging_event["sender"]["id"])
                            customer_msg = message_data.get("text", "").strip()
                            if not customer_msg: continue
                            t = threading.Thread(target=process_async_message, args=(sender_id, customer_msg))
                            t.start()
            return "EVENT_RECEIVED", 200
        except Exception as e:
            print(f"❌ Webhook Post Error: {e}")
            return "EVENT_RECEIVED", 200
    return "Not Found", 404

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
