import json
import re
from datetime import datetime
from config import (
    PERPLEXITY_API_KEY,
    PERPLEXITY_MODEL,
    DEFAULT_NOTIFICATION_TO,
)
from services_pms import (
    internal_create_customer,
    create_booking,
    pms_check_availability_pricing,
)
from services_rag import BOOKING_STORE
import requests



def call_perplexity(prompt, system="You are Nexrova AI assistant."):
    if not PERPLEXITY_API_KEY:
        return "LLM key not configured."

    try:
        url = "https://api.perplexity.ai/chat/completions"
        headers = {
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": PERPLEXITY_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.0,
        }

        r = requests.post(url, json=payload, headers=headers, timeout=30)
        data = r.json()

        return data.get("choices", [{}])[0].get("message", {}).get("content", "")

    except Exception as e:
        return f"LLM error: {e}"



def send_whatsapp(message, to=DEFAULT_NOTIFICATION_TO):
    print(f"[WHATSAPP MOCK] → {to}: {message}")
    return True




def detect_intent(msg):
    msg = msg.lower()

    if any(w in msg for w in ["towel", "clean", "housekeeping", "laundry"]):
        return "housekeeping"

    if any(w in msg for w in ["book", "reservation", "check in", "check-in"]):
        return "start_booking"

    if "room type" in msg or "i want" in msg:
        return "select_room"

    if "customer" in msg or "booking" in msg or "availability" in msg:
        return "pms_query"

    return "chitchat"




def parse_booking_slots(text):
    system_prompt = (
        "Extract booking information as JSON with keys: "
        "name, email, phone, check_in_date, check_out_date, guests."
    )

    raw = call_perplexity(f"Extract: {text}", system_prompt)

    try:
        data = json.loads(raw)
        return data
    except:
        return regex_fallback_slots(text)



def regex_fallback_slots(text):
    email = None
    m = re.search(r"[\w\.-]+@[\w\.-]+", text)
    if m:
        email = m.group(0)

    phone = None
    n = re.search(r"\+?\d{9,15}", text)
    if n:
        phone = n.group(0)

    name_match = re.search(r"(?:my name is|i am)\s+([A-Za-z ]+)", text, re.I)
    name = name_match.group(1).strip() if name_match else None

    date_from = None
    date_to = None
    d1 = re.search(r"from (\d{4}-\d{2}-\d{2})", text)
    d2 = re.search(r"to (\d{4}-\d{2}-\d{2})", text)
    if d1:
        date_from = d1.group(1)
    if d2:
        date_to = d2.group(1)

    guests = None
    g = re.search(r"(\d+)\s+(guests|people)", text)
    if g:
        guests = int(g.group(1))

    return {
        "name": name,
        "email": email,
        "phone": phone,
        "check_in_date": date_from,
        "check_out_date": date_to,
        "guests": guests
    }




def handle_chat_logic(message, session):
    intent = detect_intent(message)
    flow = session.get("booking_flow", {"state": "IDLE", "slots": {}})

 
    if intent == "housekeeping":
        ticket = {
            "id": len(BOOKING_STORE.metadata) + 1,
            "text": message,
            "created_at": datetime.utcnow().isoformat()
        }
        send_whatsapp(f"Housekeeping request: {message}")
        return f"Housekeeping request noted. Ticket #{ticket['id']}."

    if intent == "start_booking":
        slots = parse_booking_slots(message)

        
        for k, v in slots.items():
            if v:
                flow["slots"][k] = v

        session["booking_flow"] = flow

        needed = []
        required = ["name", "email", "check_in_date", "check_out_date", "guests"]

        for k in required:
            if not flow["slots"].get(k):
                needed.append(k)

        if needed:
            return f"I still need: {', '.join(needed)}."

        
        name = flow["slots"]["name"]
        email = flow["slots"]["email"]
        phone = flow["slots"].get("phone", "")
        names = name.split()
        cid = internal_create_customer(names[0], " ".join(names[1:]) if len(names) > 1 else "Guest", email, phone)

        if cid:
            flow["slots"]["customer_id"] = cid

        
        rooms = pms_check_availability_pricing(
            flow["slots"]["check_in_date"],
            flow["slots"]["check_out_date"],
            flow["slots"]["guests"]
        )

        if not rooms:
            return "Sorry, no rooms available for those dates."

        flow["available_rooms"] = {r["id"]: r for r in rooms}
        flow["state"] = "AWAITING_ROOM_CHOICE"
        session["booking_flow"] = flow

        msg = "Available rooms:\n"
        for r in rooms:
            msg += f"- Room Type {r['id']}: {r['name']} (${r['total_price']})\n"

        return msg + "\nPlease select a room type ID."

    
    if intent == "select_room" and flow.get("state") == "AWAITING_ROOM_CHOICE":
        m = re.search(r"(\d+)", message)
        if not m:
            return "Please provide a valid room type ID."

        rid = m.group(1)

        if rid not in flow.get("available_rooms", {}):
            return "Invalid room type."

        room = flow["available_rooms"][rid]

       
        booking_resp = create_booking(
            flow["slots"]["customer_id"],
            rid,
            flow["slots"]["check_in_date"],
            flow["slots"]["check_out_date"]
        )

        if not booking_resp:
            return "Booking failed."

        send_whatsapp(f"Booking confirmed for Room {rid}.")
        session["booking_flow"] = {"state": "IDLE", "slots": {}}

        return f"Your booking is confirmed! Room Type {rid}. Total: ${room['total_price']}."

    return call_perplexity(message)
