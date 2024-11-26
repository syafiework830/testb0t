from langchain_core.prompts import ChatPromptTemplate
from langchain_openai.embeddings.azure import AzureOpenAIEmbeddings
from langchain_community.retrievers import AzureAISearchRetriever
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_openai.chat_models.azure import AzureChatOpenAI
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from langchain.chains.retrieval import create_retrieval_chain
import os
from dotenv import load_dotenv
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.prompts import (FewShotChatMessagePromptTemplate)
from langchain_community.document_compressors.flashrank_rerank import FlashrankRerank
from langchain.retrievers import ContextualCompressionRetriever

from langchain_community.vectorstores import AzureSearch
import warnings
from langchain._api import LangChainDeprecationWarning
warnings.simplefilter("ignore", category=LangChainDeprecationWarning)
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module='azure.search.documents.indexes.models._index')

from router_template import hr_template_semantic_hybrid
from botbuilder.core import ActivityHandler

load_dotenv()

AZURE_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY")
AZURE_SEARCH_ENDPOINT = os.environ.get("AZURE_SEARCH_ENDPOINT")
AZURE_COGNITIVE_SEARCH_INDEX_NAME = os.environ.get("AZURE_COGNITIVE_SEARCH_INDEX_NAME")
AZURE_COGNITIVE_SEARCH_API_KEY = os.environ.get("AZURE_COGNITIVE_SEARCH_API_KEY")
AZURE_CONN_STRING = os.environ.get("AZURE_CONN_STRING")
CONTAINER_NAME = os.environ.get("CONTAINER_NAME")

class hr_bot(ActivityHandler):

    def __init__(self):
        super().__init__()
        
        self.model = AzureChatOpenAI(model="gpt-4o-2024-08-06",
            azure_deployment="gpt-4o",
            api_key=AZURE_API_KEY,
            azure_endpoint="https://ocr-chatbot-mccalla.openai.azure.com/",
            api_version="2024-08-01-preview",
            max_tokens=4000
        )

        self.embeddings = AzureOpenAIEmbeddings(
                                model="text-embedding-3-large",
                                api_key="8dd26d2d746041fe90a8892f68806c3d",
                                azure_endpoint="https://ocr-chatbot-mccalla.openai.azure.com/",
                                api_version="2023-05-15", 
                                dimensions=1536)
        
        self.chat_history = []
        #self.selected_option = None  # Initialize the selected_option attribute

    async def hr_bot(self, text, chat_history, embeddings, model, selected_option, full_name, email):

        if selected_option == "mccalla-int":    #selected_option  = organization
            office_location = "Malaysia"
            indexName = "mccallaint_handbook"
            leave_portal = 'www.iloginhr.com'
            company_name = "McCalla Integrative"
        else:
            office_location = "US"
            indexName = "mrlp_handbook"
            leave_portal = 'Human Resource Department or your immediate superior'
            company_name = "McCalla Raymer Leibert Pierce"

        vector_store = AzureSearch(
            azure_search_endpoint=AZURE_SEARCH_ENDPOINT,
            azure_search_key=AZURE_COGNITIVE_SEARCH_API_KEY,
            index_name=indexName,
            embedding_function= embeddings,
            search_type= 'semantic-hybrid'
        )

        hr_template_msg = hr_template_semantic_hybrid()

        def few_shot_prompt(company_name):
            examples = [
                {
                    "input": "how many PTOs do I get?",
                    "output": f"To determine your annual leave entitlement, I need to know your length of service with {company_name}. How long have you been working here?"
                },
                {
                    "input": "how many PTOs do I have?",
                    "output": f"I can't assist you with that. Please visit www.iloginhr.com to check your available annual leave."
                },
                {
                    "input": "how many annual leave am I entitled to?",
                    "output": f"To determine your annual leave entitlement, please let me know how many years you have been working at {company_name}."
                },
                {
                    "input": "2 years",
                    "output": "Based on your 2 years of service, you are entitled to 15 days of annual leave per year."
                },
                {
                    "input": "how many medical leave days do I get?",
                    "output": "You are entitled to 18 days of Medical Leave annually. Remember, a Medical Certificate is required for each Medical Leave taken, and you must submit your leave applications via the leave application portal at www.iloginhr.com"
                }
            ]

            example_prompt = ChatPromptTemplate.from_messages([
                ("human", "{input}"),
                ("ai", "{output}"),
            ])
            
            few_shot_prompt = FewShotChatMessagePromptTemplate(
                example_prompt=example_prompt,
                examples=examples)
            
            return few_shot_prompt

        prompt = ChatPromptTemplate.from_messages([
            ("system", hr_template_msg),
            MessagesPlaceholder(variable_name="chat_history"),
            few_shot_prompt(company_name),
            ("human", '{input}')
        ])

        def retrieval_compression():
            retriever = AzureAISearchRetriever(
                service_name=AZURE_SEARCH_ENDPOINT,
                api_key=AZURE_COGNITIVE_SEARCH_API_KEY,
                content_key="content", 
                top_k=3, 
                index_name=indexName
                )

            compressor = FlashrankRerank(top_n=5)
            compression_retriever = ContextualCompressionRetriever(
                base_compressor=compressor, 
                base_retriever=retriever,
                ) 
            return compression_retriever

        retriever_prompt = ChatPromptTemplate.from_messages([
            MessagesPlaceholder(variable_name="chat_history"),
            ("system", '''
                Given a chat history and the latest user question
                which might reference context in the chat history, formulate a standalone question
                which can be understood without the chat history. Do NOT answer the question,
                just reformulate it if needed and otherwise return it as is.
            '''),
            ("human", '{input}')
        ])

        chain = create_stuff_documents_chain(model, prompt)
        history_aware_retriever = create_history_aware_retriever(
            llm=model,
            retriever=retrieval_compression,
            prompt=retriever_prompt
        )

        retrieval_chain = create_retrieval_chain(
            history_aware_retriever,
            chain
        )

        response = retrieval_chain.invoke({
            "input": text,
            "chat_history": chat_history,
            "context": history_aware_retriever,
            "leave_portal": leave_portal,
            "full_name": full_name,
            "email": email,
            "office_location":office_location,
            "company_name": company_name
        })

        return response['answer']