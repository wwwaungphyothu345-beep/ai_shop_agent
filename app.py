import os
from flask import Flask, request, jsonify
import requests
import json
import threading

app = Flask(__name__)

# --- CONFIGURATION SETUP ---
PAGE_ACCESS_TOKEN = "EAAWTc0UsYPgBR45NIFxOFGnOPn8ji8WlcseZAF483nv1I8VoRXa3ryPUyBLsclEgEGf3hZBlZASNZAnssvA7PnIBg0paS4zBVu7CmdTrqOS21zTpUSgIXDAVxT8UoF6seZAZB6mtkUeEkAdoSWhfPfJLUdzYnmxBZAynxW1OJvvk78FySknSOZA33MIGRzMLPh45OBH1WKwvIwZDZD"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbw_22BeUhWNShR1K_oGoIRJZ3_uhyLZmlenbghGsSMn1ar3pLtBoHjHvdoV74T5TbJtmQ/exec"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

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
        if not GEMINI_API_KEY:
            print("⚠️ GEMINI_API_KEY IS LITERALLY MISSING IN ENVIRONMENT")
            return "ERROR_API_KEY_MISSING"
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        
        formatted_contents = []
        for chat in chat_history[-6:]:
            formatted_contents.append({
                "role": "user" if chat["role"] == "user" else "model",
                "parts": [{"text": chat["text"]}]
            })
            
        formatted_contents.append({
            "role": "user",
            "parts": [{"text": user_msg}]
        })
        
        payload = {
            "contents": formatted_contents,
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "generationConfig": {
                "temperature": 0.3
            }
        }
        
        res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=15)
        print(f"🤖 Gemini API Status Response Code: {res.status_code}")
        
        if res.status_code == 200:
            res_data = res.json()
            return res_data['candidates'][0]['message']['parts'][0]['text']
        else:
            print(f"❌ Gemini API Error Message: {res.text}")
    except Exception as e:
        print(f"❌ Gemini Exception Occurred: {e}")
    return "ERROR_GEMINI_FAIL"

def process_async_message(sender_id, customer_msg):
    try:
        prod_res = call_google_script("read_products")
        cod_res = call_google_script("read_cod")
        setting_res = call_google_script("read_setting")
        
        # 🛡️ Safe check format (အကယ်၍ Sheet ထဲက none ပြန်လာရင် မပျက်ကျအောင်ကာကွယ်ခြင်း)
        products = (prod_res.get("data", []) if prod_res else []) or []
        cod_cities = (cod_res.get("data", []) if cod_res else []) or []
        settings = (setting_res.get("data", {}) if setting_res else {}) or {}

        shop_context = f"""
        သင်သည် ယဉ်ကျေးပျူငှာသော မြန်မာ AI Shop Assistant တစ်ဦးဖြစ်သည်။
        ကာစတန်မာများကို မြန်မာလို လေသံချိုချိုဖြင့် ဝန်ဆောင်မှုပေးပါ။
        
        [ရရှိနိုင်သော ကုန်ပစ္စည်းစာရင်း]
        {json.dumps(products, ensure_ascii=False)}
        
        [COD (ပစ္စည်းရောက်မှငွေချေ) ရသော မြို့များစာရင်း]
        {', '.join(cod_cities)}
        
        [COD မရပါက ငွေကြိုလွှဲရမည့် အချက်အလက် (Settings)]
        {json.dumps(settings, ensure_ascii=False)}

        [စည်းကမ်းချက်များ]
        ၁။ ပစ္စည်းဈေးနှုန်းနှင့် စတော့ခ်များကို ရရှိနိုင်သောကုန်ပစ္စည်းစာရင်းအတိုင်း တိကျစွာဖြေပါ။
        ၂။ ကာစတန်မာက ၎င်းတို့နေထိုင်သည့် မြို့ကို ပြောလာပါက 'COD ရသော မြို့များစာရင်း' ထဲတွင် ပါဝင်မှု ရှိမရှိ စစ်ဆေးပါ။
           - ပါဝင်ပါက: COD ရကြောင်းပြောပါ။
           - မပါဝင်ပါက: COD မရသဖြင့် Settings ထဲရှိ အကောင့်သို့ ငွေကြိုလွှဲပေးရမည်ဖြစ်ကြောင်း ရှင်းပြပါ။
        ၃။ ကာစတန်မာက မှာယူရန် အချက်အလက် (အမည်၊ ဖုန်း၊ လိပ်စာ၊ ပစ္စည်း) ပေးလာပါက အော်ဒါစာရင်းကို အတည်ပြုပြီး "အော်ဒါစာရင်း မှတ်သားလိုက်ပါပြီရှင်" ဟု သေချာပေါက် ထည့်ပြောပါ။
        """

        if sender_id not in app.chat_memory:
            app.chat_memory[sender_id] = []
            
        ai_reply = ask_gemini_agent(shop_context, customer_msg, app.chat_memory[sender_id])
        
        if ai_reply == "ERROR_API_KEY_MISSING":
            send_fb_message(sender_id, "⚠️ System Config Error: GEMINI_API_KEY is missing in Render Env Variables.")
            return
        elif ai_reply == "ERROR_GEMINI_FAIL":
            send_fb_message(sender_id, "⚠️ AI Engine ချိတ်ဆက်မှု အဆင်မပြေပါ။ သင်၏ Gemini API Key သက်တမ်း သို့မဟုတ် စည်းကမ်းချက်များကို စစ်ဆေးပေးပါရန်။")
            return

        app.chat_memory[sender_id].append({"role": "user", "text": customer_msg})
        app.chat_memory[sender_id].append({"role": "model", "text": ai_reply})

        if "အော်ဒါစာရင်း မှတ်သား" in ai_reply or "အော်ဒါတင်ပေး" in ai_reply:
            order_payload = {
                "order_data": {
                    "customer_name": "Facebook Customer",
                    "phone": "စာထဲတွင်ကြည့်ရန်",
                    "address": "လိပ်စာစစ်ဆေးဆဲ",
                    "order_details": f"Msg: {customer_msg}"
                }
            }
            call_google_script("write_order", order_payload)

        send_fb_message(sender_id, ai_reply)
    except Exception as e:
        print(f"❌ Core Process Error: {e}")

@app.route('/', methods=['GET'])
def home():
    key_status = "Detected ✅" if GEMINI_API_KEY else "Missing ❌"
    return f"🚀 Engine v380.0 - Robust Sheet Parsing - API Key Status: {key_status}"

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
