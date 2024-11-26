import os

from dotenv import load_dotenv

load_dotenv()

class Config:
    """Bot Configuration"""

    PORT = 8000
    APP_ID = os.environ.get("BOT_ID")
    APP_PASSWORD = os.environ.get("BOT_PASSWORD")
    AZURE_OPENAI_API_KEY = os.environ["AZURE_OPENAI_API_KEY"] # Azure OpenAI API key
    AZURE_OPENAI_MODEL_DEPLOYMENT_NAME = os.environ["AZURE_OPENAI_MODEL_DEPLOYMENT_NAME"] # Azure OpenAI model deployment name
    AZURE_OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"] # Azure OpenAI endpoint
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"] # Azure OpenAI embedding deployment
    AZURE_SEARCH_KEY = os.environ["AZURE_SEARCH_KEY"] # Azure Search key
    AZURE_SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"] # Azure Search endpoint
    MicrosoftAppPassword= os.environ["BOT_PASSWORD"]
    MicrosoftAppId = os.environ["BOT_ID"]

    
    print("ID: True") if APP_ID == MicrosoftAppId else print(f"ID: Not True")
    print("ID: True") if APP_PASSWORD == MicrosoftAppPassword else print("ID: Not True")
        

    #print(f"{APP_ID}\n{APP_PASSWORD}\n{AZURE_OPENAI_API_KEY}\n{AZURE_OPENAI_MODEL_DEPLOYMENT_NAME}\{AZURE_OPENAI_ENDPOINT}")
    #print(f"{AZURE_OPENAI_EMBEDDING_DEPLOYMENT}\n{AZURE_SEARCH_KEY}\n{AZURE_SEARCH_ENDPOINT}\n{MicrosoftAppPassword}\n{MicrosoftAppId}")