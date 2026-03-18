from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI()

# -------------------- DATA --------------------

rooms = [
    {"id": 1, "room_number": "101", "type": "Single", "price_per_night": 1000, "floor": 1, "is_available": True},
    {"id": 2, "room_number": "102", "type": "Double", "price_per_night": 2000, "floor": 1, "is_available": True},
    {"id": 3, "room_number": "201", "type": "Suite", "price_per_night": 4000, "floor": 2, "is_available": True},
    {"id": 4, "room_number": "202", "type": "Deluxe", "price_per_night": 3500, "floor": 2, "is_available": True},
    {"id": 5, "room_number": "301", "type": "Single", "price_per_night": 1200, "floor": 3, "is_available": True},
    {"id": 6, "room_number": "302", "type": "Double", "price_per_night": 2200, "floor": 3, "is_available": True},
]

bookings = []
booking_counter = 1

# -------------------- MODELS --------------------

class BookingRequest(BaseModel):
    guest_name: str = Field(..., min_length=2)
    room_id: int = Field(..., gt=0)
    nights: int = Field(..., gt=0, le=30)
    phone: str = Field(..., min_length=10)
    meal_plan: str = "none"
    early_checkout: bool = False


class NewRoom(BaseModel):
    room_number: str = Field(..., min_length=1)
    type: str = Field(..., min_length=2)
    price_per_night: int = Field(..., gt=0)
    floor: int = Field(..., gt=0)
    is_available: bool = True


# -------------------- HELPERS --------------------

def find_room(room_id):
    for room in rooms:
        if room["id"] == room_id:
            return room
    return None


def calculate_stay_cost(price, nights, meal_plan, early_checkout):
    meal_cost = 0
    if meal_plan == "breakfast":
        meal_cost = 500
    elif meal_plan == "all-inclusive":
        meal_cost = 1200

    total = (price + meal_cost) * nights

    discount = 0
    if early_checkout:
        discount = total * 0.1
        total -= discount

    return total, discount


def filter_rooms_logic(type, max_price, floor, is_available):
    filtered = rooms

    if type is not None:
        filtered = [r for r in filtered if r["type"].lower() == type.lower()]
    if max_price is not None:
        filtered = [r for r in filtered if r["price_per_night"] <= max_price]
    if floor is not None:
        filtered = [r for r in filtered if r["floor"] == floor]
    if is_available is not None:
        filtered = [r for r in filtered if r["is_available"] == is_available]

    return filtered


# -------------------- DAY 1 --------------------

@app.get("/")
def home():
    return {"message": "Welcome to Grand Stay Hotel"}


@app.get("/rooms")
def get_rooms():
    return {
        "rooms": rooms,
        "total": len(rooms),
        "available_count": len([r for r in rooms if r["is_available"]])
    }


@app.get("/rooms/summary")
def rooms_summary():
    prices = [r["price_per_night"] for r in rooms]
    types = {}
    for r in rooms:
        types[r["type"]] = types.get(r["type"], 0) + 1

    return {
        "total": len(rooms),
        "available": len([r for r in rooms if r["is_available"]]),
        "occupied": len([r for r in rooms if not r["is_available"]]),
        "cheapest": min(prices),
        "expensive": max(prices),
        "by_type": types
    }


# -------------------- FILTER + SEARCH + SORT + PAGE + BROWSE (BEFORE {id}) --------------------

@app.get("/rooms/filter")
def filter_rooms(
    type: Optional[str] = None,
    max_price: Optional[int] = None,
    floor: Optional[int] = None,
    is_available: Optional[bool] = None
):
    result = filter_rooms_logic(type, max_price, floor, is_available)
    return {"rooms": result, "count": len(result)}


@app.get("/rooms/search")
def search_rooms(keyword: str):
    result = [
        r for r in rooms
        if keyword.lower() in r["room_number"].lower()
        or keyword.lower() in r["type"].lower()
    ]

    if not result:
        return {"message": "No rooms found"}

    return {"results": result, "total_found": len(result)}


@app.get("/rooms/sort")
def sort_rooms(sort_by: str = "price_per_night", order: str = "asc"):
    if sort_by not in ["price_per_night", "floor", "type"]:
        raise HTTPException(status_code=400, detail="Invalid sort_by")

    if order not in ["asc", "desc"]:
        raise HTTPException(status_code=400, detail="Invalid order")

    return sorted(rooms, key=lambda x: x[sort_by], reverse=(order == "desc"))


@app.get("/rooms/page")
def paginate_rooms(page: int = 1, limit: int = 2):
    start = (page - 1) * limit
    end = start + limit

    total = len(rooms)
    total_pages = (total + limit - 1) // limit

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": total_pages,
        "rooms": rooms[start:end]
    }


@app.get("/rooms/browse")
def browse_rooms(
    keyword: Optional[str] = None,
    sort_by: str = "price_per_night",
    order: str = "asc",
    page: int = 1,
    limit: int = 3
):
    result = rooms

    if keyword:
        result = [
            r for r in result
            if keyword.lower() in r["room_number"].lower()
            or keyword.lower() in r["type"].lower()
        ]

    result = sorted(result, key=lambda x: x[sort_by], reverse=(order == "desc"))

    start = (page - 1) * limit
    end = start + limit
    total = len(result)
    total_pages = (total + limit - 1) // limit

    return {
        "total": total,
        "total_pages": total_pages,
        "page": page,
        "results": result[start:end]
    }


# -------------------- {room_id} LAST --------------------

@app.get("/rooms/{room_id}")
def get_room(room_id: int):
    room = find_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


# -------------------- BOOKINGS --------------------

@app.get("/bookings")
def get_bookings():
    return {"bookings": bookings, "total": len(bookings)}


@app.post("/bookings")
def create_booking(request: BookingRequest):
    global booking_counter

    room = find_room(request.room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if not room["is_available"]:
        raise HTTPException(status_code=400, detail="Room not available")

    total, discount = calculate_stay_cost(
        room["price_per_night"],
        request.nights,
        request.meal_plan,
        request.early_checkout
    )

    booking = {
        "booking_id": booking_counter,
        "guest_name": request.guest_name,
        "room_id": request.room_id,
        "nights": request.nights,
        "meal_plan": request.meal_plan,
        "total_cost": total,
        "discount": discount,
        "status": "confirmed"
    }

    room["is_available"] = False
    bookings.append(booking)
    booking_counter += 1

    return booking


@app.get("/bookings/active")
def active_bookings():
    return {
        "active_bookings": [
            b for b in bookings if b["status"] in ["confirmed", "checked_in"]
        ]
    }


@app.post("/checkin/{booking_id}")
def checkin(booking_id: int):
    for b in bookings:
        if b["booking_id"] == booking_id:
            b["status"] = "checked_in"
            return b
    raise HTTPException(status_code=404, detail="Booking not found")


@app.post("/checkout/{booking_id}")
def checkout(booking_id: int):
    for b in bookings:
        if b["booking_id"] == booking_id:
            b["status"] = "checked_out"
            room = find_room(b["room_id"])
            if room:
                room["is_available"] = True
            return b
    raise HTTPException(status_code=404, detail="Booking not found")


@app.get("/bookings/search")
def search_bookings(keyword: str):
    return {
        "results": [
            b for b in bookings if keyword.lower() in b["guest_name"].lower()
        ]
    }


@app.get("/bookings/sort")
def sort_bookings(sort_by: str = "total_cost"):
    if sort_by not in ["total_cost", "nights"]:
        raise HTTPException(status_code=400, detail="Invalid sort field")

    return sorted(bookings, key=lambda x: x[sort_by])


# -------------------- ROOM CRUD --------------------

@app.post("/rooms", status_code=201)
def add_room(room: NewRoom):
    for r in rooms:
        if r["room_number"] == room.room_number:
            raise HTTPException(status_code=400, detail="Duplicate room number")

    new_room = {"id": len(rooms) + 1, **room.dict()}
    rooms.append(new_room)
    return new_room


@app.put("/rooms/{room_id}")
def update_room(
    room_id: int,
    price_per_night: Optional[int] = None,
    is_available: Optional[bool] = None
):
    room = find_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if price_per_night is not None:
        room["price_per_night"] = price_per_night
    if is_available is not None:
        room["is_available"] = is_available

    return room


@app.delete("/rooms/{room_id}")
def delete_room(room_id: int):
    room = find_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if not room["is_available"]:
        raise HTTPException(status_code=400, detail="Room is occupied")

    rooms.remove(room)
    return {"message": "Room deleted"}