from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# -----------------------------
# Product Database (Mock)
# -----------------------------
products = [
    {"id": 1, "name": "Wireless Mouse", "price": 499, "in_stock": True},
    {"id": 2, "name": "Notebook", "price": 99, "in_stock": True},
    {"id": 3, "name": "USB Hub", "price": 299, "in_stock": False},
    {"id": 4, "name": "Pen Set", "price": 49, "in_stock": True}
]

# -----------------------------
# Cart & Orders Storage
# -----------------------------
cart = []
orders = []
order_counter = 1


# -----------------------------
# Checkout Request Model
# -----------------------------
class CheckoutRequest(BaseModel):
    customer_name: str
    delivery_address: str


# -----------------------------
# Helper Functions
# -----------------------------
def get_product(product_id: int):
    for product in products:
        if product["id"] == product_id:
            return product
    return None


def calculate_subtotal(product, quantity):
    return product["price"] * quantity


# -----------------------------
# Add Item to Cart
# -----------------------------
@app.post("/cart/add")
def add_to_cart(product_id: int, quantity: int = 1):

    product = get_product(product_id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if not product["in_stock"]:
        raise HTTPException(
            status_code=400,
            detail=f"{product['name']} is out of stock"
        )

    # Check if product already exists in cart
    for item in cart:
        if item["product_id"] == product_id:
            item["quantity"] += quantity
            item["subtotal"] = calculate_subtotal(product, item["quantity"])
            return {
                "message": "Cart updated",
                "cart_item": item
            }

    subtotal = calculate_subtotal(product, quantity)

    cart_item = {
        "product_id": product["id"],
        "product_name": product["name"],
        "quantity": quantity,
        "unit_price": product["price"],
        "subtotal": subtotal
    }

    cart.append(cart_item)

    return {
        "message": "Added to cart",
        "cart_item": cart_item
    }


# -----------------------------
# View Cart
# -----------------------------
@app.get("/cart")
def view_cart():

    if not cart:
        return {"message": "Cart is empty"}

    grand_total = sum(item["subtotal"] for item in cart)

    return {
        "items": cart,
        "item_count": len(cart),
        "grand_total": grand_total
    }


# -----------------------------
# Remove Item from Cart
# -----------------------------
@app.delete("/cart/{product_id}")
def remove_from_cart(product_id: int):

    for item in cart:
        if item["product_id"] == product_id:
            cart.remove(item)
            return {"message": "Item removed from cart"}

    raise HTTPException(status_code=404, detail="Item not in cart")


# -----------------------------
# Checkout
# -----------------------------
@app.post("/cart/checkout")
def checkout(order: CheckoutRequest):

    global order_counter

    if not cart:
        raise HTTPException(
            status_code=400,
            detail="Cart is empty — add items first"
        )

    placed_orders = []
    grand_total = 0

    for item in cart:

        order_data = {
            "order_id": order_counter,
            "customer_name": order.customer_name,
            "delivery_address": order.delivery_address,
            "product": item["product_name"],
            "quantity": item["quantity"],
            "total_price": item["subtotal"]
        }

        orders.append(order_data)
        placed_orders.append(order_data)

        grand_total += item["subtotal"]
        order_counter += 1

    cart.clear()

    return {
        "message": "Checkout successful",
        "orders_placed": placed_orders,
        "grand_total": grand_total
    }


# -----------------------------
# View Orders
# -----------------------------
@app.get("/orders")
def get_orders():

    return {
        "orders": orders,
        "total_orders": len(orders)
    }