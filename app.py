import os
from flask import Flask, request, jsonify
import requests
import json
import threading

app = Flask(__name__)

# --- CONFIGURATION SETUP ---
PAGE_ACCESS_TOKEN = "EAAWTc0UsYPgBR45NIFxOFGnOPn8ji8WlcseZAF483nv1I8VoRXa3ryPUyBLsclEgEGf3hZBlZASNZAnssvA7PnIBg0paS4zBVu7CmdTrqOS21zTpUSgIXDAVxT8UoF6seZAZB6mtkUeEkAdoSWhfPfJLUdzYnmxBZAynxW1OJvvk78FySknSOZA33MIGRzMLPh45OBH1WKwvIwZDZD"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxQ7-2n6atk5XKv5wV0Kfhb5x1CcIu9qNPkSKUO8ElEI9iwdW1qyQCSZtMNsHIhdZh3Pg/exec"
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE" # <- သင့် Gemini API Key ကို ဤနေရာတွင် ထည့်ပါ

if not hasattr(app, 'processed_mid'): app.processed_mid = set()
if not hasattr(app, 'chat_memory'): app.chat_memory = {}

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
        res = requests.post(SCRIPT_URL, headers={"Content-Type": "application/json"}, data=json.dumps(payload), timeout=15)
        if res.status_code == 200: return res.json()
    except Exception as e:
        print(f"❌ Sheet Sync Error ({action}): {e}")
    return None

def ask_gemini_agent(system_prompt, user_msg, chat_history):
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        
        contents = []
        for chat in chat_history[-6:]:
            contents.append({"role": chat["role"], "parts": [{"text": chat["text"]}]})
        contents.append({"role": "user", "parts": [{"text": user_msg}]})
        
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": contents,
            "generationConfig": {"temperature": 0.3}
        }
        
        res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=15)
        if res.status_code == 200:
            res_data = res.json()
            return res_data['candidates'][0]['message']['parts'][0]['text']
    except Exception as e:
        print(f"❌ Gemini Error: {e}")
    return "မင်္ဂလာပါရှင်၊ စနစ်အနည်းငယ် အလုပ်ရှုပ်နေပါသဖြင့် ခေတ္တစောင့်ဆိုင်းပေးပါရှင်။"

# --- CORE INTELLIGENT ROUTING ENGINE ---
def process_async_message(sender_id, customer_msg):
    try:
        prod_res = call_google_script("read_products")
        cod_res = call_google_script("read_cod")
        setting_res = call_google_script("read_setting")
        
        products = prod_res.get("data", []) if prod_res else []
        cod_cities = cod_res.get("data", []) if cod_res else []
        settings = setting_res.get("data", {}) if setting_res else {}

        shop_context = f"""
        သင်သည် လူမှုကောင်းမွန်ပြူငှာသော AI Shop Assistant တစ်ဦးဖြစ်သည်။ မြန်မာဘာသာဖြင့် သာယာချိုသာစွာ ဖြေကြားပေးပါ။
        
        [လက်ရှိရရှိနိုင်သော ပစ္စည်းစာရင်း (Products)]
        {json.dumps(products, ensure_ascii=False)}
        
        [COD (ပစ္စည်းရောက်မှငွေချေ) ရရှိနိုင်သောမြို့များ (COD Cities)]
        {', '.join(cod_cities)}
        
        [ငွေလွှဲရမည့် အချက်အလက် (Settings - COD မရသောမြို့များအတွက်)]
        {json.dumps(settings, ensure_ascii=False)}

        [စည်းမျဉ်းများနှင့် လမ်းညွှန်ချက်များ]
        - ကာစတန်မာ မေးမြန်းသော ပစ္စည်းစာရင်း၊ ဈေးနှုန်း၊ စတော့ခ်များကို Products စာရင်းအတိုင်း တိကျစွာပြောပါ။
        - ကာစတန်မာက ၎င်းတို့၏ 'မြို့နယ်/မြို့' ကို ပြောလာလျှင် COD ရရှိနိုင်သော မြို့များထဲတွင် ပါဝင်ခြင်း ရှိမရှိ စစ်ဆေးပါ။
        - ကာစတန်မာ၏ မြို့သည် COD ရလျှင် "COD ရပါတယ်ရှင်" ဟု ပြောပါ။ COD မရပါက Setting ထဲရှိ ငွေလွှဲရမည့်အကောင့်များကို ပြသပြီး "ငွေကြိုလွှဲပေးရပါမယ်ရှင်" ဟု လေသံချိုချိုဖြင့် အသိပေးပါ။
        - ကာစတန်မာက ဝယ်ယူရန် (အမည်၊ ဖုန်း၊ လိပ်စာ၊ မှာမည့်ပစ္စည်း) တို့ကို ပြည့်စုံစွာ ပေးလာပါက၊ အော်ဒါအချက်အလက်များကို အတည်ပြုပြီး "အော်ဒါစာရင်း မှတ်သားလိုက်ပါပြီရှင်" ဟု ပြောကြားပေးပါ။
        """

        if sender_id not in app.chat_memory:
            app.chat_memory[sender_id] = []
            
        ai_reply = ask_gemini_agent(shop_context, customer_msg, app.chat_memory[sender_id])
        
        app.chat_memory[sender_id].append({"role": "user", "text": customer_msg})
        app.chat_memory[sender_id].append({"role": "model", "text": ai_reply})

        if "အော်ဒါစာရင်း မှတ်သား" in ai_reply or "အော်ဒါ တင်ပေး" in ai_reply:
            order_payload = {
                "order_data": {
                    "sender_id": sender_id,
                    "name": "Customer",
                    "phone": "Customer Phone",
                    "address": customer_msg,
                    "township": "စစ်ဆေးဆဲ",
                    "product": "စစ်ဆေးဆဲ",
                    "payment_method": "COD သို့မဟုတ် Transfer"
                }
            }
            call_google_script("write_order", order_payload)

        send_fb_message(sender_id, ai_reply)

    except Exception as e:
        print(f"❌ Core Process Error: {e}")
        send_fb_message(sender_id, "မင်္ဂလာပါရှင်၊ စနစ်အနည်းငယ် အလုပ်ရှုပ်နေပါသဖြင့် ခေတ္တစောင့်ဆိုင်းပေးပါရှင်။")

@app.route('/', methods=['GET'])
def home():
    return "🚀 Live AI-Agent Multi-Sheet Sync Engine v310.0 https://dictionary.cambridge.org/dictionary/english/updated - Online!"

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
