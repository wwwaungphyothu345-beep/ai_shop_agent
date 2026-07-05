import os
from flask import Flask, request, jsonify
import requests
import json
import re

app = Flask(__name__)

# --- CONFIGURATION SETUP ---
BOT_TOKEN = "8996226211:AAH6G64un9oNG2qFRG0RRcCadoHdTDUpeJY"
PAGE_ACCESS_TOKEN = "EAAWTc0UsYPgBR3qeVX7zGhDeFwG69yZBBVy3ZCurzHjhK95nNdvhy9r0ZBQVMGgFZAVO6YxuM52tionH75HzqATyjkXRAYLUEi4WSEZATkHGl4GMT85lesZAgZAMTVokh5BqMSo2UK2EUQFvJifZCuPW53KgBaSMcRArbgWIAAHhbxImacX2eYlWIhHVi6HGg0CNS0uX2huslAZDZD"
FB_VERIFY_TOKEN = "ai_shop_agent_token_2026"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbx59Jc9RzVTD_3x2oC9RSAxVE-mLkjCwjMvld1N5yk8-ej4UFvPyQhqO9W01sfBjcYS/exec"

FINANCE_GROUP = "-1004461406737" 
PACKING_GROUP = "-1004376924884" 

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

# စာသားများထဲမှ ဖုန်းနံပါတ် သီးသန့်ဆွဲထုတ်ယူသည့် စနစ်
def extract_phone(text):
    match = re.search(r'(09\d{7,11})', text.replace(" ", "").replace("-", ""))
    return match.group(1) if match else "မသိရပါ"

@app.route('/', methods=['GET'])
def home():
    return "🚀 Live Dedicated Engine v50.0 [Advanced Intent & Clean Tracking] - Online!"

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
                            message_data = messaging_event["message"]
                            mid = message_data.get("mid")
                            
                            if mid in app.processed_mid: return "EVENT_RECEIVED", 200
                            if mid:
                                app.processed_mid.add(mid)
                                if len(app.processed_mid) > 50: app.processed_mid.pop()

                            sender_id = str(messaging_event["sender"]["id"])
                            customer_msg = message_data.get("text", "").strip()
                            if not customer_msg: continue

                            # --- RULE 1: COMPLAIN & BAD FEEDBACK DETECTION ---
                            complain_keywords = ["မရဘူး", "ပျက်", "မှား", "မကြိုက်", "နောက်ကျ", "ကြာတယ်", "အဆင်မပြေ", "မတက်ဘူး", "လဲ", "ပြန်အမ်း", "တိုင်"]
                            if any(kw in customer_msg.lower() for kw in complain_keywords):
                                fallback_reply = "မင်္ဂလာပါရှင်၊ လူကြီးမင်း ကြုံတွေ့ရတဲ့ အခက်အခဲအတွက် စိတ်မကောင်းပါဘူးရှင်။ အကြောင်းအရာကို ဝန်ထမ်းများမှ အမြန်ဆုံး စစ်ဆေးပြီး အဆင်ပြေအောင် ဖြေရှင်းပေးပါမည်ရှင်။ ခေတ္တစောင့်ဆိုင်းပေးပါဦးရှင့်။"
                                send_fb_message(sender_id, fallback_reply)
                                
                                # Complain ဖြစ်ပါကလည်း Telegram သို့ လိုရင်းတိုရှင်း ပို့မည်
                                comp_alert = f"⚠️ *COMPLAIN သတိပေးချက်*\n\n👤 *ID:* `{sender_id}`\n💬 *ဝယ်သူစာ:* {customer_msg}"
                                send_telegram_message(FINANCE_GROUP, comp_alert)
                                continue

                            # Gemini Core AI Integration
                            try:
                                sheet_data = call_google_script({"action": "read"})
                                inventory_context = ""
                                if sheet_data and sheet_data.get("status") == "success" and "data" in sheet_data:
                                    inventory_context = "📦 ဆိုင်ရှိ ပစ္စည်းများနှင့် လက်ကျန်စာရင်း -\n"
                                    for item in sheet_data["data"]:
                                        p_name = item.get("product_name") or item.get("productname") or "မသိပါ"
                                        p_price = item.get("price") or "ညှိနှိုင်း"
                                        p_stock = item.get("stock") or "0"
                                        inventory_context += f"- {p_name} | စျေး: {p_price} ကျပ် | လက်ကျန်: {p_stock} ခု\n"

                                # [🎯 ULTRA SYSTEM INSTRUCTION] AI ကို စကားမများစေရန် ဥပဒေသတင်းကျပ်စွာ ပေးခြင်း
                                system_instruction = (
                                    "You are an AI assistant for a retail online shop. Answer in Burmese yanjayswar and strictly brief.\n"
                                    "RULES:\n"
                                    "1. ONLY answer about product price and stock availability based on the context provided.\n"
                                    "2. If the user gives phone/address or wants to buy, check stock. If available, reply exactly: 'အမှာစာကို စနစ်တကျ မှတ်တမ်းတင်ပေးပြီးပါပြီရှင်။'\n"
                                    "3. Do not chat or give extra filler words. Keep it to 1-2 lines maximum."
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

                                # --- RULE 2: SMART COD / PRE-PAID & TELEGRAM CLEAN NOTIFICATION ---
                                order_triggers = ["ဝယ်", "ယူမယ်", "ငွေလွှဲ", "kpay", "wave", "ဘဏ်", "09", "လိပ်စာ", "မြို့", "လမ်း", "ယူမည်"]
                                if any(tok in customer_msg.lower() for tok in order_triggers):
                                    # Payment Method ဉာဏ်ရည်တုဖြင့် ခွဲခြားခြင်း
                                    pay_method = "COD (ပစ္စည်းရောက်မှငွေချေ)"
                                    prepaid_signals = ["လွှဲပြီး", "kpay", "wave", "screenshot", "ဘဏ်", "ကတ်", "cb", "ayeyar", "kbz"]
                                    if any(ps in customer_msg.lower() for ps in prepaid_signals):
                                        pay_method = "Pre-paid (ငွေကြိုလွှဲ)"

                                    phone_extracted = extract_phone(customer_msg)
                                    
                                    # [⚠️ CLEAN TELEGRAM FORMAT] စာသားအပိုများ လုံးဝမပါဘဲ ကွက်တိ စာရင်းဇယားပုံစံသာ ပို့ပေးမည့်စနစ်
                                    clean_tg_text = (
                                        f"📋 *အမှာစာအသစ် ရရှိပါသည်*\n"
                                        f"👤 *Customer ID:* `{sender_id}`\n"
                                        f"💬 *ဝယ်သူစာ:* {customer_msg}\n"
                                        f"📱 *ဖုန်းနံပါတ်:* {phone_extracted}\n"
                                        f"💳 *ငွေချေစနစ်:* {pay_method}"
                                    )
                                    send_telegram_message(FINANCE_GROUP, clean_tg_text)
                                    send_telegram_message(PACKING_GROUP, clean_tg_text)

                                send_fb_message(sender_id, ai_reply)

                            except Exception as e:
                                send_fb_message(sender_id, "မင်္ဂလာပါရှင်၊ မကြာမီ ဝန်ထမ်းများမှ ပြန်လည်ဖြေကြားပေးပါမည်ရှင်။")
                                
                return "EVENT_RECEIVED", 200
        except:
            return jsonify({"status": "error"}), 500
    return "Not Found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
