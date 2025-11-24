import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from config import (
    QLOAPPS_API_KEY,
    QLOAPPS_BASE_URL,
)



def qlo_get(resource, params=None):
    if params is None:
        params = {}

    params["ws_key"] = QLOAPPS_API_KEY
    url = f"{QLOAPPS_BASE_URL}/{resource}"

    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        return ET.fromstring(r.text)
    except Exception as e:
        print(f"[QLO_GET ERROR] {e}")
        return None




def qlo_post(resource, xml_body):
    url = f"{QLOAPPS_BASE_URL}/{resource}?ws_key={QLOAPPS_API_KEY}&schema=blank"

    headers = {"Content-Type": "application/xml"}

    try:
        r = requests.post(url, data=xml_body, headers=headers, timeout=30)
        r.raise_for_status()
        root = ET.fromstring(r.text)
        return root
    except Exception as e:
        print(f"[QLO_POST ERROR] {e}")
        return None



def build_customer_xml(firstname, lastname, email, phone):
    customer = ET.Element("prestashop")
    cust = ET.SubElement(customer, "customer")

    ET.SubElement(cust, "id_default_group").text = "3"
    ET.SubElement(cust, "firstname").text = firstname
    ET.SubElement(cust, "lastname").text = lastname
    ET.SubElement(cust, "email").text = email
    ET.SubElement(cust, "active").text = "1"
    ET.SubElement(cust, "phone").text = phone or ""

    return ET.tostring(customer, encoding="utf-8")



def internal_create_customer(firstname, lastname, email, phone):
    xml_body = build_customer_xml(firstname, lastname, email, phone)
    resp = qlo_post("customers", xml_body)

    if resp is None:
        return None

    try:
        cid = resp.find(".//id").text
        return cid
    except:
        return None



def build_booking_xml(customer_id, room_type_id, check_in, check_out):
    root = ET.Element("prestashop")
    booking = ET.SubElement(root, "booking")

    ET.SubElement(booking, "id_customer").text = str(customer_id)
    ET.SubElement(booking, "id_room_type").text = str(room_type_id)
    ET.SubElement(booking, "date_from").text = check_in
    ET.SubElement(booking, "date_to").text = check_out
    ET.SubElement(booking, "status").text = "1"  # confirmed

    return ET.tostring(root, encoding="utf-8")




def create_booking(customer_id, room_type_id, check_in, check_out):
    xml_body = build_booking_xml(customer_id, room_type_id, check_in, check_out)
    resp = qlo_post("bookings", xml_body)

    if resp is None:
        return None

    try:
        bid = resp.find(".//id").text
        return bid
    except:
        return None




def get_room_types():
    root = qlo_get("room_types")

    room_types = []
    if root is None:
        return room_types

    for r in root.findall(".//room_type"):
        room = {
            "id": r.find("id").text,
            "name": r.find("name").text,
            "base_price": float(r.find("price").text or 0)
        }
        room_types.append(room)

    return room_types




def pms_check_availability_pricing(check_in, check_out, guests):
    """
    Basic availability engine.
    You can customize pricing rules here.
    """

    try:
        dt_in = datetime.strptime(check_in, "%Y-%m-%d")
        dt_out = datetime.strptime(check_out, "%Y-%m-%d")
        nights = (dt_out - dt_in).days
    except Exception:
        return []

    room_types = get_room_types()
    available = []

    if not room_types:
        return []

    for room in room_types:
        base_price = room["base_price"]
        total_price = base_price * nights

       
        if guests > 2:
            total_price *= 1.20

        if nights >= 5:
            total_price *= 0.85

        available.append({
            "id": room["id"],
            "name": room["name"],
            "base_price": base_price,
            "nights": nights,
            "total_price": round(total_price, 2)
        })

    return available



def create_housekeeping_ticket(guest_name, room, text, priority="normal"):
    ticket = {
        "guest_name": guest_name,
        "room": room,
        "description": text,
        "priority": priority,
        "created_at": datetime.utcnow().isoformat()
    }
    print("[HOUSEKEEPING TICKET CREATED]", ticket)
    return ticket
