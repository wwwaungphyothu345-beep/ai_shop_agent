import os
from flask import Flask, request, jsonify
import requests
import json
import threading

app = Flask(__name__)

# --- CONFIGURATION SETUP ---
PAGE_ACCESS_TOKEN = "EAAWTc0UsYPgBR45NIFxOFGnOPn8ji8WlcseZAF483nv1I8VoRXa3ryPUyBLsclEgEGf3hZBlZASNZAnssvA7PnIBg0paS4zBVu7CmdTrqOS21zTpUSgIXDAVxT8UoF6seZAZB6mtkUeEkAdoSWhfPfJLUdzYnmxBZAynxW1OJvvk78FySknSOZA33MIGRzMLPh45OBH1WKwvIwZDZD"

if not hasattr(app, 'processed_mid'): app.processed_mid = set()

def get_gemini_url():
    current_key = os.environ.get("GEMINI_API_KEY", "").strip() or os.environ.get("gemini_api_key", "").strip()
    return f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={current_key}"

def send_fb_message(recipient_id, text_reply):
    try:
        url = f"https://graph.facebook.com/v21.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
        payload = {"recipient": {"id": str(recipient_id)}, "message": {"text": text_reply}}
        res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=8)
        print(f"📡 FB SEND STATUS: {res.status_code}")
    except Exception as e:
        print(f"❌ FB SEND EXCEPTION: {e}")

# --- PURE SMART CHAT LOGIC (ဘာမေးမေး အလိုက်သင့် စမတ်ကျကျ ပြန်ဖြေပေးမည့်အပိုင်း) ---
def process_async_message(sender_id, customer_msg):
    try:
        # AI ကို ဘာမေးမေး အလိုက်သင့် ပျူငှာစွာ လိုရင်းတိုရှင်း စာပြန်တတ်စေရန် ညွှန်ကြားခြင်း
        system_instruction = (
            "မင်းက မြန်မာနိုင်ငံက Online Shop အရောင်းဝန်ထမ်း AI ဖြစ်တယ်။ "
            "ကာစတန်မာက ဘာပဲလာမေးမေး (နှုတ်ဆက်တာ၊ ပစ္စည်းအကြောင်း၊ စျေးမေးတာ၊ Complain တက်တာ သို့မဟုတ် တခြားအထွေထွေ စကားပြောတာ) "
            "အားလုံးကို အလိုက်သင့် ယဉ်ကျေးပျူငှာစွာနှင့် လိုရင်းတိုရှင်း မြန်မာလို အကောင်းဆုံး ပြန်လည်ဖြေကြားပေးရမယ်။ "
            "မင်းမသိတဲ့ သီးသန့်ကိစ္စတွေ လာမေးရင်လည်း စိတ်မဆိုးပါနဲ့ ဝန်ထမ်းတွေနဲ့ အမြန်ဆုံး ချိတ်ဆက်ပေးမယ်လို့ အလိုက်သင့် ချော့မော့ဖြေပေးပါ။"
        )

        gemini_payload = {
            "contents": [{"parts": [{"text": f"Customer: {customer_msg}"}]}],
            "systemInstruction": {"parts": [{"text": system_instruction}]}
        }
        
        gemini_res = requests.post(get_gemini_url(), headers={'Content-Type': 'application/json'}, data=json.dumps(gemini_payload), timeout=12)
        res_json = gemini_res.json()
        
        ai_reply = ""
        if "candidates" in res_json and len(res_json["candidates"]) > 0:
            ai_reply = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
        
        if not ai_reply:
            ai_reply = "မင်္ဂလာပါရှင်၊ လူကြီးမင်းမေးမြန်းမှုကို ဝန်ထမ်းများမှ မကြာမီ စစ်ဆေးဖြေကြားပေးပါမည်ရှင်။"

        send_fb_message(sender_id, ai_reply)

    except Exception as e:
        print(f"❌ Core Process Error: {e}")
        send_fb_message(sender_id, "မင်္ဂလာပါရှင်၊ လူကြီးမင်းမေးမြန်းထားသော အကြောင်းအရာကို ဝန်ထမ်းများမှ ချက်ချင်း ပြန်လည်ဖြေကြားပေးပါမည်ရှင်။")

@app.route('/', methods=['GET'])
def home():
    return "🚀 Live Dedicated Engine v150.0 [Pure AI Response Mode] - Online!"

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        challenge = request.args.get('hub.challenge')
        if challenge: return challenge, 200
        return "Active", 200
    elif request.method == 'POST':
        try:
            data = request.get_json() or {}
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
        except:
            return "EVENT_RECEIVED", 200
    return "Not Found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
