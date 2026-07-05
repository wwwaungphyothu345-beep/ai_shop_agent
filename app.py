import os
from flask import Flask, request, jsonify
import requests
import json

app = Flask(__name__)

# --- CONFIGURATION SETUP ---
BOT_TOKEN = "8996226211:AAH6G64un9oNG2qFRG0RRcCadoHdTDUpeJY"
PAGE_ACCESS_TOKEN = "EAAWTc0UsYPgBR3qeVX7zGhDeFwG69yZBBVy3ZCurzHjhK95nNdvhy9r0ZBQVMGgFZAVO6YxuM52tionH75HzqATyjkXRAYLUEi4WSEZATkHGl4GMT85lesZAgZAMTVokh5BqMSo2UK2EUQFvJifZCuPW53KgBaSMcRArbgWIAAHhbxImacX2eYlWIhHVi6HGg0CNS0uX2huslAZDZD"
FB_VERIFY_TOKEN = "ai_shop_agent_token_2026"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbx59Jc9RzVTD_3x2oC9RSAxVE-mLkjCwjMvld1N5yk8-ej4UFvPyQhqO9W01sfBjcYS/exec"

FINANCE_GROUP = "-1004461406737" 
PACKING_GROUP = "-1004376924884" 

# Event ID များကို မှတ်ထားပြီး စာထပ်မံမပို့အောင် တားဆီးရန် Database ယာယီဆောက်ခြင်း
if not hasattr(app, 'processed_mid'):
    app.processed_mid = set()

def get_gemini_url():
    current_key = os.environ.get("GEMINI_API_KEY", "").strip() or os.environ.get("gemini_api_key", "").strip()
    return f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={current_key}"

def send_fb_message(recipient_id, text_reply):
    try:
        url = f"https://graph.facebook.com/v21.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
        payload = {"recipient": {"id": str(recipient_id)}, "message": {"text": text_reply}}
        requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=5)
    except: pass

def send_telegram_message(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=5)
    except: pass

def call_google_script(payload):
    try:
        res = requests.post(SCRIPT_URL, headers={"Content-Type": "application/json"}, data=json.dumps(payload), timeout=10)
        if res.status_code == 200: return res.json()
    except: pass
    return None

@app.route('/', methods=['GET'])
def home():
    return "🚀 Live Dedicated Engine v45.0 [Fix Duplicate & Prompt Engine] - Online!"

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        challenge = request.args.get('hub.challenge')
        if challenge: return challenge, 200
        return "Facebook Endpoint Active", 200
        
    elif request.method == 'POST':
        # စာထပ်မံမလာစေရန် Facebook အား ချက်ချင်း တုံ့ပြန်မှုပေးခြင်း (200 OK Fast Response)
        try:
            data = request.get_json() or {}
            if data.get("object") == "page":
                for entry in data.get("entry", []):
                    for messaging_event in entry.get("messaging", []):
                        if messaging_event.get("message"):
                            message_data = messaging_event["message"]
                            mid = message_data.get("mid")
                            
                            # စာသားထပ်နေပါက လုံးဝကျော်သွားရန်
                            if mid in app.processed_mid:
                                return "EVENT_RECEIVED", 200
                            if mid:
                                app.processed_mid.add(mid)
                                # Cache မကြီးထွားစေရန် ၅၀ ကျော်ပါက အဟောင်းဖြတ်ခြင်း
                                if len(app.processed_mid) > 50:
                                    app.processed_mid.pop()

                            sender_id = str(messaging_event["sender"]["id"])
                            customer_msg = message_data.get("text", "").strip()
                            if not customer_msg: continue

                            # Gemini Content Process
                            try:
                                sheet_data = call_google_script({"action": "read"})
                                inventory_context = ""
                                if sheet_data and sheet_data.get("status") == "success" and "data" in sheet_data:
                                    inventory_context = "📦 လက်ရှိဆိုင်ရှိ ပစ္စည်းစာရင်းစာအုပ်နှင့် လက်ကျန်များ -\n"
                                    for item in sheet_data["data"]:
                                        p_name = item.get("product_name") or item.get("productname") or "မသိပါ"
                                        p_price = item.get("price") or "ညှိနှိုင်း"
                                        p_stock = item.get("stock") or "0"
                                        inventory_context += f"🔹 {p_name} | စျေး: {p_price} ကျပ် | လက်ကျန်: {p_stock} ခု\n"

                                # [🎯 CRITICAL FIX] Gemini 2.5 စနစ်အမှန်အတွက် System Instruction အား Parameter သီးသန့်ခွဲထုတ်ခြင်း
                                system_instruction = (
                                    "မင်းက မြန်မာနိုင်ငံက နာမည်ကြီး Online Shop အရောင်းစာရေးမလေး ဖြစ်တယ်။ "
                                    "ယဉ်ကျေးပျူငှာစွာနှင့် လိုရင်းတိုရှင်း ကွက်တိသာ ပြန်ဖြေပါ။ စကားလုံးများ ထပ်ခါတလဲလဲ မပြောပါနှင့်။ "
                                    "ကာစတန်မာက ဝယ်ယူလိုသည်ဟု ဆိုပါက သို့မဟုတ် အမည်၊ ဖုန်း၊ လိပ်စာ ပေးလာပါက "
                                    "ပစ္စည်းစာရင်းထဲတွင် လက်ကျန်ရှိမရှိ အရင်စစ်ဆေးပြီး 'အမှာစာကို စနစ်တကျ မှတ်တမ်းတင်ပေးပြီးပါပြီရှင်' ဟုသာ ယဉ်ကျေးစွာ ပြောပါ။"
                                )

                                gemini_payload = {
                                    "contents": [{"parts": [{"text": f"{inventory_context}\n\nCustomer: {customer_msg}"}]}],
                                    "systemInstruction": {"parts": [{"text": system_instruction}]}
                                }
                                
                                gemini_res = requests.post(get_gemini_url(), headers={'Content-Type': 'application/json'}, data=json.dumps(gemini_payload), timeout=10)
                                res_json = gemini_res.json()
                                
                                ai_reply = ""
                                if "candidates" in res_json and len(res_json["candidates"]) > 0:
                                    candidate = res_json["candidates"][0]
                                    if "content" in candidate and "parts" in candidate["content"] and len(candidate["content"]["parts"]) > 0:
                                        ai_reply = candidate["content"]["parts"][0].get("text", "").strip()
                                
                                if not ai_reply:
                                    ai_reply = "မင်္ဂလာပါရှင်၊ လူကြီးမင်းမေးမြန်းမှုကို ဝန်ထမ်းများမှ မကြာမီ စစ်ဆေးဖြေကြားပေးပါမည်ရှင်။"

                                # --- TELEGRAM SMART NOTIFICATION ENGINE ---
                                # အမှန်တကယ် ဝယ်ယူသည့် အချက်အလက် (ဥပမာ ဖုန်းနံပါတ် သို့မဟုတ် ဝယ်မည်) ပါမှသာ Telegram သို့ ပို့မည်
                                trigger_keywords = ["ဝယ်", "ယူမယ်", "ငွေလွှဲ", "kpay", "wave", "ဘဏ်", "099", "092", "094", "097", "098", "မန္တလေး", "ရန်ကုန်"]
                                if any(keyword in customer_msg.lower() for keyword in trigger_keywords):
                                    notification_text = f"📢 *အမှာစာအသစ် ရရှိပါသည်*\n\n👤 *Customer ID:* `{sender_id}`\n💬 *ဝယ်ယူသူ မက်ဆေ့ခ်ျ:* {customer_msg}\n🤖 *AI တုံ့ပြန်မှု:* {ai_reply}"
                                    send_telegram_message(FINANCE_GROUP, notification_text)
                                    send_telegram_message(PACKING_GROUP, notification_text)

                                send_fb_message(sender_id, ai_reply)

                            except Exception as e:
                                send_fb_message(sender_id, "မင်္ဂလာပါရှင်၊ ခေတ္တစောင့်ဆိုင်းပေးပါဦးရှင်။")
                                
                return "EVENT_RECEIVED", 200
        except:
            return jsonify({"status": "error"}), 500
    return "Not Found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
