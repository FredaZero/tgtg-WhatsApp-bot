# tgtg-WhatsApp-bot
## Project Status: In Development
This project aims to build an intelligent conversational bot using the **Rasa framework** and the Meta WhatsApp platform. The bot automates processes for Too Good To Go (TGTG), including availability monitoring and order placement.
## Key Features
This assistant is designed to streamline the TGTG experience by offering the following core functionalities:

| Feature | Description | Status |
| :--- | :--- | :--- |
| **🔐 One-Time Authentication** | On first use, the TGTG Token is obtained via email verification and stored persistently; subsequent uses do not require re-login. | ✅ Designed |
| **📦 Real-Time Stock Query** | Users can check the remaining quantity of products at a specified store. | ✏️ In Progress |
| **🕒 Pickup Time Query** | Automatically provides the pickup time window for the order. | ✏️ In Progress |
| **🛒 API Ordering** | Lock and create an order for the user via the TGTG API. | ⏳ To Be Integrated |
| **📅 Calendar Integration** | After a successful order, the pickup event can be saved to the user's calendar (by sending an `.ics` file). | ⏳ To Be Integrated |
| **🔄 Background Monitoring** | **Core Feature:** The bot polls the target store's availability every 30 minutes, and notifies the user immediately once stock is found. | ✏️ In Progress |
## Technical Architecture & Stack
The project utilizes a modular architecture based on the following key components:
| Category | Component | Purpose |
| :--- | :--- | :--- |
| **Conversational AI** | **Rasa Open Source** | NLU (Natural Language Understanding) and Core Dialogue Management. |
| **Messaging** | **Meta WhatsApp Business Platform** | Handles message sending/receiving via Webhooks. |
| **TGTG Client** | ```tgtg-python``` | Community-maintained, unofficial Python client for the TGTG API. |
| **Persistence** | **Database (e.g., PostgreSQL/SQLite)** | Stores user session data, TGTG Tokens, and monitoring task queues.|
| **Scheduling** | ```APScheduler```| Runs a separate service for the 30-minute inventory polling and proactive messaging. |
| **Custom Design** | ```BaseTgtgAction``` | An abstract base class for custom actions, implementing centralized login verification and client injection to prevent code repetition. |
## Important Disclaimer
Please be aware that this project relies on an unofficial/reverse-engineered TGTG client (tgtg-python).

Risk: Using a non-official API may violate Too Good To Go's Terms of Service.

Stability: The API interface is subject to change without notice, which may cause features to break.

The developers of this project are not responsible for any account issues or legal consequences resulting from its use.

