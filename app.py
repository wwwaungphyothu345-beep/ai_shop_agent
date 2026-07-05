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

if not hasattr(app, 'processed_mid'): app.processed_mid = set()
if not hasattr(app, 'user_states'): app.user_states = {}

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
        res = requests.post(SCRIPT_URL, headers={"Content-Type": "application/json"}, data=json.dumps(payload), timeout=12)
        if res.status_code == 200: return res.json()
    except: pass
    return None

@app.route('/', methods=['GET'])
def home():
    return "🚀 Live Dedicated Engine v60.0 [Advanced E-Commerce Workflow] - Online!"

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
                        
                        # --- TELEGRAM GROUP မှ FINANCE CONFIRMATION စစ်ဆေးခြင်း ---
                        # (ဒီစနစ်က Telegram ဘက်ကလာတဲ့ Chat မဟုတ်ဘဲ Webhook Event တွေကို ခွဲခြားပါတယ်)
                        if messaging_event.get("message"):
                            message_data = messaging_event["message"]
                            mid = message_data.get("mid")
                            
                            if mid in app.processed_mid: return "EVENT_RECEIVED", 200
                            if mid:
                                app.processed_mid.add(mid)
                                if len(app.processed_mid) > 50: app.processed_mid.pop()

                            sender_id = str(messaging_event["sender"]["id"])
                            
                            # ဓာတ်ပုံ သို့မဟုတ် Screenshot လာပါက (Pre-paid / Transfer Capture)
                            if "attachments" in message_data:
                                for att in message_data["attachments"]:
                                    if att["type"] == "image":
                                        img_url = att["payload"]["url"]
                                        state = app.user_states.get(sender_id, {})
                                        
                                        fn_alert = (
                                            f"💰 *ငွေလွှဲပေးပို့လာပါသည် (Finance Group အတည်ပြုရန်)*\n\n"
                                            f"👤 *Customer ID:* `{sender_id}`\n"
                                            f"📦 *ပစ္စည်း:* {state.get('product', 'မသိရပါ')}\n"
                                            f"📱 *ဖုန်း:* {state.get('phone', 'မသိရပါ')}\n"
                                            f"📍 *လိပ်စာ:* {state.get('address', 'မသိရပါ')}\n"
                                            f"🖼️ *ငွေလွှဲပြေစာ:* [ကြည့်ရှုရန်]({img_url})"
                                        )
                                        send_telegram_message(FINANCE_GROUP, fn_alert)
                                        send_fb_message(sender_id, "ငွေလွှဲပြေစာ (Screenshot) ရရှိပါပြီရှင်။ ငွေစာရင်းဌာနမှ စစ်ဆေးအတည်ပြုပေးနေပါသဖြင့် ခေတ္တစောင့်ဆိုင်းပေးပါရှင်။")
                                return "EVENT_RECEIVED", 200

                            customer_msg = message_data.get("text", "").strip()
                            if not customer_msg: continue

                            # State ယူခြင်း
                            if sender_id not in app.user_states:
                                app.user_states[sender_id] = {"step": "browsing", "product": "", "address": "", "phone": ""}
                            
                            state = app.user_states[sender_id]

                            # --- အဆင့်ဆင့် လုပ်ငန်းစဉ် (WORKFLOW ENGINE) ---
                            
                            # ၁။ ပစ္စည်းမေးမြန်းခြင်း အဆင့်
                            if state["step"] == "browsing":
                                sheet_data = call_google_script({"action": "read"})
                                inventory_context = ""
                                if sheet_data and sheet_data.get("status") == "success" and "data" in sheet_data:
                                    for item in sheet_data["data"]:
                                        p_name = item.get("product_name") or item.get("productname") or ""
                                        p_price = item.get("price") or ""
                                        p_stock = item.get("stock") or "0"
                                        inventory_context += f"- {p_name} | စျေး: {p_price} | လက်ကျန်: {p_stock}\n"

                                system_instruction = (
                                    "You are a strict retail assistant. Only state product price and stock from context. "
                                    "If user wants to buy, ask exactly: 'ဝယ်ယူမည့် ပစ္စည်းအမည်နှင့် အရေအတွက်ကို ပြောပေးပါရှင်။'"
                                )
                                gemini_payload = {
                                    "contents": [{"parts": [{"text": f"{inventory_context}\n\nCustomer: {customer_msg}"}]}],
                                    "systemInstruction": {"parts": [{"text": system_instruction}]}
                                }
                                gemini_res = requests.post(get_gemini_url(), headers={'Content-Type': 'application/json'}, data=json.dumps(gemini_payload), timeout=10)
                                ai_reply = gemini_res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                                
                                if "ဝယ်ယူမည့်" in ai_reply or "ပစ္စည်းအမည်" in ai_reply:
                                    state["step"] = "waiting_product"
                                send_fb_message(sender_id, ai_reply)
                                
                            elif state["step"] == "waiting_product":
                                state["product"] = customer_msg
                                state["step"] = "waiting_address"
                                send_fb_message(sender_id, "ပို့ဆောင်ပေးရမည့် လိပ်စာ (မြို့နယ်အပါအဝင်) ကို ပြောပေးပါရှင်။")

                            elif state["step"] == "waiting_address":
                                state["address"] = customer_msg
                                state["step"] = "waiting_phone"
                                send_fb_message(sender_id, "ဆက်သွယ်ရန် ဖုန်းနံပါတ်လေး ပြောပေးပါရှင်။")

                            elif state["step"] == "waiting_phone":
                                state["phone"] = customer_msg
                                
                                # --- GOOGLE SHEET မှ COD မြို့နယ်များနှင့် တိုက်စစ်ခြင်း ---
                                sheet_townships = call_google_script({"action": "read_cod_townships"})
                                cod_available = False
                                if sheet_townships and "data" in sheet_townships:
                                    for t in sheet_townships["data"]:
                                        t_name = str(t.get("township", "")).lower().strip()
                                        if t_name and t_name in state["address"].lower():
                                            cod_available = True
                                            break
                                
                                if cod_available:
                                    # COD ရပါက အမှာစာကို အလိုအလျောက် အတည်ပြုပြီး Packing သို့ တန်းပို့သည်
                                    send_fb_message(sender_id, f"လူကြီးမင်းတို့ မြို့နယ်သည် အိမ်အရောက်ငွေချေ (COD) ရသော မြို့နယ်ဖြစ်သဖြင့် အမှာစာကို စနစ်တကျ မှတ်တမ်းတင်ပေးလိုက်ပါပြီရှင်။")
                                    
                                    pk_alert = (
                                        f"📦 *အမှာစာအသစ် ရရှိပါသည် (COD System)*\n\n"
                                        f"👤 *Customer ID:* `{sender_id}`\n"
                                        f"🛍️ *ပစ္စည်းအမျိုးအစား/အရေအတွက်:* {state['product']}\n"
                                        f"📱 *ဖုန်းနံပါတ်:* {state['phone']}\n"
                                        f"📍 *ပို့ဆောင်ရမည့်လိပ်စာ:* {state['address']}\n"
                                        f"💳 *ငွေချေစနစ်:* COD (ပစ္စည်းရောက်မှငွေချေ)"
                                    )
                                    send_telegram_message(PACKING_GROUP, pk_alert)
                                    state["step"] = "completed"
                                else:
                                    # COD မရပါက ဘဏ်စာရင်းများထုတ်ပေးပြီး ငွေကြိုလွှဲခိုင်းသည်
                                    sheet_banks = call_google_script({"action": "read_banks"})
                                    bank_info = "🔹 KBZ Pay: 09xxxxxxx\n🔹 Wave Pay: 09xxxxxxx"
                                    if sheet_banks and "data" in sheet_banks:
                                        bank_info = ""
                                        for b in sheet_banks["data"]:
                                            bank_info += f"🔹 {b.get('bank_name')}: {b.get('account_no')} ({b.get('account_name')})\n"
                                            
                                    reply_msg = (
                                        f"လူကြီးမင်းတို့ မြို့နယ်သည် COD မရရှိနိုင်သေးသောကြောင့် ငွေကြိုလွှဲစနစ်ဖြင့်သာ ဆောင်ရွက်ပေးရပါမည်ရှင်။\n\n"
                                        f"💰 *လွှဲရမည့် ဘဏ်အကောင့်များ -*\n{bank_info}\n"
                                        f"ငွေလွှဲပြီးပါက ငွေလွှဲပြေစာ (Screenshot) လေး ပေးပို့ပေးပါရှင်။"
                                    )
                                    send_fb_message(sender_id, reply_msg)
                                    state["step"] = "waiting_screenshot"

                return "EVENT_RECEIVED", 200
        except Exception as e:
            return jsonify({"status": "error"}), 500
    return "Not Found", 404

# --- TELEGRAM BOT WEBHOOK (FINANCE မှ CONFIRM နှိပ်ခြင်းနှင့် PACKING မှ VOUCHER တင်ခြင်း စီမံရန်) ---
@app.route('/telegram', methods=['POST'])
def telegram_webhook():
    try:
        tg_data = request.get_json() or {}
        if "message" in tg_data:
            msg = tg_data["message"]
            chat_id = str(msg["chat"]["id"])
            text = msg.get("text", "").strip()

            # ၁။ Finance Group ကနေ "confirm [Customer_ID]" ဟု ရိုက်၍ အတည်ပြုခြင်း
            if chat_id == FINANCE_GROUP and text.lower().startswith("confirm"):
                parts = text.split()
                if len(parts) > 1:
                    c_id = parts[1]
                    state = app.user_states.get(c_id, {})
                    
                    # Packing Group သို့ အမှာစာအချက်အလက်သန့်သန့် ပို့ပေးခြင်း
                    pk_alert = (
                        f"📦 *ငွေလွှဲအတည်ပြုပြီး အမှာစာ (Pre-paid)*\n\n"
                        f"👤 *Customer ID:* `{c_id}`\n"
                        f"🛍️ *ပစ္စည်းအမျိုးအစား/အရေအတွက်:* {state.get('product', 'မသိရပါ')}\n"
                        f"📱 *ဖုန်းနံပါတ်:* {state.get('phone', 'မသိရပါ')}\n"
                        f"📍 *ပို့ဆောင်ရမည့်လိပ်စာ:* {state.get('address', 'မသိရပါ')}\n"
                        f"💳 *ငွေချေစနစ်:* Pre-paid (ငွေလွှဲဝင်ပြီး)"
                    )
                    send_telegram_message(PACKING_GROUP, pk_alert)
                    send_telegram_message(FINANCE_GROUP, f"✅ Customer ID `{c_id}` ၏ အမှာစာအား Packing Team ထံသို့ လွှဲပြောင်းပေးလိုက်ပါပြီ။")
                    send_fb_message(c_id, "လူကြီးမင်း၏ ငွေလွှဲမှုကို အတည်ပြုပြီးပါပြီရှင်။ ပစ္စည်းများကို ထုပ်ပိုးရေးဌာနသို့ လွှဲပြောင်းပေးလိုက်ပြီဖြစ်လို့ ခေတ္တစောင့်ဆိုင်းပေးပါရှင်။")

            # ၂။ Packing Group ကနေ Customer ID ရိုက်ပြီး ဘောင်ချာပုံ/စာ ပို့ခြင်း
            elif chat_id == PACKING_GROUP and ("photo" in msg or "document" in msg):
                # စာသားထဲတွင် Customer ID ပါမပါ စစ်ဆေးခြင်း
                caption = msg.get("caption", "").strip()
                c_id_match = re.search(r'(\d{15,20})', caption)
                if c_id_match:
                    c_id = c_id_match.group(1)
                    send_fb_message(c_id, f"📦 လူကြီးမင်းမှာယူထားသော ပစ္စည်းအား ထုပ်ပိုးပြီးစီးသွားပါပြီရှင်။ ပစ္စည်းပေးပို့မှု ဘောင်ချာ (Voucher) အား ပူးတွဲပေးပို့အပ်ပါတယ်ရှင် -\n\n{caption}")
                    send_telegram_message(PACKING_GROUP, f"✅ Customer `{c_id}` ထံသို့ ဘောင်ချာ ပေးပို့ပြီးပါပြီ။")

        return jsonify({"status": "ok"}), 200
    except:
        return jsonify({"status": "error"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
