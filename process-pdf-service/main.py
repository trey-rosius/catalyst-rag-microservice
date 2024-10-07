import time

import grpc
from pinecone import ServerlessSpec, Pinecone
from langchain_community.embeddings import OpenAIEmbeddings
from models.cloud_events import CloudEvent
import logging
import tempfile
import whisper

import base64

import os
from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from dapr.clients import DaprClient
from fastapi import FastAPI, HTTPException
from langchain_text_splitters import CharacterTextSplitter
from pypdf import PdfReader

app = FastAPI()
pinecone_api_key = os.getenv('PINECONE_API_KEY', '')
open_ai_api_key = os.getenv('OPENAI_API_KEY', '')



os.environ['PINECONE_API_KEY'] = pinecone_api_key
os.environ['OPENAI_API_KEY'] = os.getenv('OPEN_AI_API_KEY', '')
logging.basicConfig(level=logging.INFO)
index_name = 'dapr-langchain-rag-tutorial'


def decode_base64_to_pdf(base64_string, output_file_path):
    # Decode the Base64 string to binary data
    pdf_data = base64.b64decode(base64_string)
    # Write the binary data to a PDF file
    with open(output_file_path, "wb") as pdf_file:
        pdf_file.write(pdf_data)
        print(f"PDF file has been saved to {output_file_path}")



@app.post('/subscribe/files/process')
async def process_pdf_event(event: CloudEvent):
    with DaprClient() as d:
        try:

            with open("output.pdf", "rb") as f:
                reader = PdfReader(f)
                pages = str(len(reader.pages))

                print(f"pages : {pages}")

            pc = Pinecone(api_key=pinecone_api_key)
            spec = ServerlessSpec(cloud='aws', region='us-east-1')

            if index_name in pc.list_indexes().names():
                pc.delete_index(index_name)
                # create a new index
            pc.create_index(
                index_name,
                dimension=1536,  # dimensionality of text-embedding-ada-002
                metric='dotproduct',
                spec=spec
            )
            # wait for index to be initialized
            while not pc.describe_index(index_name).status['ready']:
                time.sleep(1)
                ##pdf loader
            loader = PyPDFLoader("output.pdf")

            documents = loader.load()
            text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
            docs = text_splitter.split_documents(documents)

            embeddings = OpenAIEmbeddings(api_key=open_ai_api_key)
            vector_store = PineconeVectorStore.from_documents(
                docs,
                embeddings,
                index_name=index_name,

            )
            return {"message": "Successfully loaded"}

        except grpc.RpcError as err:
            print(f"Error={err.details()}")
            raise HTTPException(status_code=500, detail=err.details())


