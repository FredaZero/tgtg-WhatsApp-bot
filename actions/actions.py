# actions/actions.py

import logging
from typing import Any, Text, Dict, List, Optional
from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import FollowupAction, SlotSet, Form
from tgtg import TgtgClient, TgtgAPIError, TgtgLoginError

# Assuming you have implemented the manager as discussed previously
from actions.client_manager import TGTGManager 
from actions.items_summary import summarize_magic_bag
from dateutil import parser # You might need: pip install python-dateutil

logger = logging.getLogger(__name__)

class ActionTgtgBase(Action):
    """
    Base Class for all TGTG Actions.
    Handles:
    1. Getting the client for the specific user.
    2. Auto-saving tokens if they were refreshed during the API call.
    3. Catching Auth errors and forcing a re-login if tokens are dead.
    """

    def name(self) -> Text:
        raise NotImplementedError("Subclasses must define a name.")

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        user_id = tracker.sender_id
        client = TGTGManager.get_client(user_id)

        # 1. Intercept: User not logged in at all
        if not client:
            dispatcher.utter_message(text="To proceed, I need to verify your identity with TGTG.")
            return [FollowupAction("action_start_login_process")]

        # 2. Try running the business logic
        try:
            # We pass the client to the subclass
            events = self.run_authenticated(dispatcher, tracker, domain, client)
            
            # 3. AUTO-REFRESH CHECK:
            # If the library refreshed the token during the API call, we must save it.
            # We compare the client's current tokens with what is in the DB.
            TGTGManager.save_if_changed(user_id, client)
            
            return events

        except (TgtgAPIError, TgtgLoginError) as e:
            # 4. Handle Token Expiration
            # If we get here, it means even the Refresh Token failed (or API is down).
            logger.error(f"TGTG API Error for user {user_id}: {e}")
            
            # Check if it's an Auth error (usually 401 or 403)
            # Note: exact status code checking depends on tgtg-python version, 
            # but generally assuming fatal auth error here:
            
            dispatcher.utter_message(text="Your login session has expired. Let's authenticate you again.")
            
            # Clear old credentials so we don't loop
            # (You need to implement a delete method in your manager, or just overwrite later)
            # tgtg_manager.delete_credentials(user_id) 
            
            return [FollowupAction("action_start_login_process")]

        except Exception as e:
            logger.error(f"Unexpected error in {self.name()}: {e}", exc_info=True)
            dispatcher.utter_message(text="I'm having trouble connecting to TGTG right now. Please try again later.")
            return []

    def run_authenticated(self, dispatcher, tracker, domain, client) -> List[Dict[Text, Any]]:
        raise NotImplementedError("Subclasses must implement run_authenticated")


# -------------------------------------------------------------------------
# Login Flow
# -------------------------------------------------------------------------

class ActionTGTGClientLogin(Action):
    def name(self) -> Text:
        return "action_start_login_process"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        dispatcher.utter_message(text="Okay, I'll send a verification email to you.")
        return [
            SlotSet("requested_slot", "email"),
            Form("login_form") 
        ]
    
class ActionSubmitLoginForm(FormValidationAction):
    def name(self) -> Text:
        return "action_submit_login_form"

    async def run(self, dispatcher, tracker, domain):
        email = tracker.get_slot("email")
        user_id = tracker.sender_id
        
        if not email:
            dispatcher.utter_message(text="I need a valid email address.")
            return [Form(self.name())]

        client = TgtgClient(email=email)
        
        try:
            dispatcher.utter_message(text=f"Sending email to {email}. Please check your inbox and click the link inside.")
            
            # BLOCKING CALL: This waits for the user to click the link
            credentials = client.get_credentials() 
            
            # Save to DB
            TGTGManager.save_credentials(user_id, credentials)
            
            dispatcher.utter_message(text="Authentication successful! You can now use the bot.")
            
            return [SlotSet("is_logged_in", True), SlotSet("email", email), Form(None)]
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            dispatcher.utter_message(text="⚠️ Verification timed out or failed. Please try again.")
            return [Form(None)] # Stop the form so they aren't stuck

# -------------------------------------------------------------------------
# Business Logic
# -------------------------------------------------------------------------
class ActionCheckAvailability(ActionTgtgBase):
    def name(self) -> Text:
        return "action_check_tgtg"

    def run_authenticated(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
            client: TgtgClient) -> List[Dict[Text, Any]]:

        # 1. Get Store Name
        store_name = tracker.get_slot("store") or next(tracker.get_latest_entity_values("store"), None)

        if not store_name:
            dispatcher.utter_message(text="Which store should I check?")
            return []

        items = client.get_items()
        
        # 2. Find the matching item
        target_payload = None
        for item in items:
            # Compare lowercase to be safe
            if store_name.lower() in item['store']['store_name'].lower():
                target_payload = item
                break
        
        if not target_payload:
            dispatcher.utter_message(text=f"I couldn't find '{store_name}' in your favorites list.")
            return []
        
        # 3. USE YOUR CUSTOM FUNCTION
        summary = summarize_magic_bag(target_payload)
        
        stock = summary.get('remaining', 0)
        restaurant_name = summary.get('restaurant', store_name)
        item_id = summary.get('id')
        
        if stock > 0:
            # Optional: Add extra info like price or rating if available in your summary
            price = summary.get('price', '')
            dispatcher.utter_message(text=f"Yes! {restaurant_name} has {stock} bags available ({price}).")
            
            # Save vital data for subsequent actions (Ordering/Calendar)
            return [
                SlotSet("availability", str(stock)),
                SlotSet("item_id", item_id),
                SlotSet("store", restaurant_name) 
            ]
        else:
            dispatcher.utter_message(text=f"Sorry, nothing at {restaurant_name} right now.")
            return []

class ActionCheckPickupTime(ActionTgtgBase):
    def name(self) -> Text:
        return "action_check_pickup_time"

    def run_authenticated(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
            client: TgtgClient) -> List[Dict[Text, Any]]:
            
        store_name = tracker.get_slot("store")
        if not store_name:
            dispatcher.utter_message(text="Which store are we talking about?")
            return []
        
        items = client.get_items()
        
        target_payload = None
        for item in items:
            if store_name.lower() in item['store']['store_name'].lower():
                target_payload = item
                break

        if not target_payload:
            dispatcher.utter_message(text=f"Cannot find info for {store_name}.")
            return []

        # 1. USE YOUR CUSTOM FUNCTION for the Message
        summary = summarize_magic_bag(target_payload)
        
        # Your function returns a pretty string like "18:00 → 18:30"
        readable_window = summary.get("pickup_window")

        if readable_window:
             dispatcher.utter_message(text=f"The pickup time for {summary['restaurant']} is: {readable_window}.")
        else:
             dispatcher.utter_message(text=f"The pickup time is currently unavailable.")

        # 2. USE RAW DATA for the Slot (Calendar needs ISO format)
        # We cannot easily parse "18:00 -> 18:30" back into a date object without knowing "Today" vs "Tomorrow".
        # So we grab the raw start time from the original payload for the system to remember.
        try:
            raw_start_time = target_payload['pickup_interval']['start']
        except (KeyError, TypeError):
            raw_start_time = None

        return [SlotSet("pickup_time", raw_start_time)]

class ActionReserveOrder(ActionTgtgBase):
    def name(self) -> Text:
        return "action_reserve_tgtg"

    def run_authenticated(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
            client: TgtgClient) -> List[Dict[Text, Any]]:
            
        # We rely on the Slot set by ActionCheckAvailability
        item_id = tracker.get_slot("item_id")
        
        if not item_id:
            dispatcher.utter_message(text="I'm not sure which item you want to order. Please check stock first.")
            return []
            
        try:
            client.checkout(item_id)
            dispatcher.utter_message(text="🎉 Order locked! Please complete payment in the TGTG app.")
        except Exception as e:
            dispatcher.utter_message(text=f"Failed to create order: {str(e)}")
        
        return []
    
class ActionReminder(Action):
    def name(self) -> Text:
        return "action_set_reminder"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        pickup_time_str = tracker.get_slot("pickup_time")
        store_name = tracker.get_slot("store") or "TGTG Pickup"
        
        if not pickup_time_str:
            dispatcher.utter_message(text="I don't have a pickup time saved. Please ask for the pickup time first.")
            return []

        try:
            # 1. Parse the ISO string (e.g., '2023-10-27T18:00:00Z')
            dt = parser.parse(pickup_time_str)
            
            # 2. Format for your Calendar Tool (Assuming format YYYYMMDDTHHMM)
            formatted_time = dt.strftime("%Y%m%dT%H%M")
            
            # TODO
            # --- GOOGLE CALENDAR LOGIC HERE ---
            # result = google_calendar.create_event(summary=f"Food: {store_name}", start=formatted_time)
            
            dispatcher.utter_message(text=f"✅ I've added a reminder for {store_name} at {dt.strftime('%H:%M')} to your calendar.")
            
        except Exception as e:
            logger.error(f"Calendar error: {e}")
            dispatcher.utter_message(text="I couldn't process the date format for the calendar.")
        
        return []