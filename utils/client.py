from tgtg import TgtgClient
import os
import argparse
import dotenv
dotenv.load_dotenv()

client = TgtgClient(
    access_token=os.getenv("ACCESS_TOKEN"),
    refresh_token=os.getenv("REFRESH_TOKEN"),
    cookie=os.getenv("COOKIE")
)

# items = client.get_items(
#     favorites_only=True,
#     latitude=51.45156929283408,
#     longitude=-0.9728701578499089,
#     radius=10,
# )
items = client.get_favorites()

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import re
import time

def summarize_magic_bag(payload: dict) -> dict:
    item = payload["item"]
    store = payload["store"]
    pickup = payload.get("pickup_interval", {})
    address = store["store_location"]["address"]["address_line"]

    # 1) Restaurant name
    id = item["item_id"]
    restaurant_name = store["store_name"]
    branch = store.get("branch")
    if branch and branch.lower() not in restaurant_name.lower():
        restaurant_name = f"{restaurant_name} — {branch}"

    # 2) Address
    full_address = address

    # 3) What food (from description; naive parse)
    desc = (item.get("description") or "").strip()
   
    # Try to pull items after phrases like "You could receive items such as ..." etc.
    foods = []
    m = re.search(r"(?:such as|e\.g\.,?|like|include)\s+(.*)", desc, re.IGNORECASE)
    # print("match:", m)
    if m:
        # print("matched:", m.group(1))
        if m.group(1).strip().endswith(":"):
            # remove trailing period
            m = re.search(r"either:\s*(.*)", desc, re.IGNORECASE | re.DOTALL)
            candidates = m.group(1).strip() if m else desc
        else:
            candidates = m.group(1)
    else:
        # fallback: use the whole description
        candidates = desc
    # split by commas and "or"
    parts = re.split(r",|\bor\b|/|、", candidates)
    for p in parts:
        p = p.strip(" .!?:;").lower()
        if not p:
            continue
        # basic cleanups
        p = re.sub(r"^and\s+", "", p)
        # avoid trailing commentary
        p = re.sub(r"^(please note.*)$", "", p)
        if p and len(p) <= 60:
            foods.append(p)
    # de-dup while keeping order
    seen = set()
    foods = [f for f in foods if not (f in seen or seen.add(f))]
    if not foods and desc:
        foods = [desc]  # fallback: keep the raw description
    
    # 4) Remaining quantity
    remaining = payload.get("items_available", 0)
    # 5) Item price
    item_price = item["item_price"]["minor_units"] / (10 ** item["item_price"]["decimals"])
    item_value = item["item_value"]["minor_units"] / (10 ** item["item_value"]["decimals"])
    # 6) Pickup window → local time (Europe/London)
    tz_local = ZoneInfo("Europe/London")
    def to_local(iso_z):
        if not iso_z:
            return None
        dt = datetime.fromisoformat(iso_z.replace("Z", "+00:00"))
        return dt.astimezone(tz_local).strftime("%Y-%m-%d %H:%M")

    pickup_start = to_local(pickup.get("start"))
    pickup_end = to_local(pickup.get("end"))
    # 7) Packaging info
    packaging = "No" if item.get("packaging_option") == "BAG_ALLOWED" else "Yes"
    # 8) item category
    category = item.get("item_category", "N/A")
    return {
        "restaurant": restaurant_name,
        "id": id,
        "category": category,
        "address": full_address,
        "foods": candidates,
        "remaining": remaining,
        "price": item_price,
        "value": item_value,
        "pickup_window": f"{pickup_start} → {pickup_end}" if pickup_start and pickup_end else None,
        "need to bring own bag?": packaging,
    }

args = argparse.ArgumentParser()
args.add_argument("--order", default="None", help="Make an order of an item by ID")
args = args.parse_args()

for i, payload in enumerate(items):
    summary = summarize_magic_bag(payload)

    # Pretty print card
    print(f"""🍱 {summary['restaurant']} - {summary['id']}
    📍 {summary['address']}
    🕒 Pickup: {summary['pickup_window']}
    📦 Left: {summary['remaining']}
    💷 Price: £{summary['price']}
    💰 Original value: £{summary['value']}
    🍽️  Possible items: {summary['foods']}
    🛍️  Bring own bag? {summary['need to bring own bag?']}"""
    )
    print("-" * 40)

if args.order != "None":
    print(f"Attempting to order item ID {args.order}...")
    order = client.create_order(args.order, 1)
    print("Order response:", order)
    time.sleep(2)  # wait a bit before polling
    order_status = client.get_order_status(order["id"])
    while order_status["state"] != "RESERVED":
        print("Waiting for reservation...")
        time.sleep(2)  # wait a bit before polling again
        order_status = client.get_order_status(order["id"])
    if order_status["state"] == "RESERVED":
        print("Order successful! 🎉")
    else:
        print("Order may have failed. Please check the response above.")
# # ---- Example usage ----
# payload = items[-1]  # paste your JSON dict here
# summary = summarize_magic_bag(payload)

# # Pretty print card
# print(f"""🍱 {summary['restaurant']}
# 📍 {summary['address']}
# 🕒 Pickup: {summary['pickup_window']}
# 📦 Left: {summary['remaining']}
# 💷 Price: £{summary['price']}
# 🍽️ Possible items: {", ".join(summary['foods'][:6])}{' …' if len(summary['foods'])>6 else ''}
# 🛍️ Bring own bag? {summary['need to bring own bag?']}"""
# )



# print(type(items))
# print(items[0])