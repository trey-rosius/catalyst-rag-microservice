import grpc
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA

from fastapi import FastAPI
import logging
import os
import tempfile
import whisper
from pytubefix import YouTube
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
#YOUTUBE_VIDEO = "https://www.youtube.com/watch?v=cdiD-9MMpb0"
YOUTUBE_VIDEO = "https://www.youtube.com/watch?v=T-D1OfcDW1M"


@app.post('/v1.0/get/youtube')
def get_youtube(query_model: QueryModel):
    print("we in here 1")

    # Let's do this only if we haven't created the transcription file yet.
    if not os.path.exists("transcription.txt"):
        print("we in here 2")
        youtube = YouTube(YOUTUBE_VIDEO,'WEB_CREATOR')
        audio = youtube.streams.get_audio_only()
        print("we in here 3")

        # Let's load the base model. This is not the most accurate
        # model but it's fast.
        whisper_model = whisper.load_model("base")
        print("we in here 3-1")

        with tempfile.TemporaryDirectory() as tmpdir:
            print("we in here 4")
            file = audio.download(output_path=tmpdir,mp3=True)
            transcription = whisper_model.transcribe(file, fp16=False)["text"].strip()
            print("we in here 5")

            with open("transcription.txt", "w") as file:
                print("we in here 6")
                file.write(transcription)
        with open("transcription.txt") as file:
            print("we in here 7")
            transcription = file.read()

        return transcription[:100]
    else:
        with open("transcription.txt") as file:
            transcription = file.read()

        return transcription[:100]


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
