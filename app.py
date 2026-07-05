import os
from flask import Flask, request, jsonify
import requests
import json
import threading

app = Flask(__name__)

# --- CONFIGURATION SETUP ---
BOT_TOKEN = "8996226211:AAH6G64un9oNG2qFRG0RRcCadoHdTDUpeJY"
PAGE_ACCESS_TOKEN = "EAAWTc0UsYPgBR45NIFxOFGnOPn8ji8WlcseZAF483nv1I8VoRXa3ryPUyBLsclEgEGf3hZBlZASNZAnssvA7PnIBg0paS4zBVu7CmdTrqOS21zTpUSgIXDAVxT8UoF6seZAZB6mtkUeEkAdoSWhfPfJLUdzYnmxBZAynxW1OJvvk78FySknSOZA33MIGRzMLPh45OBH1WKwvIwZDZD"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbx59Jc9RzVTD_3x2oC9RSAxVE-mLkjCwjMvld1N5yk8-ej4UFvPyQhqO9W01sfBjcYS/exec"

FINANCE_GROUP = "-1004461406737" 
PACKING_GROUP = "-1004376924884" 

if not hasattr(app, 'processed_mid'): app.processed_mid = set()
if not hasattr(app, 'user_states'): app.user_states = {}

def get_gemini_url():
    current_key = os.environ.get("GEMINI_API_KEY", "").strip() or os.environ.get("gemini_api_key", "").strip()
    return f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={current_key}"

def send_fb_message(recipient_id, text_reply):
    try:
        url = f"https://graph.facebook.com/v21.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
        payload = {"recipient": {"id": str(recipient_id)}, "message": {"text": text_reply}}
        res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=8)
        print(f"📡 Render Log -> FB Reply Status: {res.status_code} | Body: {res.text}")
    except Exception as e:
        print(f"❌ FB Reply Error: {e}")

def process_async_message(sender_id, customer_msg, message_data):
    try:
        if "attachments" in message_data:
            for att in message_data["attachments"]:
                if att["type"] == "image":
                    img_url = att["payload"]["url"]
                    fn_alert = f"💰 *ငွေလွှဲပြေစာ ရရှိပါသည်*\n\n👤 *Customer ID:* `{sender_id}`\n🖼️ *ငွေလွှဲပြေစာ:* [ကြည့်ရှုရန်]({img_url})"
                    
                    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                    payload = {
                        "chat_id": FINANCE_GROUP, "text": fn_alert, "parse_mode": "Markdown",
                        "reply_markup": {"inline_keyboard": [[{"text": "Confirm 🟢", "callback_data": f"conf_{sender_id}"},{"text": "Reject 🔴", "callback_data": f"rej_{sender_id}"}]]}
                    }
                    requests.post(url, json=payload, timeout=8)
                    send_fb_message(sender_id, "ငွေလွှဲပြေစာ ရရှိပါပြီရှင်။ ငွေစာရင်းဌာနမှ စစ်ဆေးအတည်ပြုပေးနေပါသဖြင့် ခေတ္တစောင့်ဆိုင်းပေးပါရှင်။")
            return

        send_fb_message(sender_id, "မင်္ဂလာပါရှင်၊ လူကြီးမင်းမေးမြန်းမှုကို စနစ်မှ စစ်ဆေးနေပါပြီရှင်။")
    except Exception as e:
        print(f"❌ Thread Error: {e}")

@app.route('/', methods=['GET'])
def home():
    return "🚀 Live Dedicated Engine v85.0 [Token Diagnostic Active] - Online!"

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        challenge = request.args.get('hub.challenge')
        if challenge: return challenge, 200
        return "Active", 200
    elif request.method == 'POST':
        try:
            data = request.get_json() or {}
            print(f"📩 Render Received Webhook Event: {json.dumps(data)}")
            if data.get("object") == "page":
                for entry in data.get("entry", []):
                    for messaging_event in entry.get("messaging", []):
                        if messaging_event.get("message"):
                            message_data = messaging_event["message"]
                            mid = message_data.get("mid")
                            if mid in app.processed_mid: continue
                            app.processed_mid.add(mid)
                            
                            sender_id = str(messaging_event["sender"]["id"])
                            customer_msg = message_data.get("text", "").strip()
                            
                            t = threading.Thread(target=process_async_message, args=(sender_id, customer_msg, message_data))
                            t.start()
            return "EVENT_RECEIVED", 200
        except Exception as e:
            print(f"❌ Webhook Error: {e}")
            return "EVENT_RECEIVED", 200
    return "Not Found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
