import grpc
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA

from fastapi import FastAPI
import logging
import os

from models.query_model import QueryModel
from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone

user_db = os.getenv('DAPR_USER_DB', '')

app = FastAPI()
PINECONE_API_KEY = os.getenv('PINECONE_API_KEY', "")
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
os.environ['PINECONE_API_KEY'] = PINECONE_API_KEY
os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY
logging.basicConfig(level=logging.INFO)

index_name = 'dapr-langchain-rag-tutorial'
model_name = 'text-embedding-ada-002'


@app.post('/v1.0/state/query')
def query_rag(query_model: QueryModel):
    pc = Pinecone(api_key=PINECONE_API_KEY)
    index = pc.Index(index_name)
    embedding = OpenAIEmbeddings(api_key=OPENAI_API_KEY, model=model_name)
    text_field = "text"
    vectorstore = PineconeVectorStore(
        index, embedding, text_field
    )
    # completion llm
    llm = ChatOpenAI(
        openai_api_key=OPENAI_API_KEY,
        model_name='gpt-3.5-turbo',
        temperature=0.0
    )
    qa = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vectorstore.as_retriever()
    )
    logging.info(f"query is {query_model.query}")
    response = qa.run(query_model.query)

    return response
