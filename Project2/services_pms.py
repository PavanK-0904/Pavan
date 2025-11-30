
import pymysql
from datetime import datetime
from config import (
    MYSQL_HOST,
    MYSQL_PORT,
    MYSQL_USER,
    MYSQL_PASSWORD,
    MYSQL_DATABASE,
)


def get_db_connection():
    """Create and return a MySQL database connection"""
    try:
        connection = pymysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Exception as e:
        print(f"[DB CONNECTION ERROR] {e}")
        return None


def execute_query(query, params=None):
    """Execute a SELECT query and return results"""
    connection = get_db_connection()
    if not connection:
        return None
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params or ())
            results = cursor.fetchall()
        return results
    except Exception as e:
        print(f"[DB QUERY ERROR] {e}")
        return None
    finally:
        connection.close()


def execute_insert(query, params=None):
    """Execute an INSERT query and return the last inserted ID"""
    connection = get_db_connection()
    if not connection:
        return None
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params or ())
            connection.commit()
            return cursor.lastrowid
    except Exception as e:
        print(f"[DB INSERT ERROR] {e}")
        connection.rollback()
        return None
    finally:
        connection.close()


def get_room_types():
    """
    Fetch all room types from Minical database.
    Returns list of room types with id, name, and base price information.
    """
    try:
        
        query = """
            SELECT 
                rt.id,
                rt.name,
                rt.max_occupancy,
                rt.max_adults,
                rt.max_children,
                rt.description,
                COUNT(r.room_id) as available_units
            FROM room_type rt
            LEFT JOIN room r ON rt.id = r.room_type_id 
                AND r.is_deleted = 0
                AND r.can_be_sold_online = 1
            WHERE (rt.is_deleted IS NULL OR rt.is_deleted = 0)
                AND rt.can_be_sold_online = 1
            GROUP BY rt.id
            HAVING available_units > 0
        """
        
        results = execute_query(query)
        
        if not results:
            print("[ROOM TYPES] No room types found in database")
            return []
        
        room_types = []
        for row in results:
           
            room_type = {
                "id": row["id"],
                "name": row["name"],
                "base_price": 100.00,  
                "max_occupancy": row["max_occupancy"] or 2,
                "max_adults": row["max_adults"] or 2,
                "max_children": row["max_children"] or 0,
                "description": row["description"] or "",
                "available_units": row["available_units"]
            }
            room_types.append(room_type)
        
        print(f"[ROOM TYPES] Found {len(room_types)} room types")
        return room_types
        
    except Exception as e:
        print(f"[ERROR] Failed to fetch room types: {e}")
        return []


def internal_create_customer(firstname, lastname, email, phone):
    """
    Create a customer in Minical database.
    Returns customer_id on success, None on failure.
    """
    try:
        
        check_query = "SELECT customer_id FROM customer WHERE email = %s LIMIT 1"
        existing = execute_query(check_query, (email,))
        
        if existing and len(existing) > 0:
            customer_id = existing[0]["customer_id"]
            print(f"[CUSTOMER] Found existing customer: {customer_id}")
            return customer_id
        
    
        full_name = f"{firstname} {lastname}".strip()
        insert_query = """
            INSERT INTO customer (
                customer_name, 
                email, 
                phone, 
                company_id,
                is_deleted
            ) VALUES (%s, %s, %s, %s, %s)
        """
        
        customer_id = execute_insert(
            insert_query, 
            (full_name, email, phone or "", 1, 0)
        )
        
        if customer_id:
            print(f"[CUSTOMER] Created new customer: {customer_id}")
            return customer_id
        else:
            print("[CUSTOMER] Failed to create customer")
            return None
            
    except Exception as e:
        print(f"[ERROR] Failed to create customer: {e}")
        return None


def create_booking(customer_id, room_type_id, check_in, check_out):
    """
    Create a booking in Minical database.
    Returns booking_id on success, None on failure.
    """
    try:
        
        room_query = """
            SELECT room_id FROM room 
            WHERE room_type_id = %s 
                AND is_deleted = 0
                AND can_be_sold_online = 1
            LIMIT 1
        """
        
        available_rooms = execute_query(room_query, (room_type_id,))
        
        if not available_rooms or len(available_rooms) == 0:
            print(f"[BOOKING] No available rooms for type {room_type_id}")
            return None
        
        room_id = available_rooms[0]["room_id"]
        
       
        insert_query = """
            INSERT INTO booking (
                booking_customer_id,
                company_id,
                is_deleted
            ) VALUES (%s, %s, %s)
        """
        
        booking_id = execute_insert(
            insert_query,
            (customer_id, 1, 0)
        )
        
        if booking_id:
            print(f"[BOOKING] Created booking: {booking_id}")
            
            return booking_id
        else:
            print("[BOOKING] Failed to create booking")
            return None
            
    except Exception as e:
        print(f"[ERROR] Failed to create booking: {e}")
        return None


def pms_check_availability_pricing(check_in, check_out, guests):
    """
    Check room availability and calculate pricing.
    Returns list of available rooms with pricing.
    """
    try:
        
        dt_in = datetime.strptime(check_in, "%Y-%m-%d")
        dt_out = datetime.strptime(check_out, "%Y-%m-%d")
        nights = (dt_out - dt_in).days
        
        if nights <= 0:
            print("[AVAILABILITY] Invalid date range")
            return []
        
        
        room_types = get_room_types()
        
        if not room_types:
            print("[AVAILABILITY] No room types available")
            return []
        
        available = []
        
        for room in room_types:

            if guests > room["max_occupancy"]:
                continue
            
           
            
        
            base_price = room["base_price"]
            total_price = base_price * nights
            
           
            if guests > room["max_adults"]:
                
                extra_guests = guests - room["max_adults"]
                total_price += (extra_guests * 20 * nights)  
            
            if nights >= 7:
                total_price *= 0.85  
            elif nights >= 5:
                total_price *= 0.90  
            
            available.append({
                "id": room["id"],
                "name": room["name"],
                "description": room["description"],
                "max_occupancy": room["max_occupancy"],
                "base_price": base_price,
                "nights": nights,
                "total_price": round(total_price, 2)
            })
        
        print(f"[AVAILABILITY] Found {len(available)} available room types")
        return available
        
    except Exception as e:
        print(f"[ERROR] Failed to check availability: {e}")
        return []


def create_housekeeping_ticket(guest_name, room, text, priority="normal"):
    """Create a housekeeping ticket (mock implementation)"""
    ticket = {
        "guest_name": guest_name,
        "room": room,
        "description": text,
        "priority": priority,
        "created_at": datetime.utcnow().isoformat()
    }
    print("[HOUSEKEEPING TICKET CREATED]", ticket)
    return ticket

