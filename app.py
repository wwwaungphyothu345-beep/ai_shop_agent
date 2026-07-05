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
        res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
        print(f"📡 FB SEND STATUS: {res.status_code} | RESPONSE: {res.text}")
    except Exception as e:
        print(f"❌ FB SEND EXCEPTION: {e}")

def send_telegram_with_buttons(chat_id, text, customer_id):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": {
                "inline_keyboard": [
                    [
                        {"text": "Confirm 🟢", "callback_data": f"conf_{customer_id}"},
                        {"text": "Reject 🔴", "callback_data": f"rej_{customer_id}"}
                    ]
                ]
            }
        }
        requests.post(url, json=payload, timeout=10)
    except: pass

def send_telegram_message(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=10)
    except: pass

def call_google_script(payload):
    try:
        res = requests.post(SCRIPT_URL, headers={"Content-Type": "application/json"}, data=json.dumps(payload), timeout=15)
        if res.status_code == 200: return res.json()
    except: pass
    return None

@app.route('/', methods=['GET'])
def home():
    return "🚀 Live Dedicated Engine v75.0 [Absolute Active] - Online!"

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        challenge = request.args.get('hub.challenge')
        if challenge: return challenge, 200
        return "Active", 200
        
    elif request.method == 'POST':
        try:
            data = request.get_json() or {}
            print(f"📩 INCOMING WEBHOOK DATA: {json.dumps(data)}")
            
            if data.get("object") == "page":
                for entry in data.get("entry", []):
                    for messaging_event in entry.get("messaging", []):
                        if messaging_event.get("message"):
                            message_data = messaging_event["message"]
                            mid = message_data.get("mid")
                            
                            if mid in app.processed_mid: return "EVENT_RECEIVED", 200
                            if mid:
                                app.processed_mid.add(mid)
                                if len(app.processed_mid) > 100: app.processed_mid.clear()

                            sender_id = str(messaging_event["sender"]["id"])
                            
                            # Image / Screenshot Handler
                            if "attachments" in message_data:
                                for att in message_data["attachments"]:
                                    if att["type"] == "image":
                                        img_url = att["payload"]["url"]
                                        state = app.user_states.get(sender_id, {})
                                        
                                        fn_alert = (
                                            f"💰 *ငွေလွှဲပြေစာ ရရှိပါသည်*\n\n"
                                            f"👤 *Customer ID:* `{sender_id}`\n"
                                            f"📦 *ပစ္စည်း:* {state.get('product', 'စစ်ဆေးရန်')}\n"
                                            f"📱 *ဖုန်း:* {state.get('phone', 'စစ်ဆေးရန်')}\n"
                                            f"📍 *လိပ်စာ:* {state.get('address', 'စစ်ဆေးရန်')}\n"
                                            f"🖼️ *ငွေလွှဲပြေစာ:* [ကြည့်ရှုရန်]({img_url})"
                                        )
                                        send_telegram_with_buttons(FINANCE_GROUP, fn_alert, sender_id)
                                        send_fb_message(sender_id, "ငွေလွှဲပြေစာ ရရှိပါပြီရှင်။ ငွေစာရင်းဌာနမှ စစ်ဆေးအတည်ပြုပေးနေပါသဖြင့် ခေတ္တစောင့်ဆိုင်းပေးပါရှင်။")
                                return "EVENT_RECEIVED", 200

                            customer_msg = message_data.get("text", "").strip()
                            if not customer_msg: continue

                            if sender_id not in app.user_states:
                                app.user_states[sender_id] = {"step": "browsing", "product": "", "address": "", "phone": ""}
                            
                            state = app.user_states[sender_id]

                            # Workflow Logic
                            try:
                                sheet_data = call_google_script({"action": "read"})
                                inventory_context = ""
                                if sheet_data and sheet_data.get("status") == "success" and "data" in sheet_data:
                                    for item in sheet_data["data"]:
                                        p_name = item.get("product_name") or item.get("productname") or ""
                                        p_price = item.get("price") or ""
                                        p_stock = item.get("stock") or "0"
                                        inventory_context += f"- {p_name} | စျေး: {p_price} | လက်ကျန်: {p_stock}\n"

                                system_instruction = (
                                    "You are a helpful retail shop assistant. Answer in Burmese briefly. "
                                    "If the customer expresses intent to buy, ask them exactly: 'ဝယ်ယူမည့် ပစ္စည်းအမည်နှင့် အရေအတွက်ကို ပြောပေးပါရှင်။'"
                                )
                                gemini_payload = {
                                    "contents": [{"parts": [{"text": f"{inventory_context}\n\nCustomer: {customer_msg}"}]}],
                                    "systemInstruction": {"parts": [{"text": system_instruction}]}
                                }
                                
                                gemini_res = requests.post(get_gemini_url(), headers={'Content-Type': 'application/json'}, data=json.dumps(gemini_payload), timeout=12)
                                res_json = gemini_res.json()
                                
                                ai_reply = ""
                                if "candidates" in res_json and len(res_json["candidates"]) > 0:
                                    ai_reply = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                                
                                if not ai_reply:
                                    ai_reply = "မင်္ဂလာပါရှင်၊ ပစ္စည်းနှင့်ပတ်သက်ပြီး သိလိုသည်များကို မေးမြန်းနိုင်ပါတယ်ရှင်။"

                                # Step Handler
                                if state["step"] == "browsing" and ("ဝယ်ယူမည့်" in ai_reply or "ပစ္စည်းအမည်" in ai_reply):
                                    state["step"] = "waiting_product"
                                    send_fb_message(sender_id, ai_reply)
                                    continue
                                    
                                elif state["step"] == "waiting_product":
                                    state["product"] = customer_msg
                                    state["step"] = "waiting_address"
                                    send_fb_message(sender_id, "ပို့ဆောင်ပေးရမည့် လိပ်စာ (မြို့နယ်အပါအဝင်) ကို ပြောပေးပါရှင်။")
                                    continue
                                    
                                elif state["step"] == "waiting_address":
                                    state["address"] = customer_msg
                                    state["step"] = "waiting_phone"
                                    send_fb_message(sender_id, "ဆက်သွယ်ရန် ဖုန်းနံပါတ်လေး ပြောပေးပါရှင်။")
                                    continue
                                    
                                elif state["step"] == "waiting_phone":
                                    state["phone"] = customer_msg
                                    
                                    sheet_townships = call_google_script({"action": "read_cod_townships"})
                                    cod_available = False
                                    if sheet_townships and "data" in sheet_townships:
                                        for t in sheet_townships["data"]:
                                            t_name = str(t.get("township", "")).lower().strip()
                                            if t_name and t_name in state["address"].lower():
                                                cod_available = True
                                                break
                                    
                                    if cod_available:
                                        send_fb_message(sender_id, f"လူကြီးမင်းတို့ မြို့နယ်သည် အိမ်အရောက်ငွေချေ (COD) ရသော မြို့နယ်ဖြစ်သဖြင့် အမှာစာကို စနစ်တကျ မှတ်တမ်းတင်ပေးလိုက်ပါပြီရှင်။")
                                        pk_alert = (
                                            f"📦 *အမှာစာအသစ် ရရှိပါသည် (COD System)*\n\n"
                                            f"👤 *Customer ID:* `{sender_id}`\n"
                                            f"🛍️ *ပစ္စည်းအမျိုးအစား/အရေအတွက်:* {state['product']}\n"
                                            f"📱 *ဖုန်းနံပါတ်:* {state['phone']}\n"
                                            f"📍 *ပို့ဆောင်ရမည့်လိပ်စာ:* {state['address']}\n"
                                            f"💳 *ငွေချေစနစ်:* COD"
                                        )
                                        send_telegram_message(PACKING_GROUP, pk_alert)
                                        state["step"] = "completed"
                                    else:
                                        sheet_banks = call_google_script({"action": "read_banks", "sheet_name": "settings"})
                                        bank_info = ""
                                        if sheet_banks and "data" in sheet_banks and len(sheet_banks["data"]) > 0:
                                            for b in sheet_banks["data"]:
                                                b_name = b.get("bank_name") or b.get("bankname") or "Bank"
                                                b_no = b.get("account_no") or b.get("accountno") or "0000"
                                                b_owner = b.get("account_name") or b.get("accountname") or ""
                                                bank_info += f"🔹 {b_name}: {b_no} ({b_owner})\n"
                                        else:
                                            bank_info = "🔹 KBZ Pay: 09xxxxxx\n🔹 Wave Pay: 09xxxxxx\n"
                                                
                                        reply_msg = (
                                            f"လူကြီးမင်းတို့ မြို့နယ်သည် COD မရရှိနိုင်သေးသောကြောင့် Ngwe Kyo Lwe စနစ်ဖြင့်သာ ဆောင်ရွက်ပေးရပါမည်ရှင်။\n\n"
                                            f"💰 *လွှဲရမည့် ဘဏ်အကောင့်များ -*\n{bank_info}\n"
                                            f"ငွေလွှဲပြီးပါက ငွေလွှဲပြေစာ (Screenshot) လေး ပေးပို့ပေးပါရှင်။"
                                        )
                                        send_fb_message(sender_id, reply_msg)
                                        state["step"] = "waiting_screenshot"
                                    continue

                                # ပုံမှန် စကားပြောအဆင့်
                                send_fb_message(sender_id, ai_reply)

                            except Exception as gem_err:
                                print(f"❌ GEMINI/LOGIC ERROR: {gem_err}")
                                send_fb_message(sender_id, "မင်္ဂလာပါရှင်၊ လူကြီးမင်းမေးမြန်းမှုကို ဝန်ထမ်းများမှ မကြာမီ စစ်ဆေးဖြေကြားပေးပါမည်ရှင်။")

                return "EVENT_RECEIVED", 200
        except Exception as main_err:
            print(f"❌ MAIN WEBHOOK CRITICAL ERROR: {main_err}")
            return "EVENT_RECEIVED", 200
    return "Not Found", 404

@app.route('/telegram', methods=['POST'])
def telegram_webhook():
    try:
        tg_data = request.get_json() or {}
        if "callback_query" in tg_data:
            cb = tg_data["callback_query"]
            cb_id = cb["id"]
            data_field = cb["data"]
            chat_id = str(cb["message"]["chat"]["id"])
            message_id = cb["message"]["message_id"]
            
            if data_field.startswith("conf_"):
                c_id = data_field.replace("conf_", "")
                state = app.user_states.get(c_id, {})
                
                p_name = state.get('product') or "စစ်ဆေးရန်"
                p_phone = state.get('phone') or "စစ်ဆေးရန်"
                p_addr = state.get('address') or "စစ်ဆေးရန်"
                
                pk_alert = (
                    f"📦 *ငွေလွှဲအတည်ပြုပြီး အမှာစာ (Pre-paid)*\n\n"
                    f"👤 *Customer ID:* `{c_id}`\n"
                    f"🛍️ *ပစ္စည်းအမျိုးအစား/အရေအတွက်:* {p_name}\n"
                    f"📱 *ဖုန်းနံပါတ်:* {p_phone}\n"
                    f"📍 *ပို့ဆောင်ရမည့်လိပ်စာ:* {p_addr}\n"
                    f"💳 *ငွေချေစနစ်:* Pre-paid"
                )
                send_telegram_message(PACKING_GROUP, pk_alert)
                send_fb_message(c_id, "လူကြီးမင်း၏ Ngwe Lwal Hmu Ko Ati Pyu Pi Par Pyi Shin. Po Saung Pay Myi Voucher Ar Myan Sone Pay Po Pay Par Myi.")
                
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={
                    "chat_id": chat_id, "message_id": message_id,
                    "text": f"✅ *အတည်ပြုပြီးပါပြီ* (Customer ID: `{c_id}`)"
                })
                
            elif data_field.startswith("rej_"):
                c_id = data_field.replace("rej_", "")
                send_fb_message(c_id, "လူကြီးမင်း ပေးပို့လာသော ငွေလွှဲပြေစာအား စစ်ဆေးရာတွင် အဆင်မပြေမှုတစ်ခုရှိနေပါသဖြင့် ဝန်ထမ်းများမှ ချက်ချင်း ဆက်သွယ်ပေးပါမည်ရှင်။")
                
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={
                    "chat_id": chat_id, "message_id": message_id,
                    "text": f"❌ *ငြင်းပယ်လိုက်ပါသည်* (Customer ID: `{c_id}`)"
                })
                
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cb_id})

        return jsonify({"status": "ok"}), 200
    except:
        return jsonify({"status": "ok"}), 200

if __name__ == '__main__':

cd ~/ai_shop_agent && rm -f app.py && cat << 'EOF' > app.py
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
