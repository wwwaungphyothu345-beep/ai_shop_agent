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

def get_gemini_url():
    current_key = (os.environ.get("GEMINI_API_KEY", "").strip() or 
                   os.environ.get("gemini_api_key", "").strip() or 
                   os.environ.get("Gemini_Api_Key", "").strip())
    return f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={current_key}"

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

# --- HUMAN-LIKE SALES BOT WITH GOOGLE SHEET SYNC ---
def process_async_message(sender_id, customer_msg):
    try:
        # ၁။ Google Sheet ထဲက လက်ရှိ ပစ္စည်းစာရင်းနဲ့ စျေးနှုန်းများကို ဆွဲဖတ်ခြင်း
        sheet_data = call_google_script({"action": "read"})
        inventory_context = ""
        if sheet_data and sheet_data.get("status") == "success" and "data" in sheet_data:
            inventory_context = "📦 ဆိုင်ရှိ လက်ရှိရရှိနိုင်သော ပစ္စည်းစာရင်းနှင့် စျေးနှုန်းများ -\n"
            for item in sheet_data["data"]:
                p_name = item.get("product_name") or item.get("productname") or ""
                p_price = item.get("price") or "ညှိနှိုင်း"
                p_stock = item.get("stock") or "0"
                if p_name:
                    inventory_context += f"- {p_name} | စျေး: {p_price} ကျပ် | လက်ကျန်: {p_stock} ခု\n"

        # ၂။ AI ကို စက်ရုပ်လိုမဟုတ်ဘဲ "တကယ့်လူအရောင်းဝန်ထမ်း" အတိုင်း အလိုက်သင့် စကားပြောရန် ညွှန်ကြားခြင်း
        system_instruction = (
            "မင်းက မြန်မာနိုင်ငံက Online Shop တစ်ခုရဲ့ သွက်လက်ချက်ချာပြီး သဘောကောင်းတဲ့ 'လူ' အရောင်းစာရေးမလေး ဖြစ်တယ်။ "
            "စက်ရုပ်လို အသေစာသားတွေ လုံးဝမသုံးပါနဲ့။ ကာစတန်မာက ဘာပဲလာမေးမေး (နှုတ်ဆက်တာ၊ စျေးမေးတာ၊ ပစ္စည်းအကြောင်း၊ Complain တက်တာ သို့မဟုတ် စနောက်တာ) "
            "အားလုံးကို တကယ့်လူတစ်ယောက်လိုပဲ အလိုက်သင့် ယဉ်ကျေးပျူငှာစွာနှင့် စမတ်ကျကျ မြန်မာလို ပြန်လည်ဖြေကြားပေးရမယ်။ "
            "ပစ္စည်းစျေးနှုန်း သို့မဟုတ် လက်ကျန်အခြေအနေကို မေးလာရင် ပေးထားတဲ့ ပစ္စည်းစာရင်း (Inventory Context) ကို လူလိုပဲ ဖတ်ပြီး တิတိကျကျ ဖြေပေးပါ။ "
            "အကယ်၍ ကာစတန်မာက ပစ္စည်းမှာယူလိုကြောင်း၊ ဝယ်ယူလိုကြောင်း ပြောလာပါက သို့မဟုတ် အချက်အလက်ပေးလာပါက "
            "အမှာစာကို စနစ်တကျ မှတ်တမ်းတင်ပေးပါမည်ဟု ယဉ်ကျေးစွာ ပြောကြားပေးပါ။"
        )

        gemini_payload = {
            "contents": [{"parts": [{"text": f"{inventory_context}\n\nCustomer: {customer_msg}"}]}],
            "systemInstruction": {"parts": [{"text": system_instruction}]}
        }
        
        # ၃။ Gemini AI API သို့ လှမ်းခေါ်ခြင်း
        gemini_res = requests.post(get_gemini_url(), headers={'Content-Type': 'application/json'}, data=json.dumps(gemini_payload), timeout=12)
        res_json = gemini_res.json()
        
        ai_reply = ""
        if "candidates" in res_json and len(res_json["candidates"]) > 0:
            ai_reply = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
        
        if not ai_reply:
            ai_reply = "မင်္ဂလာပါရှင်၊ လူကြီးမင်းမေးမြန်းမှုကို ဝန်ထမ်းများမှ မကြာမီ စစ်ဆေးဖြေကြားပေးပါမည်ရှင်။"

        # ၄။ Facebook Messenger သို့ စာပြန်ပို့ခြင်း
        send_fb_message(sender_id, ai_reply)

    except Exception as e:
        print(f"❌ Core Process Error: {e}")
        send_fb_message(sender_id, "မင်္ဂလာပါရှင်၊ လူကြီးမင်းမေးမြန်းထားသော အကြောင်းအရာကို ဝန်ထမ်းများမှ ချက်ချင်း ပြန်လည်ဖြေကြားပေးပါမည်ရှင်။")

@app.route('/', methods=['GET'])
def home():
    return "🚀 Live Dedicated Engine v210.0 [Pure Human Chat Mode + Sheet Sync] - Online!"

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
