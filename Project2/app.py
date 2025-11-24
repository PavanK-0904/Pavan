
from flask_cors import CORS
from flask import Flask, request, jsonify, session, render_template



from core import handle_chat_logic, parse_booking_slots


from services_pms import (
    qlo_get,
    qlo_post,
    internal_create_customer,
    create_housekeeping_ticket,
    create_booking,
    pms_check_availability_pricing,
)


from services_rag import (
    CUSTOMER_STORE,
    BOOKING_STORE,
    ROOM_TYPE_STORE,
    build_all_rag,
)

from config import FLASK_SECRET_KEY

app = Flask(__name__)
CORS(app)
app.secret_key = FLASK_SECRET_KEY



@app.route("/")
def home():
    return "<h3>Nexrova AI Backend Running</h3>"


@app.route("/chat/message", methods=["POST"])
def chat_message():
    user_message = request.json.get("message", "")
    response = handle_chat_logic(user_message, session)
    return jsonify({"response": response})

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/home")
def home_page():
    return render_template("index.html")

@app.route("/auto_checkin", methods=["POST"])
def auto_checkin():
    text = request.json.get("text", "")
    parsed = parse_booking_slots(text)

    created = None
    if parsed.get("name") and parsed.get("email"):
        names = parsed["name"].split()
        firstname = names[0]
        lastname = " ".join(names[1:]) if len(names) > 1 else "Guest"
        phone = parsed.get("phone", "")

        cid = internal_create_customer(firstname, lastname, parsed["email"], phone)
        if cid:
            created = {"customer_id": cid}

    return jsonify({"parsed": parsed, "created": created})


@app.route("/create_customer", methods=["POST"])
def api_create_customer():
    data = request.json
    firstname = data.get("firstname")
    lastname = data.get("lastname")
    email = data.get("email")
    phone = data.get("phone")

    cid = internal_create_customer(firstname, lastname, email, phone)
    if not cid:
        return jsonify({"status": "error", "message": "Failed to create customer"}), 500

    return jsonify({"status": "ok", "customer_id": cid})


@app.route("/create_housekeeping_ticket", methods=["POST"])
def api_create_housekeeping():
    data = request.json
    ticket = create_housekeeping_ticket(
        guest_name=data.get("guest_name", "Guest"),
        room=data.get("room", "Unknown"),
        text=data.get("text", ""),
        priority=data.get("priority", "normal")
    )
    return jsonify({"status": "ok", "ticket": ticket})


@app.route("/rag_sync", methods=["POST"])
def api_rag_sync():
    result = build_all_rag()
    return jsonify({"status": "ok", "result": result})


@app.route("/rag_status", methods=["GET"])
def api_rag_status():
    return jsonify({
        "customers": len(CUSTOMER_STORE.metadata),
        "bookings": len(BOOKING_STORE.metadata),
        "room_types": len(ROOM_TYPE_STORE.metadata)
    })



if __name__ == "__main__":
    print("[STARTUP] Building RAG indexes...")
    build_all_rag()
    print("[STARTUP] Nexrova AI backend ready.")
    app.run(host="0.0.0.0", port=5000, debug=True)
