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
from services_rag import BOOKING_STORE, HOTEL_INFO_STORE
import requests



def call_perplexity(prompt, system="You are Nexrova AI assistant.", history=None):
    if not PERPLEXITY_API_KEY:
        print("[LLM] Key not configured")
        return "LLM key not configured."

    try:
        print(f"[LLM] Calling Perplexity with prompt: {prompt[:50]}...")
        url = "https://api.perplexity.ai/chat/completions"
        headers = {
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json"
        }

        messages = [{"role": "system", "content": system}]
        
        
        if history:
            
            hist_to_add = history[-10:]
            
            
            if hist_to_add and hist_to_add[-1].get("role") == "user" and hist_to_add[-1].get("content") == prompt:
                hist_to_add = hist_to_add[:-1]
                
            messages.extend(hist_to_add)
            
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": PERPLEXITY_MODEL,
            "messages": messages,
            "temperature": 0.0,
        }

        r = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if r.status_code != 200:
            print(f"[LLM] Error {r.status_code}: {r.text}")
            return f"Error from AI provider: {r.status_code}"
            
        data = r.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        print(f"[LLM] Response received: {content[:50]}...")
        return content

    except Exception as e:
        print(f"[LLM] Exception: {e}")
        return f"LLM error: {e}"



def send_whatsapp(message, to=DEFAULT_NOTIFICATION_TO):
    print(f"[WHATSAPP MOCK] → {to}: {message}")
    return True




def detect_intent(msg, session=None):
    """
    Enhanced multi-layered intent classification system with confidence scoring.
    Returns tuple: (intent, confidence) or just intent for backward compatibility.
    """
    msg_lower = msg.lower()
    
    
    intent_patterns = {
        "housekeeping": [
            r"\b(need|want|request|require|get|bring|send).*\b(towel|towels|tissue|toiletries)",
            r"\b(clean|cleaning|tidy|make up).*\b(room|bathroom|bed)",
            r"\b(room|bathroom|toilet).*\b(dirty|messy|cleaning)",
            r"\b(change|replace|refresh).*\b(sheets?|bedding|linens?|towels?)",
            r"\bhousekeeping\b",
            r"\blaundry\b",
            r"\b(maintenance|repair|fix).*\b(room|ac|tv|light|shower|toilet)",
            r"\b(garbage|trash|waste)\b",
        ],
        
        
        "cancel_booking": [
            r"\b(cancel|cancellation)\b",
            r"\brefund\b",
            r"\b(don'?t|do not)\s+want.*\b(booking|reservation|room)",
        ],
        
        "modify_booking": [
            r"\b(change|modify|update|edit|reschedule).*\b(booking|reservation)",
            r"\bextend.*\b(stay|booking|reservation)",
            r"\b(move|shift|postpone).*\b(check|dates?)",
            r"\bupgrade.*\b(room|booking)",
        ],
        
        "start_booking": [
            r"\b(book|reserve)\b(?!.*\b(cancel|change|modify|upgrade))",  
            r"\bmake.*reservation\b",
            r"\b(want|need|would like).*\b(book|reserve|stay)\b",
            r"\b(i want to|can i|please)\s+check[\s-]?in\b", 
            r"\b(register|registration)\b", 
            r"\b(looking|searching).*\b(room|accommodation)",
            r"\bstay.*\bhotel\b",
            r"\b(make|create|do).*\b(booking|reservation)", 
            r"\bplace.*a.*booking\b",
            r"\b(need|want).*\b(room|accommodation|stay)\b", 
            r"\bcheck[\s-]?in\b", 
        ],
        
        "select_room": [
            r"\b(want|choose|select|pick|prefer|like|take).*\b(room|type).*\d+",
            r"\b(go with|book|reserve).*\d+",
            r"\broom\s+type\s+\d+\b",
            r"\b(deluxe|suite|standard|premium|luxury)\b",
            r"\bi'?ll\s+take\b",
        ],
        
        "check_availability": [
            r"\b(check|verify|see|show).*\bavailability\b",
            r"\b(any|do you have).*\bavailable\b",
            r"\bavailable\s+(for|on|from)\b",
            r"\b(vacancy|vacancies)\b",
            r"\brooms?\s+(free|available)\b",
        ],
        
        "amenities_inquiry": [
            r"\b(do you have|is there|are there).*\b(pool|gym|spa|restaurant|wifi|parking|breakfast)",
            r"\b(facilities|amenities|services)\b",
            r"\b(breakfast|lunch|dinner|meal).*\b(included|available|served|free)",
            r"\b(wifi|internet|parking|pool|gym|spa|restaurant|bar)\b",
            r"\broom\s+service\b",
            r"\bfree\s+(wifi|internet|parking|breakfast)",
        ],
        
        "pricing_inquiry": [
            r"\b(how much|what'?s the).*\b(price|cost|rate|charge|fee)",
            r"\bhow\s+much\b",
            r"\b(price|pricing|rates?|cost)\b",
            r"\b(cheap|expensive|affordable|budget)\b",
            r"\b(discount|offer|deal|promotion|special)s?\b",  
            r"\b(any|have).*\b(discount|offer|deal|special)",
            r"\bwhat.*are.*prices\b", 
        ],
        
        "location_directions": [
            r"\b(where|location|address)\b",
            r"\bhow.*\b(get|reach|find).*\bhotel\b",
            r"\b(near|close to|far from)\b",
            r"\b(airport|station|downtown).*\b(distance|far|close|away)",
            r"\bhow far\b",
            r"\bdirections?\b",
        ],
    }
    
    
    intent_scores = {}
    
    for intent, patterns in intent_patterns.items():
        for pattern in patterns:
            if re.search(pattern, msg_lower):
                
                intent_scores[intent] = intent_scores.get(intent, 0) + 0.7
    
    
    if session:
        flow = session.get("booking_flow", {})
        current_state = flow.get("state", "IDLE")
        
        
        if current_state == "AWAITING_ROOM_CHOICE":
            
            if re.search(r'\d+', msg):
                intent_scores["select_room"] = intent_scores.get("select_room", 0) + 0.5
        
        
        if flow.get("slots"):
            intent_scores["start_booking"] = intent_scores.get("start_booking", 0) + 0.2
    
     
    if intent_scores:
        best_intent = max(intent_scores.items(), key=lambda x: x[1])
        intent, confidence = best_intent
        
                if confidence >= 0.5:
            return intent
    
    
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
    text_lower = text.lower()
    
    
    email = None
    m = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    if m:
        email = m.group(0)

    
    phone = None
    
    n = re.search(r"(?:phone|mobile|call)?\s*[:\-]?\s*(\+?\d{9,15})", text, re.I)
    if n:
        phone = n.group(1)

    
    name = None
    
    name_match = re.search(r"(?:my name is|i am|name[:\s]+)\s+([A-Za-z ]+)", text, re.I)
    if name_match:
        raw_name = name_match.group(1).strip()
        
        stop_words = ["email", "phone", "check", "from", "to", "i need", "guests", "room"]
        for word in stop_words:
            if f" {word}" in raw_name.lower():
                raw_name = raw_name.lower().split(f" {word}")[0]
        name = raw_name.title()

    
    date_pattern = r"(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{4})"
    
    date_from = None
    date_to = None
    

    range_pattern = r"from\s+" + date_pattern + r".*?to\s+" + date_pattern
    range_match = re.search(range_pattern, text_lower)
    if range_match:
        date_from = range_match.group(1)
        date_to = range_match.group(2)
    else:
        
        d1_pattern = r"(?:check[\s-]?in|start|from)\s*[:\-]?\s*" + date_pattern
        d2_pattern = r"(?:check[\s-]?out|end|to|until)\s*[:\-]?\s*" + date_pattern
        
        d1 = re.search(d1_pattern, text_lower)
        d2 = re.search(d2_pattern, text_lower)
        if d1: date_from = d1.group(1)
        if d2: date_to = d2.group(1)

    
    def normalize_date(d):
        if not d: return None
        d = d.replace("/", "-")
        try:
            
            if re.match(r"\d{1,2}-\d{1,2}-\d{4}", d):
                parts = d.split("-")
                return f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
            return d 
        except:
            return d

    date_from = normalize_date(date_from)
    date_to = normalize_date(date_to)

    
    guests = None
   
    g = re.search(r"\b(\d{1,2})\s*(?:guests|people|adults|pax)", text_lower)
    if not g:
        g = re.search(r"(?:guests|people|adults|pax)\s*[:\-]?\s*(\d{1,2})", text_lower)
    
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
    
    if "history" not in session:
        session["history"] = []
    
    
    session["history"].append({"role": "user", "content": message})
    
    flow = session.get("booking_flow", {"state": "IDLE", "slots": {}})
    current_state = flow.get("state", "IDLE")
    
    response = ""
    intent = detect_intent(message, session)
    
    if current_state == "COLLECTING_INFO":
    
        new_slots = parse_booking_slots(message)
        
        
        for k, v in new_slots.items():
            if v:
                flow["slots"][k] = v
        
        session["booking_flow"] = flow
        
        
        needed = []
        required = ["name", "email", "check_in_date", "check_out_date", "guests"]
        
        for k in required:
            if not flow["slots"].get(k):
                needed.append(k)
        
        if needed:
            
            response = f"I still need the following details: {', '.join(needed)}."
        else:
            
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
                response = "Sorry, no rooms available for those dates. Please try different dates."
              
                flow["slots"]["check_in_date"] = None
                flow["slots"]["check_out_date"] = None
                session["booking_flow"] = flow
            else:
                flow["available_rooms"] = {r["id"]: r for r in rooms}
                flow["state"] = "AWAITING_ROOM_CHOICE"
                session["booking_flow"] = flow

                msg = "Available rooms:\n"
                for r in rooms:
                    msg += f"- Room Type {r['id']}: {r['name']} (${r['total_price']})\n"
                response = msg + "\nPlease select a room type ID."


    elif current_state == "AWAITING_ROOM_CHOICE":
        
        if intent == "select_room" or re.search(r"\b\d+\b", message):
            m = re.search(r"(\d+)", message)
            if m:
                rid = m.group(1)
                available_rooms = flow.get("available_rooms", {})
                
                
                selected_room = None
                if rid in available_rooms:
                    selected_room = available_rooms[rid]
                elif int(rid) in available_rooms:
                    selected_room = available_rooms[int(rid)]
                
                else:
                    
                    for k, v in available_rooms.items():
                        if str(k) == rid:
                            selected_room = v
                            break
                
                if selected_room:
                    
                    final_rid = selected_room["id"]
                    
                    booking_resp = create_booking(
                        flow["slots"].get("customer_id", 0), 
                        final_rid,
                        flow["slots"]["check_in_date"],
                        flow["slots"]["check_out_date"]
                    )

                    if booking_resp:
                        send_whatsapp(f"Booking confirmed for Room {final_rid}.")
                        session["booking_flow"] = {"state": "IDLE", "slots": {}}
                        response = f"Your booking is confirmed! Room Type {final_rid}. Total: ${selected_room['total_price']}."
                    else:
                        response = "Booking failed. Please try again or contact support."
                else:
                    response = "Invalid room type ID. Please select from the list above."
            else:
                response = "Please provide the room type ID."
        else:
            
            pass


    if not response:
    
        
        
        def get_hotel_context(query):
            results = HOTEL_INFO_STORE.search(query, top_k=3)
            if results:
                return "\n\nRelevant Hotel Info:\n" + "\n".join([r["text"] for r in results])
            return ""

        if intent == "housekeeping":
            ticket = {
                "id": len(BOOKING_STORE.metadata) + 1,
                "text": message,
                "created_at": datetime.utcnow().isoformat()
            }
            send_whatsapp(f"Housekeeping request: {message}")
            response = f"Housekeeping request noted. Ticket #{ticket['id']}."

        elif intent == "start_booking":
            
            flow["state"] = "COLLECTING_INFO"
            
            
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
                response = f"I'd be happy to help you book a room at Chennai BnB. I need: {', '.join(needed)}."
            else:
            
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
                    response = "Sorry, no rooms available for those dates. Please try different dates."
                    flow["slots"]["check_in_date"] = None
                    flow["slots"]["check_out_date"] = None
                    session["booking_flow"] = flow
                else:
                    flow["available_rooms"] = {r["id"]: r for r in rooms}
                    flow["state"] = "AWAITING_ROOM_CHOICE"
                    session["booking_flow"] = flow

                    msg = "Great! I found available rooms:\n"
                    for r in rooms:
                        msg += f"- Room Type {r['id']}: {r['name']} (${r['total_price']})\n"
                    response = msg + "\nPlease select a room type ID to confirm."
        
        elif intent == "check_availability":
            context = get_hotel_context(message)
            availability_prompt = (
                "You are a helpful receptionist at Chennai BnB Serviced Apartments. "
                "The guest is asking about room availability. "
                "Politely ask them for their check-in date, check-out date, and number of guests. "
                "Be warm and professional."
                f"{context}"
            )
            response = call_perplexity(message, system=availability_prompt, history=session["history"])

        elif intent == "amenities_inquiry":
            context = get_hotel_context(message)
            amenities_prompt = (
                "You are a knowledgeable receptionist at Chennai BnB Serviced Apartments. "
                "The guest is asking about hotel facilities and amenities. "
                "Use the provided hotel info to answer accurately. "
                "Highlight relevant amenities like WiFi, Kitchen, Parking, etc. "
                "Keep your response concise (2-3 sentences)."
                f"{context}"
            )
            response = call_perplexity(message, system=amenities_prompt, history=session["history"])

        elif intent == "pricing_inquiry":
            context = get_hotel_context(message)
            pricing_prompt = (
                "You are a professional receptionist at Chennai BnB Serviced Apartments. "
                "The guest is asking about pricing and rates. "
                "Use the provided hotel info to quote accurate prices for Deluxe, Premium, Suite, etc. "
                "Mention that rates may vary and offer to check specific dates. "
                "Keep your response concise (2-3 sentences)."
                f"{context}"
            )
            response = call_perplexity(message, system=pricing_prompt, history=session["history"])

        elif intent == "location_directions":
            context = get_hotel_context(message)
            location_prompt = (
                "You are a helpful receptionist at Chennai BnB Serviced Apartments. "
                "The guest is asking about our location or directions. "
                "Use the provided hotel info to give accurate directions (Thiru Nagar, near Metro). "
                "Mention nearby landmarks if helpful. "
                "Keep your response concise (2-3 sentences)."
                f"{context}"
            )
            response = call_perplexity(message, system=location_prompt, history=session["history"])

        elif intent == "modify_booking":
            context = get_hotel_context(message)
            modify_prompt = (
                "You are a helpful receptionist at Chennai BnB Serviced Apartments. "
                "The guest wants to modify their existing booking. "
                "Politely ask them for their booking reference number or the name and email "
                "used for the reservation. "
                "Refer to the modification policy in the hotel info if relevant."
                f"{context}"
            )
            response = call_perplexity(message, system=modify_prompt, history=session["history"])

        elif intent == "cancel_booking":
            context = get_hotel_context(message)
            cancel_prompt = (
                "You are a professional receptionist at Chennai BnB Serviced Apartments. "
                "The guest wants to cancel their booking. "
                "Politely ask them for their booking reference number or the name and email. "
                "Explain the cancellation policy clearly based on the provided hotel info "
                "(Free up to 24h before, etc.)."
                f"{context}"
            )
            response = call_perplexity(message, system=cancel_prompt, history=session["history"])

        else:
           
            context = get_hotel_context(message)
            receptionist_prompt = (
                "You are a friendly and professional receptionist at Chennai BnB Serviced Apartments. "
                "Greet guests warmly, answer their questions about the hotel, and help them with their needs. "
                "Use the provided hotel info to answer specific questions if applicable. "
                "Keep responses concise and helpful (2-3 sentences maximum). "
                "Always maintain a warm, professional, and welcoming tone."
                f"{context}"
            )
            response = call_perplexity(message, system=receptionist_prompt, history=session["history"])
    
    
    session["history"].append({"role": "assistant", "content": response})
    
    return response


