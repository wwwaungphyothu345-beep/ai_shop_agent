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

# Render Env ထဲရှိ GEMINI_API_KEY ကို ဆွဲဖတ်ခြင်း
def get_gemini_url():
    current_key = os.environ.get("GEMINI_API_KEY", "").strip() or os.environ.get("gemini_api_key", "").strip()
    return f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={current_key}"

def send_fb_message(recipient_id, text_reply):
    try:
        url = f"https://graph.facebook.com/v21.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
        payload = {"recipient": {"id": str(recipient_id)}, "message": {"text": text_reply}}
        requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
    except: pass

# Telegram Group ထံသို့ စာလှမ်းပို့သည့် စနစ်
def send_telegram_message(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=10)
    except: pass

def call_google_script(payload):
    try:
        res = requests.post(SCRIPT_URL, headers={"Content-Type": "application/json"}, data=json.dumps(payload), timeout=20, allow_redirects=True)
        if res.status_code == 200: return res.json()
    except: pass
    return None

@app.route('/', methods=['GET'])
def home():
    return "🚀 Live Dedicated Engine v40.0 [FB + Telegram Omnichannel] - Online!"

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        challenge = request.args.get('hub.challenge')
        if challenge: return challenge, 200
        return "Facebook Endpoint Active", 200
        
    elif request.method == 'POST':
        try:
            data = request.get_json() or {}
            if data.get("object") == "page":
                for entry in data.get("entry", []):
                    for messaging_event in entry.get("messaging", []):
                        if messaging_event.get("message"):
                            sender_id = str(messaging_event["sender"]["id"])
                            message_data = messaging_event["message"]
                            customer_msg = message_data.get("text", "").strip()
                            if not customer_msg: continue

                            ai_reply = ""
                            try:
                                check_key = os.environ.get("GEMINI_API_KEY", "").strip() or os.environ.get("gemini_api_key", "").strip()
                                if not check_key:
                                    send_fb_message(sender_id, "⚠️ GEMINI_API_KEY လိုအပ်နေပါသည်။")
                                    continue

                                sheet_data = call_google_script({"action": "read"})
                                inventory_context = ""
                                if sheet_data and sheet_data.get("status") == "success" and "data" in sheet_data:
                                    inventory_context = "\n📦 ပစ္စည်းစာရင်းစာအုပ် -\n"
                                    for item in sheet_data["data"]:
                                        p_name = item.get("product_name") or item.get("productname") or "မသိပါ"
                                        p_price = item.get("price") or "ညှိနှိုင်း"
                                        p_stock = item.get("stock") or "0"
                                        inventory_context += f"🔹 {p_name} | စျေး: {p_price} ကျပ် | လက်ကျန်: {p_stock} ခု\n"
                                
                                system_instruction = "မင်းက Online Shop အရောင်း AI ဖြစ်တယ်။ မြန်မာလို ယဉ်ကျေးစွာ ကွက်တိပြန်ဖြေပါ။ ကာစတန်မာက ဝယ်ယူမည် သို့မဟုတ် ငွေလွှဲမည်ဟု ဆိုပါက စနစ်တကျ မှတ်တမ်းတင်ပေးမည်ဟု ပြောပါ။"
                                full_prompt = f"{system_instruction}\n{inventory_context}\n\nCustomer: {customer_msg}"
                                
                                gemini_payload = {"contents": [{"parts": [{"text": full_prompt}]}]}
                                gemini_res = requests.post(get_gemini_url(), headers={'Content-Type': 'application/json'}, data=json.dumps(gemini_payload), timeout=15)
                                res_json = gemini_res.json()
                                
                                if "candidates" in res_json and len(res_json["candidates"]) > 0:
                                    candidate = res_json["candidates"][0]
                                    if "content" in candidate and "parts" in candidate["content"] and len(candidate["content"]["parts"]) > 0:
                                        ai_reply = candidate["content"]["parts"][0].get("text", "").strip()
                                
                                # --- AUTOMATIC TELEGRAM NOTIFICATION ---
                                # စာသားထဲတွင် ဝယ်ယူခြင်း သို့မဟုတ် ငွေလွှဲခြင်းဆိုင်ရာ စကားလုံးများပါက Telegram သို့ ချက်ချင်းအကြောင်းကြားမည်
                                trigger_keywords = ["ဝယ်", "ယူမယ်", "ငွေလွှဲ", "kpay", "wave", "ဘဏ်", "ယူမည်", "ဝယ်မယ်"]
                                if any(keyword in customer_msg.lower() for keyword in trigger_keywords):
                                    notification_text = f"📢 *အမှာစာ သတိပေးချက်*\n\n👤 Customer ID: `{sender_id}`\n💬 မက်ဆေ့ခ်ျ: {customer_msg}\n🤖 AI တုံ့ပြန်မှု: {ai_reply}"
                                    send_telegram_message(FINANCE_GROUP, notification_text)
                                    send_telegram_message(PACKING_GROUP, notification_text)

                                if not ai_reply:
                                    ai_reply = f"မင်္ဂလာပါ၊ ဝန်ထမ်းများမှ စစ်ဆေးဖြေကြားပေးပါမည်။"
                                        
                            except Exception as e:
                                ai_reply = f"မင်္ဂလာပါ၊ ခေတ္တစောင့်ဆိုင်းပေးပါဦးဗျာ။"
                                
                            send_fb_message(sender_id, ai_reply)
                return "EVENT_RECEIVED", 200
        except:
            return jsonify({"status": "error"}), 500
    return "Not Found", 404

# Telegram Webhook လက်ခံမည့် နေရာအပြည့်အစုံ
@app.route('/telegram', methods=['POST'])
def telegram_webhook():
    try:
        data = request.get_json() or {}
        if "message" in data:
            chat_id = str(data["message"]["chat"]["id"])
            text = data["message"].get("text", "")
            # Telegram ဘက်မှ လာသော စာများကို ဤနေရာတွင် စီမံနိုင်သည်
        return jsonify({"status": "ok"}), 200
    except:
        return jsonify({"status": "error"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
