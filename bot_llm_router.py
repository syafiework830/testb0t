from botbuilder.schema import Activity, ActivityTypes
from botbuilder.schema.teams import TeamsChannelAccount
from botbuilder.core import ActivityHandler, TurnContext, MessageFactory
from botbuilder.schema import ChannelAccount
from botbuilder.core.teams import TeamsInfo

import os
from dotenv import load_dotenv
from typing import List

from langchain_openai.chat_models.azure import AzureChatOpenAI
import warnings
from langchain._api import LangChainDeprecationWarning
warnings.simplefilter("ignore", category=LangChainDeprecationWarning)
from langchain_openai.embeddings.azure import AzureOpenAIEmbeddings

from router_template import greeting
from bot_hr import hr_bot

load_dotenv()

AZURE_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY")
AZURE_COGNITIVE_SEARCH_SERVICE_NAME = os.environ.get("AZURE_COGNITIVE_SEARCH_SERVICE_NAME")
AZURE_COGNITIVE_SEARCH_INDEX_NAME = os.environ.get("AZURE_COGNITIVE_SEARCH_INDEX_NAME")
AZURE_COGNITIVE_SEARCH_API_KEY = os.environ.get("AZURE_COGNITIVE_SEARCH_API_KEY")
AZURE_CONN_STRING = os.environ.get("AZURE_CONN_STRING")
CONTAINER_NAME = os.environ.get("CONTAINER_NAME")

class TeamsBot(ActivityHandler):
    def __init__(self):
        super().__init__()

        self.model = AzureChatOpenAI(model="gpt-4o-2024-08-06",
            azure_deployment="gpt-4o",
            api_key=AZURE_API_KEY,
            azure_endpoint="https://ocr-chatbot-mccalla.openai.azure.com/",
            api_version="2024-08-01-preview"
        )

        self.embeddings = AzureOpenAIEmbeddings(
                                model="text-embedding-3-large",
                                api_key="8dd26d2d746041fe90a8892f68806c3d",
                                azure_endpoint="https://ocr-chatbot-mccalla.openai.azure.com/",
                                api_version="2023-05-15",
                                dimensions= 1536)

        # Keep self.sessions as a set
        self.sessions = set()  # A set to track active users by member_id

        # Store detailed of user that already logged
        self.user_data = {}  

        self.hr_bot_instance = hr_bot()

    async def on_members_added_activity(self, members_added: List[ChannelAccount], turn_context: TurnContext):
        
        '''
        ================================================================================
        Function Context: Identify the member's detail for every initialized session
        ================================================================================
        '''

        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await self.initialize_or_retrieve_session(turn_context, member.id)
                await turn_context.send_activity(f"{greeting(member.name)}")

    async def initialize_or_retrieve_session(self, turn_context: TurnContext, member_id: str):

        '''
        ================================================================================
        Function Context: Identify if the member's session already recorded in sessions 
        set for retrieval. Else, the member will be treated as a 'GUEST' 
        ================================================================================
        '''

        if member_id not in self.sessions:
            teams_member = await self.get_member(turn_context, member_id)
            if teams_member:
                self._store_member_data(member_id, teams_member)
            else:
                self._store_guest_data()
        return self.user_data.get(member_id, self.user_data.get("Guest"))

    def _store_member_data(self, member_id, teams_member):

        '''
        ================================================================================
        Function Context: store member's data that already into the session
        ================================================================================
        '''

        self.sessions.add(member_id)
        self.user_data[member_id] = {
            "full_name": f"{teams_member.given_name} {teams_member.surname}",
            "name": teams_member.given_name,
            "email": teams_member.email,
            "organization": teams_member.email.split("@")[1].split(".")[0],
            "selected_option": teams_member.email.split("@")[1].split(".")[0].lower().strip(),
            "list_prompt": [],
            "list_response": [],
            "chat_history": [],
            "store": {}
        }

    def _store_guest_data(self):
        self.sessions.add("Guest")
        self.user_data["Guest"] = {
            "full_name": "Guest",
            "name": "Guest",
            "email": "No Email",
            "organization": "mccalla-int",
            "selected_option": "mccalla-int",
            "list_prompt": [],
            "list_response": [],
            "chat_history": [],
            "store": {}
        }

    async def get_member(self, turn_context: TurnContext, member_id: str) -> TeamsChannelAccount:
        try:
            if turn_context.activity.channel_data:
                member = await TeamsInfo.get_member(turn_context, member_id)
                return TeamsChannelAccount().deserialize(member.serialize())
            else:
                raise ValueError("No channel_data available in TurnContext activity.")
        except Exception as e:
            print(f"Error retrieving member: {e}")
            return None
        
    async def on_message_activity(self, turn_context: TurnContext):

        '''
        ================================================================================
        Function Context: 
        1. The input handling from the user by the BOT
        2. Retrieve member id to specify sessions.
        3. Routing chat to specific bots for responses.
        4. Conversation histories limited to 20 messages and 10 responses
        ================================================================================
        '''

        # Retrieving the member id and call out history's and other data 
        member_id = turn_context.activity.from_property.id or "Guest"
        user_session = await self.initialize_or_retrieve_session(turn_context, member_id)

        print(user_session["name"])

        # Receiving input (text) from user 
        text = turn_context.activity.text
        typing_activity = Activity(type=ActivityTypes.typing)
        await turn_context.send_activities([typing_activity])

        '''
        >>>>> HR Chatbot is Here!
        '''
        user_session["list_prompt"].append(text)

        res = await self.hr_bot_instance.hr_bot(
            text, 
            user_session["chat_history"], 
            self.embeddings, 
            self.model, 
            user_session["selected_option"], 
            user_session["full_name"], 
            user_session["email"]
            )
        # Appending interactions and prompting output
        # if more than 20, delete the earlier messages
        user_session["list_response"].append(res)
        if len(user_session["list_response"]) > 10:
            user_session["list_response"].pop(0)

        user_session["chat_history"].append({"role": "user", "content": text})
        user_session["chat_history"].append({"role": "assistant", "content": res})
        if len(user_session["chat_history"]) > 20:
            user_session["chat_history"].pop(0)

        await turn_context.send_activity(MessageFactory.text(res))