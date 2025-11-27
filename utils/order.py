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

active = client.get_active()
print(active)