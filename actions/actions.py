# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions


# This is a simple example for a custom action which utters "Hello World!"

from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import FollowupAction
# Import your existing TGTG wrapper here
from tgtg import TgtgClient
from actions.items_summary import summarize_magic_bag
from actions.client_mamager import tgtg_manager
import os
import argparse
import dotenv
dotenv.load_dotenv()

GLOBAL_TGTG_CLIENT = TgtgClient(
    access_token=os.getenv("ACCESS_TOKEN"),
    refresh_token=os.getenv("REFRESH_TOKEN"),
    cookie=os.getenv("COOKIE")
)

class ActionTgtgBase(Action):
    """
    所有 TGTG 相关 Action 的父类。
    它会自动处理 Client 获取和登录验证。
    """

    def name(self) -> Text:
        raise NotImplementedError("Subclasses must define a name.")

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # 1. 统一获取 Client
        user_id = tracker.sender_id
        client = tgtg_manager.get_client(user_id)

        # 2. 统一拦截：如果没登录，或者 Token 失效
        if not client:
            dispatcher.utter_message(text="To proceed your request, I need to verify your identity")
            # 3. 拦截后，强制跳转到登录流程
            # 假设你有一个 action 叫 action_ask_email 或意图叫 enter_login_flow
            return [FollowupAction("action_start_login_process")]

        # 4. 如果验证通过，调用子类的业务逻辑
        # 我们定义一个新方法 run_authenticated 供子类实现
        try:
            return self.run_authenticated(dispatcher, tracker, domain, client)
        except Exception as e:
            # 5. 统一异常处理（比如网络超时，或者 Token 刷新失败）
            print(f"Error in {self.name()}: {e}")
            dispatcher.utter_message(text="发生了一个连接错误，请稍后再试。")
            return []

    def run_authenticated(self, dispatcher, tracker, domain, client) -> List[Dict[Text, Any]]:
        """
        子类必须实现这个方法，而不是标准的 run 方法。
        这里传进来的 client 保证是 100% 可用的。
        """
        raise NotImplementedError("Subclasses must implement run_authenticated")

class ActionTGTGClientLogin(Action):
    def name(self) -> Text:
        return "action_tgtg_login"
    

class ActionCheckAvailability(Action):

    def name(self) -> Text:
        return "action_check_tgtg"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # 1. Get the store name entity from the user input
        store_name = next(tracker.get_latest_entity_values("store"), None)

        if not store_name:
            dispatcher.utter_message(text="Which store should I check?")
            return []

        # 2. Call your TGTG API (Pseudo-code)
        client = GLOBAL_TGTG_CLIENT
        items = client.get_items()
        if store_name.lower() not in [item['store']['store_name'] for item in items]:
            dispatcher.utter_message(text=f"I couldn't find {store_name} in your favorites.")
            return []
        
        # MOCK RESPONSE for demonstration
        for i, payload in enumerate(items):
            if payload['store']['store_name'].lower() == store_name.lower():
                break
        else:
            dispatcher.utter_message(text=f"I couldn't find {store_name} in your favorites.")
            return []
        item_summary = summarize_magic_bag(payload)
        items_available = item_summary.get("remaining", 0)
        
        if items_available > 0:
            dispatcher.utter_message(text=f"Yes! {store_name} has {items_available} bags available.")
        else:
            dispatcher.utter_message(text=f"Sorry, nothing at {store_name} right now.")

        return []

class ActionCheckPickupTime(Action):
    def name(self) -> Text:
        return "action_check_pickup_time"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
            
        items = GLOBAL_TGTG_CLIENT.get_items()
        store_name = domain.get("store")
        if not store_name:
            dispatcher.utter_message(text="Which store's pickup time should I check?")
            return []
        
        if store_name.lower() not in [item['store']['store_name'] for item in items]:
            dispatcher.utter_message(text=f"I couldn't find {store_name} in your favorites.")
            return []
        
        # MOCK RESPONSE for demonstration
        for i, payload in enumerate(items):
            if payload['store']['store_name'].lower() == store_name.lower():
                break
        else:
            dispatcher.utter_message(text=f"I couldn't find {store_name} in your favorites.")
            return []
        
        item_summary = summarize_magic_bag(payload)
        
        # Call your TGTG API to get pickup time
        # For demonstration, we will mock this
        pickup_time = item_summary.get("pickup_window", "unknown")
        
        dispatcher.utter_message(text=f"The pickup time for {store_name} is {pickup_time}.")
        
        return []
    
class ActionReserveOrder(Action):
    def name(self) -> Text:
        return "action_reserve_tgtg"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
            
        store_name = domain.get("store")
        if not store_name:
            dispatcher.utter_message(text="Which store should I reserve a bag from?")
            return []
        items = GLOBAL_TGTG_CLIENT.get_items()
        if store_name.lower() not in [item['store']['store_name'] for item in items]:
            dispatcher.utter_message(text=f"I couldn't find {store_name} in your favorites.")
            return []
        
        # Call your TGTG API to reserve
        # result = client.reserve(store_name)
        
        dispatcher.utter_message(text=f"I have attempted to reserve a bag at {store_name}. Check your app to confirm payment.")
        
        return []