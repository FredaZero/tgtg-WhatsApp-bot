from tgtg import TgtgClient
import json
import os

DB_FILE = "user_credentials.json"

class TGTGManager:
    def __init__(self):
        self._load_db()

    def _load_db(self):
        if not os.path.exists(DB_FILE):
            self.db = {}
        else:
            with open(DB_FILE, 'r') as f:
                self.db = json.load(f)

    def _save_db(self):
        with open(DB_FILE, 'w') as f:
            json.dump(self.db, f)

    def save_credential(self, user_id, credentials):
        """
        save user credentials
        user_id: WhatsApp sender_id
        credentials: dictionary returned after login
        """
        self.db[user_id] = credentials
        self._save_db()

    def get_client(self, user_id):
        """
        get global client instance
        """
        creds = self.db.get(user_id)
        
        if not creds:
            return None
        try:
            client = TgtgClient(
            access_token=creds.get("access_token"),
            refresh_token=creds.get("refresh_token"),
            cookie=creds.get("cookie")
        )
            return client
        except Exception as e:
            print(f"Error creating client for {user_id}: {e}")
            return None
        
tgtg_manager = TGTGManager()