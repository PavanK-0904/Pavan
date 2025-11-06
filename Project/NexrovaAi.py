from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
import os
import json
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from requests.auth import HTTPBasicAuth 

from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

QW_API_KEY = os.environ.get("QLOAPPS_API_KEY", "RR9VH2RVKQGHCTNTI6WMPCUGNJBSIVB9")
QLOAPPS_API_URL = "http://localhost/prestashop/api"


template_dir = os.path.dirname(os.path.abspath(__file__))


def find_index_html_dir(start_dir):
    for root, dirs, files in os.walk(start_dir):
        if 'index.html' in files:
            return root
    
    candidates = [
        os.path.join(start_dir, 'agent', 'templates'),
        os.path.join(start_dir, 'pms', 'templates'),
        os.path.join(start_dir, 'templates'),
        os.path.join(start_dir, 'nexrova_v1-main')
    ]
    for c in candidates:
        if os.path.isdir(c) and 'index.html' in os.listdir(c):
            return c
    
    return start_dir

index_html_path = find_index_html_dir(template_dir)



PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY") 
PERPLEXITY_BASE_URL = "https://api.perplexity.ai"       
PERPLEXITY_MODEL = os.environ.get("PERPLEXITY_MODEL", "sonar-pro") 


try:
    PERPLEXITY_CLIENT = OpenAI(
        api_key=PERPLEXITY_API_KEY,
        base_url=PERPLEXITY_BASE_URL
    )
except Exception as e:
    print(f"WARNING: Perplexity client initialization failed. API Key might be missing or invalid. {e}")
    PERPLEXITY_CLIENT = None



SESSION_MEMORY = []
HOTEL_EMAIL = os.environ.get("HOTEL_AGENT_EMAIL", "your_hotel_staff_email@example.com")
HOTEL_PASS = os.environ.get("HOTEL_AGENT_PASS", "your_email_password")
HOTEL_STAFF_RECEIVER = "frontdesk@chennaibnb.com"


HOTEL_INFO = """
Hotel Name: Chennai BnB Serviced Apartments
Location: Thiru Nagar, Chennai, Tamil Nadu, India
Address: No. 45, Thiru Nagar Main Road, Chennai - 600032
Contact: +91-9876543210
Email: info@chennaibnb.com
Website: www.chennaibnb.com
Total Rooms: 8

=== CHECK-IN & CHECK-OUT ===
Check-in Time: 14:00 (2:00 PM)
Check-out Time: 11:00 (11:00 AM)
Early Check-in: Available on request (subject to availability)
Late Check-out: Available until 2:00 PM with additional charges
ID Proof Required: Yes (Aadhar, Passport, or Driver's License)

=== ROOM TYPES & PRICING ===
Deluxe Room (2 rooms): ₹3,500 per night
Premium Room (2 rooms): ₹4,500 per night
Suite (2 rooms): ₹6,000 per night
Executive Suite (2 rooms): ₹7,500 per night

All rooms include: King-size bed, AC, TV, Mini Fridge, Kitchenette, Private bathroom

=== WIFI & INTERNET ===
WiFi Network: ChennaibnB_Guest
WiFi Password: Available at reception desk (changes weekly for security)
Speed: 100 Mbps high-speed internet
Coverage: Available in all rooms and common areas
Data Limit: Unlimited

=== AMENITIES ===
✓ Free High-Speed WiFi
✓ 24/7 Front Desk Reception
✓ Daily Housekeeping Service
✓ Fully Equipped Kitchen Facilities
✓ Free Parking (Covered & Open)
✓ Air Conditioning in all rooms
✓ Smart TV with streaming services
✓ Laundry Service (paid)
✓ Iron & Ironing Board (on request)
✓ Hot Water 24/7
✓ Power Backup Generator
✓ CCTV Security
✓ Fire Safety Equipment

=== KITCHEN FACILITIES ===
Kitchen Hours: 24/7 Access
Facilities Include: Refrigerator, Microwave, Induction Cooktop, Cookware, Utensils, Cutlery, Dining Table
Grocery Delivery: Available through Swiggy Instamart, Blinkit, Zepto
Complimentary: Tea, Coffee, Sugar, Basic spices

=== DINING & FOOD ===
Breakfast: Complimentary South Indian breakfast (7:00 AM - 10:00 AM)
Breakfast Menu: Idli, Dosa, Vada, Upma, Pongal, Coffee, Tea, Fresh Fruits
Lunch & Dinner: Not provided (kitchen available for self-cooking)
Food Delivery: Swiggy, Zomato delivery accepted
Nearby Restaurants: 
  - Saravana Bhavan (500m) - South Indian
  - Anjappar (800m) - Chettinad Cuisine
  - Domino's Pizza (1km)
  - KFC (1.2km)

=== HOUSEKEEPING ===
Room Cleaning: Daily between 10:00 AM - 12:00 PM
Towel Change: Daily
Bed Linen Change: Every 2 days (or on request)
Extra Service: Available on request at reception
Emergency Cleaning: Call reception anytime

=== PARKING ===
Type: Free covered and open parking
Capacity: 10+ vehicles
Vehicle Types: Cars, bikes, scooters welcome
Security: 24/7 CCTV surveillance
EV Charging: Not available

=== LOCATION & DIRECTIONS ===
Full Address: No. 45, Thiru Nagar Main Road, Near Thirumangalam Metro, Chennai - 600032
Nearest Metro: Thirumangalam Metro Station (800 meters, 10 min walk)
From Airport: 7 km, 20-25 minutes by taxi (₹250-350)
From Railway Station: Chennai Central - 6 km, 25 minutes (₹200-300)
From Bus Stand: CMBT Koyambedu - 4 km, 15 minutes (₹150-200)

Google Maps: Search "Chennai BnB Serviced Apartments Thiru Nagar"
Landmarks: Near Anna Nagar, Behind Sathyam Cinemas

=== NEARBY ATTRACTIONS ===
Marina Beach: 8 km (20 min drive) - Longest urban beach in India
Kapaleeshwarar Temple: 6 km (15 min drive) - Historic Shiva temple
Express Avenue Mall: 5 km (12 min drive) - Shopping & entertainment
Valluvar Kottam: 2 km (5 min drive) - Cultural monument
Thousand Lights Mosque: 3 km (8 min drive)
Government Museum: 4 km (10 min drive)
Anna Nagar Tower Park: 3 km (8 min drive)
Phoenix Marketcity: 10 km (25 min drive)

=== TRANSPORTATION ===
Metro Access: Thirumangalam Metro (800m) - Blue Line
Bus Stop: 200 meters from property
Auto/Taxi: Always available outside
Ola/Uber: Reliable service in area
Car Rental: Can be arranged through reception
Airport Pickup: Available at ₹500

=== NEARBY FACILITIES ===
ATM: ICICI Bank ATM (100m), SBI ATM (300m)
Hospitals: Apollo Hospital (2km), MIOT Hospital (3km)
Pharmacy: MedPlus (200m), Apollo Pharmacy (400m)
Supermarket: Reliance Fresh (300m), More Supermarket (500m)
Gym: Gold's Gym (600m)

=== POLICIES ===
Cancellation: Free cancellation up to 24 hours before check-in
No Cancellation Fee: If cancelled 24+ hours in advance
50% Charge: If cancelled within 24 hours
No Refund: No-show or same-day cancellation
Modification: Booking dates can be changed (subject to availability)

Smoking: Strictly prohibited inside rooms (balcony allowed)
Pets: Not allowed
Visitors: Allowed in common areas until 10:00 PM
Parties: Not permitted
Damage: Guest liable for any damage to property

=== PAYMENT OPTIONS ===
Accepted: Cash, UPI, Credit/Debit Cards, Net Banking
UPI IDs: GooglePay, PhonePe, Paytm accepted
Online Booking: Available on website and OTAs
Advance Payment: 20% advance required for booking
Security Deposit: ₹1,000 (refundable at checkout)

=== SERVICES ===
Laundry: ₹50 per kg (24-hour service)
Doctor on Call: Available (charges apply)
Luggage Storage: Free for checked-out guests (same day)
Wake-up Call: Available on request
Newspaper: Complimentary (The Hindu, Times of India)
Travel Desk: Tour packages and cab booking assistance
Airport Drop: ₹500 (advance booking required)

=== EMERGENCY CONTACTS ===
Reception: +91-9876543210
Manager: +91-9876543211
Emergency: +91-9876543212
Police: 100
Ambulance: 108
Fire: 101

=== SPECIAL SERVICES ===
Business Travelers: Work desk in all rooms, printing/scanning at reception
Families: Extra bed available (₹500/night), baby cot available (free)
Long Stay: Special weekly/monthly rates available
Student Discounts: 10% off for students (valid ID required)
Corporate Tie-ups: Available for companies

=== COVID-19 SAFETY ===
Sanitization: Rooms sanitized before each check-in
Contactless Check-in: Available through WhatsApp
Masks: Available at reception
Temperature Checks: Mandatory at entry
Social Distancing: Maintained in common areas

=== LANGUAGES SPOKEN ===
English, Tamil, Hindi, Telugu

=== LOCAL TIPS ===
Best Time to Visit Chennai: November to February (pleasant weather)
Monsoon: June to September (carry umbrella)
Summer: March to May (hot, 35-40°C)
Local Transport: Metro is fastest, autos can be bargained
Must Try Food: Filter coffee, masala dosa, biryani, murukku
Shopping: T Nagar for traditional wear, Pondy Bazaar for street shopping
Beach Timing: Best to visit Marina Beach early morning or evening

=== WORK FROM HOME FACILITIES ===
High-Speed Internet: 100 Mbps WiFi
Work Desk: Available in all rooms
Power Backup: 24/7 generator backup
Printing/Scanning: Available at reception (₹5 per page)
Meeting Space: Common lounge area available
Long Stay Discount: Monthly rates from ₹60,000

=== CHECK-IN PROCESS ===
1. Arrive at reception desk
2. Provide booking confirmation (email/SMS)
3. Show original ID proof (Aadhar/Passport/License)
4. Complete check-in formalities (5 minutes)
5. Pay remaining amount or security deposit
6. Receive room key and welcome kit
7. Staff will escort you to your room

=== FEEDBACK & COMPLAINTS ===
Reception: Immediate assistance 24/7
Email: feedback@chennaibnb.com
WhatsApp: +91-9876543210
Google Reviews: Please leave a review after your stay
Complaints: Resolved within 2 hours

=== BOOKING INFORMATION ===
Website: www.chennaibnb.com
Phone: +91-9876543210
Email: bookings@chennaibnb.com
WhatsApp: +91-9876543210
Walk-in: Subject to availability
Online Platforms: MakeMyTrip, Goibibo, Booking.com, Airbnb

=== FREQUENTLY ASKED QUESTIONS ===

Q: Is breakfast included?
A: Yes, complimentary South Indian breakfast from 7:00 AM to 10:00 AM.

Q: Do you provide lunch and dinner?
A: No, but we have a fully equipped kitchen for self-cooking. Food delivery is also available.

Q: What time does the kitchen close?
A: The kitchen is accessible 24/7 for our guests.

Q: Can I get an extra bed?
A: Yes, extra bed available at ₹500 per night. Baby cot is free.

Q: Is parking free?
A: Yes, free covered and open parking available.

Q: How far is the nearest metro?
A: Thirumangalam Metro Station is 800 meters (10-minute walk).

Q: Do you allow pets?
A: Sorry, pets are not allowed.

Q: Is there a gym?
A: No in-house gym, but Gold's Gym is 600 meters away.

Q: Can I extend my stay?
A: Yes, subject to availability. Contact reception.

Q: What if I lose my room key?
A: Contact reception immediately. Replacement key: ₹200 charge.

=== SUSTAINABILITY INITIATIVES ===
✓ Solar water heaters
✓ LED lighting throughout
✓ Waste segregation
✓ Water conservation practices
✓ Eco-friendly cleaning products
✓ Paperless billing available

=== RECOGNITION & RATINGS ===
Google Rating: 4.5/5 stars
TripAdvisor: Certificate of Excellence 2024
Guest Satisfaction: 95%+ positive reviews
Booking.com: 8.8/10 rating

---
Last Updated: October 2025
For latest information, contact reception or visit www.chennaibnb.com
"""


def call_perplexity(prompt, system_prompt="", max_tokens=1000):
    """
    Sends a request to the Perplexity API for text generation.
    It includes the current conversation history (SESSION_MEMORY).
    (This function replaces the original call_ollama function.)
    """
    global SESSION_MEMORY
    
    if PERPLEXITY_CLIENT is None or PERPLEXITY_API_KEY is None:
       
        return "ERROR: Perplexity API Key is not configured. Please set the 'PERPLEXITY_API_KEY' environment variable."

    try:
        
        messages = [{"role": "system", "content": system_prompt}]
        
     
        conversation_history = SESSION_MEMORY[:]
        messages.extend(conversation_history)
        
       
        messages.append({"role": "user", "content": prompt})

        
        response = PERPLEXITY_CLIENT.chat.completions.create(
            model=PERPLEXITY_MODEL,
            messages=messages,
            temperature=0.0,
            max_tokens=max_tokens,
            stream=False,
            
            timeout=60 
        )

        bot_response = response.choices[0].message.content.strip()

        
        SESSION_MEMORY.append({"role": "user", "content": prompt})
        SESSION_MEMORY.append({"role": "assistant", "content": bot_response})
        
        
        if len(SESSION_MEMORY) > 10: 
            SESSION_MEMORY[:] = SESSION_MEMORY[-10:] 
            
        return bot_response

    except Exception as e:
        
        print(f"Perplexity API Error: {e}")
        
        return "I'm sorry, I'm experiencing a temporary issue with my service. Please try your request again."




def llm_classify_intent(user_message):
    """
    Uses the LLM to classify the user's intent into one of five categories.
    """
    system_prompt = f"""
    You are an expert AI intent classifier for a hotel assistant. 
    Analyze the user's request and classify it into **ONE** of the following categories:
    1. 'check_in': The user is asking to check in or about the check-in process.
    2. 'housekeeping': The user is requesting a service, maintenance, or item delivery (e.g., extra towels, fixing the AC, ordering laundry).
    3. 'faq': The user is asking a general information question about the hotel's amenities, policies, dining, or location.
    4. 'pms_query': The user is asking for specific live data from the Property Management System (PMS), such as 'show me all customers', 'what rooms are available', or 'list my current bookings'.
    5. 'other': Greetings, thanks, complaints, or any message that doesn't fit the above four.

    Respond with ONLY the category name. DO NOT add any other text, explanation, or punctuation.
    """
    
   
    intent = call_perplexity(user_message, system_prompt, max_tokens=10)
    
    
    
    valid_intents = ['check_in', 'housekeeping', 'faq', 'pms_query', 'other']
    intent = intent.lower().strip().replace('.', '').replace(',', '')
    
    return intent if intent in valid_intents else 'other'



def pms_api_call(resource_name):
    """
    Makes an authenticated GET request to the QloApps/PrestaShop Webservice API.
    
    Args:
        resource_name (str): The resource to query (e.g., 'customers', 'rooms', 'bookings').
        
    Returns:
        str: The raw XML response text or an error message.
    """
    if QW_API_KEY == "YOUR_32_CHAR_API_KEY_HERE_12345":
        return "ERROR: QloApps API Key is not configured. Please set the 'QLOAPPS_API_KEY' variable."

    api_endpoint = f"{QLOAPPS_API_URL}/{resource_name}"
    
   
    auth_tuple = (QW_API_KEY, '')
    
    try:
        response = requests.get(
            api_endpoint, 
            auth=auth_tuple, 
            headers={"Accept": "application/xml"}, 
            timeout=5
        )
        response.raise_for_status() 
        
        
        return response.text
        
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            return f"API ERROR (401 Unauthorized): Check the **API Key** and ensure it has **GET** permissions for the '{resource_name}' resource in your QloApps back office."
        elif response.status_code == 404:
            return f"API ERROR (404 Not Found): The resource '{resource_name}' does not exist at {api_endpoint}."
        else:
            return f"API ERROR ({response.status_code}): Could not retrieve data from the PMS. Details: {e}"
            
    except requests.exceptions.RequestException as e:
        return f"CONNECTION ERROR: Could not connect to the local QloApps API at {api_endpoint}. Is your web server running? Details: {e}"



def summarize_request(user_message):
    """
    Uses the LLM to summarize the service request for the staff.
    """
    system_prompt = "You are an AI assistant. Summarize the user's service request into a short, actionable, single-sentence note for a hotel staff member. The summary should be a maximum of 15 words."
    
  
    summary = call_perplexity(user_message, system_prompt, max_tokens=30)
    
    return summary

def send_housekeeping_notification(request_text, summary, guest_name, room_number):
    """
    Simulates sending an immediate notification (email) to the hotel staff.
    NOTE: This requires proper setup of HOTEL_EMAIL and HOTEL_PASS environment variables
    and enabling "Less Secure App Access" or an App Password in Gmail/other providers.
    """
    if HOTEL_EMAIL == "your_hotel_staff_email@example.com":
        print("EMAIL NOTIFICATION SKIPPED: Default email credentials found.")
        return "Email simulated: success" 

    msg = MIMEMultipart()
    msg['From'] = HOTEL_EMAIL
    msg['To'] = HOTEL_STAFF_RECEIVER
    msg['Subject'] = f"🛎️ NEW SERVICE REQUEST: Room {room_number} - {summary}"

    body = f"""
    New Service Request via AI Assistant:

    **Guest:** {guest_name}
    **Room:** {room_number}
    **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    
    **Staff Note (Summary):** {summary}
    
    **Original Guest Message:**
    {request_text}

    Please prioritize this request immediately.
    """
    msg.attach(MIMEText(body, 'plain'))

    try:
       
        server = smtplib.SMTP('smtp.office365.com', 587)
        server.starttls()
        server.login(HOTEL_EMAIL, HOTEL_PASS)
        text = msg.as_string()
        server.sendmail(HOTEL_EMAIL, HOTEL_STAFF_RECEIVER, text)
        server.quit()
        return "Email sent: success"
    except Exception as e:
        print(f"Email sending failed: {e}")
        return "Email failed: error"

def llm_answer_faq(user_message, hotel_info):
    """
    Uses the LLM to answer the user's question based ONLY on the provided hotel info text.
    """
   
    context_prompt = f"""
    You are Nexrova, a friendly and professional AI Hotel Assistant for **Chennai BnB Serviced Apartments**.
    Your current room/guest information is stored in the chat session.
    
    Your task is to answer the user's question ONLY using the detailed hotel information provided below.
    
    If the answer is found, provide a concise and helpful response.
    If the information is not present in the text, you MUST politely state that you cannot find the specific information and suggest they contact the reception at +91-9876543210.
    
    --- HOTEL KNOWLEDGE BASE ---
    {hotel_info}
    
    --- USER QUESTION ---
    {user_message}
    """
    
   
    response = call_perplexity(context_prompt, system_prompt="", max_tokens=500)
   
    
   
    if "i'm sorry" in response.lower() and "reception" not in response.lower():
        return "I'm sorry, I don't have that specific information in my knowledge base. For immediate assistance, please call the reception at **+91-9876543210**."
        
    return response



app = Flask(__name__)

app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'a_strong_default_secret_key_12345')

app.template_folder = template_dir


GUEST_DB = {
    "9876543210": {"name": "Alan", "room": "101", "checked_in": False},
    "9900990099": {"name": "Bob", "room": "205", "checked_in": True},
    "1122334455": {"name": "Charlie", "room": "310", "checked_in": False}
}


def reset_session_memory():
    global SESSION_MEMORY
    SESSION_MEMORY.clear()



@app.route('/')
def login_page():
    """Renders the login.html page."""
    if session.get('is_logged_in'):
        return redirect(url_for('chat_page'))
    
    login_path = os.path.join(index_html_path, 'login.html')
    with open(login_path, 'r') as f:
        return f.read()

@app.route('/chat')
def chat_page():
    """Renders the index.html chat page, requires login."""
    if not session.get('is_logged_in'):
        return redirect(url_for('login_page'))
        
    index_path = os.path.join(index_html_path, 'index.html')
    with open(index_path, 'r') as f:
        return f.read()

@app.route('/verify_phone', methods=['POST'])
def verify_phone():
    """API endpoint to verify the phone number and start a session."""
    data = request.json
    phone_number = data.get('phone_number')
    
    guest = GUEST_DB.get(phone_number)
    
    if guest:
       
        session['is_logged_in'] = True
        session['phone_number'] = phone_number
        session['guest_name'] = guest['name']
        session['room_number'] = guest['room']
        session['checked_in'] = guest['checked_in']
        reset_session_memory() 
        
        return jsonify({"success": True, "redirect": url_for('chat_page')})
    else:
       
        return jsonify({"success": False, "message": "Mobile number not found in active bookings. Please contact the front desk."})

@app.route('/logout', methods=['POST'])
def logout():
    """API endpoint to clear the session and redirect to login."""
    session.clear()
    reset_session_memory()
    return jsonify({"success": True, "redirect": url_for('login_page')})


@app.route('/llm_status')
def llm_status():
    """
    Checks the status of the Perplexity API connection. 
    (Replaces the original ollama_status check with an API key check.)
    """
    if PERPLEXITY_API_KEY:
        try:
            
            
            probe_client = OpenAI(api_key=PERPLEXITY_API_KEY, base_url=PERPLEXITY_BASE_URL)
            probe_client.chat.completions.create(
                model="sonar-small-chat", 
                messages=[{"role": "user", "content": "ping"}], 
                timeout=5
            )
            return jsonify({"llm": "ready", "model": PERPLEXITY_MODEL, "provider": "Perplexity"})
        except Exception as e:
            
            return jsonify({"llm": "error", "error": str(e), "provider": "Perplexity"})
    
    return jsonify({"llm": "offline", "error": "Perplexity API Key is missing.", "provider": "Perplexity"})

@app.route('/chat/message', methods=['POST'])
def handle_chat_message():
    """Main API endpoint for processing guest messages."""
    
    if not session.get('is_logged_in'):
        return jsonify({"response": "Your session has expired. Please log in again.",
                         "action": {"type": "redirect", "url": url_for('login_page')}}), 401

    user_message = request.json.get('message', '').strip()
    if not user_message:
        return jsonify({"response": "Please type a message."})

    guest_name = session.get('guest_name', 'Guest')
    room_number = session.get('room_number', 'Unknown')
    is_checked_in = session.get('checked_in', False)
    
   
    if not PERPLEXITY_API_KEY:
        return jsonify({"response": "I'm sorry, my AI services are currently offline due to a missing API Key. Please contact the front desk directly for assistance.",
                         "action": None})
   
    intent = llm_classify_intent(user_message)
    print(f"[{guest_name} - {room_number}] Classified Intent: {intent}")

    response_text = "Processing your request..."

    if intent == 'check_in':
        if is_checked_in:
            response_text = f"Welcome back, {guest_name}! It looks like you're already checked in to Room **{room_number}**. How else can I assist you with your stay?"
        else:
           
            session['checked_in'] = True 
            response_text = f"Thank you, {guest_name}! I have verified your booking. Your room is **{room_number}**. I am now sending your **digital key** to your registered email and mobile number. Your check-in is complete! Enjoy your stay."

    elif intent == 'housekeeping':
       
        summary = summarize_request(user_message)

       
        send_housekeeping_notification(
            request_text=user_message,
            summary=summary,
            guest_name=guest_name,
            room_number=room_number
        )

        response_text = f"Thank you, **{guest_name}**. Your request has been logged and instantly notified to our Housekeeping team. The summary is: **{summary}**. A staff member will attend to this in Room **{room_number}** shortly."
    
    elif intent == 'pms_query': 
        resource_to_fetch = 'customers' 
        pms_data = pms_api_call(resource_to_fetch)
        
        
        pms_prompt = f"""
        The user asked for information related to the Property Management System (PMS) with the message: "{user_message}".
        
        I have received the following raw XML data from the QloApps/PrestaShop API for the '{resource_to_fetch}' resource:
        --- XML DATA ---
        {pms_data}
        ---
        
        Your task is to:
        1. Review the XML data.
        2. If it is an **ERROR** message, simply state the error clearly to the user and suggest an action.
        3. If the XML is a **list of resources** (like customers), politely inform the user that you are displaying the raw data you received and provide the full XML response in a code block.
        
        Focus on clarity and security. Do not expose the API key.
        """
       
        response_text = call_perplexity(pms_prompt, system_prompt="", max_tokens=1000)
        


    elif intent == 'faq' or intent == 'other':
        
        response_text = llm_answer_faq(user_message, HOTEL_INFO)
        
    return jsonify({"response": response_text, "action": None})



if __name__ == '__main__':
    print("\n--- Starting Nexrova Hotel Assistant ---")
    
   
    print(f"LLM Provider: Perplexity AI")
    print(f"LLM Model: {PERPLEXITY_MODEL}")
    print(f"Perplexity API Key: {'Configured' if PERPLEXITY_API_KEY else 'MISSING (Must set PERPLEXITY_API_KEY!)'}")
    
    
    print(f"QloApps API Key: {'Configured' if QW_API_KEY != 'YOUR_32_CHAR_API_KEY_HERE_12345' else 'DEFAULT/UNCONFIGURED (MUST CHANGE!)'}")
    
    print("\nIMPORTANT: Ensure you have set the PERPLEXITY_API_KEY environment variable.")
    print("\nAccess the App at: **http://127.0.0.1:5000/**")
    
   
    app.run(debug=True)