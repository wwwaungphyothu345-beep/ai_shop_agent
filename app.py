import os
from flask import Flask, request, jsonify
import requests
import json
import threading

app = Flask(__name__)

# --- CONFIGURATION SETUP ---
PAGE_ACCESS_TOKEN = "EAAWTc0UsYPgBR45NIFxOFGnOPn8ji8WlcseZAF483nv1I8VoRXa3ryPUyBLsclEgEGf3hZBlZASNZAnssvA7PnIBg0paS4zBVu7CmdTrqOS21zTpUSgIXDAVxT8UoF6seZAZB6mtkUeEkAdoSWhfPfJLUdzYnmxBZAynxW1OJvvk78FySknSOZA33MIGRzMLPh45OBH1WKwvIwZDZD"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbx59Jc9RzVTD_3x2oC9RSAxVE-mLkjCwjMvld1N5yk8-ej4UFvPyQhqO9W01sfBjcYS/exec"

if not hasattr(app, 'processed_mid'): app.processed_mid = set()

def send_fb_message(recipient_id, text_reply):
    try:
        url = f"https://graph.facebook.com/v21.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
        payload = {"recipient": {"id": str(recipient_id)}, "message": {"text": text_reply}}
        res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
        print(f"📡 FB SEND STATUS: {res.status_code}")
    except Exception as e:
        print(f"❌ FB SEND EXCEPTION: {e}")

def call_google_script(payload):
    try:
        res = requests.post(SCRIPT_URL, headers={"Content-Type": "application/json"}, data=json.dumps(payload), timeout=15)
        if res.status_code == 200: return res.json()
    except: pass
    return None

# --- PURE GOOGLE SHEET READ & REPLY ENGINE ---
def process_async_message(sender_id, customer_msg):
    try:
        # ၁။ Google Sheet ထဲက လက်ရှိ ပစ္စည်းစာရင်းနဲ့ စျေးနှုန်းများကို Real-time တိုက်ရိုက်ဆွဲဖတ်ခြင်း
        sheet_data = call_google_script({"action": "read"})
        
        # ၂။ စာရင်းဖတ်ရရှိပါက လူကြီးမင်း၏ Google Sheet ပါ data များကို တန်းစီပြီး စာသားထုတ်ပေးခြင်း
        if sheet_data and sheet_data.get("status") == "success" and "data" in sheet_data:
            reply_text = "🛍️ *မင်္ဂလာပါရှင်၊ လက်ရှိရရှိနိုင်သော ပစ္စည်းများနှင့် စျေးနှုန်းများဖြစ်ပါတယ်ရှင် -*\n\n"
            for item in sheet_data["data"]:
                p_name = item.get("product_name") or item.get("productname") or ""
                p_price = item.get("price") or "ညှိနှိုင်း"
                p_stock = item.get("stock") or "0"
                if p_name:
                    reply_text += f"▪️ {p_name} - စျေး: {p_price} ကျပ် (လက်ကျန်: {p_stock} ခု)\n"
            
            reply_text += "\nဝယ်ယူလိုပါက ပစ္စည်းအမည်ကို ပြောကြားပေးနိုင်ပါတယ်ရှင်။"
        else:
            # Google Script Web App Link သို့မဟုတ် Sheet Permissions မှားယွင်းနေပါက ပြသမည့်စာသား
            reply_text = "⚠️ [Google Sheet Error]: Google Sheet မှ Data ဖတ်ယူ၍ မရနိုင်သေးပါ။ Web App URL (SCRIPT_URL) သို့မဟုတ် Sheet ထဲတွင် ပစ္စည်းစာရင်း ရှိမရှိ ပြန်လည်စစ်ဆေးပေးပါရှင်။"

        # ၃။ ကာစတန်မာထံသို့ Google Sheet ထဲကစာရင်းကို တိုက်ရိုက် စာပြန်ပေးခြင်း
        send_fb_message(sender_id, reply_text)

    except Exception as e:
        print(f"❌ Core Process Error: {e}")
        send_fb_message(sender_id, "မင်္ဂလာပါရှင်၊ စနစ်အနည်းငယ် အလုပ်ရှုပ်နေပါသဖြင့် ခေတ္တစောင့်ဆိုင်းပေးပါရှင်။")

@app.route('/', methods=['GET'])
def home():
    return "🚀 Live Dedicated Engine v230.0 [Pure Google Sheet Sync Mode] - Online!"

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
