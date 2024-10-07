import base64
import json
import os

import grpc
from dapr.clients import DaprClient
from fastapi import FastAPI, HTTPException
import time

import grpc
from pinecone import ServerlessSpec, Pinecone
from langchain_community.embeddings import OpenAIEmbeddings

from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings
import os
import tempfile
import whisper
from pytubefix import YouTube
import dapr.ext.workflow as wf
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader

user_db = os.getenv('DAPR_USER_DB', '')

import logging

import dapr.ext.workflow as wf

pubsub_name = os.getenv('DAPR_PUB_SUB', '')
s3_bucket = os.getenv('DAPR_BUCKET', '')
topic_name = os.getenv('UPLOADED_PDF_TOPIC_NAME', '')
pinecone_api_key = os.getenv('PINECONE_API_KEY', '')
open_ai_api_key = os.getenv('OPENAI_API_KEY', '')
# YOUTUBE_VIDEO = "https://www.youtube.com/watch?v=cdiD-9MMpb0"
#YOUTUBE_VIDEO = "https://www.youtube.com/watch?v=T-D1OfcDW1M"
YOUTUBE_VIDEO = "https://www.youtube.com/watch?v=oX7OduG1YmI"
os.environ['PINECONE_API_KEY'] = pinecone_api_key
# os.environ['OPENAI_API_KEY'] = os.getenv('OPEN_AI_API_KEY', '')
os.environ['OPENAI_API_KEY'] = open_ai_api_key
logging.basicConfig(level=logging.INFO)
index_name = 'dapr-langchain-rag'

app = FastAPI()
base_url = os.getenv('DAPR_HTTP_ENDPOINT', 'http://localhost')
pubsub_name = os.getenv('DAPR_PUB_SUB', '')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
wfr = wf.WorkflowRuntime()
wf_client = wf.DaprWorkflowClient()
wfr.start()


@app.post('/v1.0/start')
def initiate_payment():
    try:
        with DaprClient() as d:
            start_workflow = d.start_workflow(
                workflow_name='youtube_workflow',
                input={"status": True},
                workflow_component="dapr"
            )
            logging.info(f'Starting workflow with instance id: {start_workflow.instance_id}')
            return {"message": "Workflow started successfully", "workflow_id": start_workflow.instance_id}

    except grpc.RpcError as err:
        logger.error(f"Failed to start workflow: {err}")
        raise HTTPException(status_code=500, detail=str(err))


@wfr.workflow(name='youtube_workflow')
def youtube_process_workflow(ctx: wf.DaprWorkflowContext, wf_input: any):
    try:
        wf_input['instance_id'] = ctx.instance_id
        process_youtube_video_response = yield ctx.call_activity(process_youtube_video, input=wf_input)
        if process_youtube_video_response is not None:
            yield ctx.call_activity(upload_file_s3,
                                    input={

                                        "status": True

                                    })

            yield ctx.call_activity(save_to_vector_store,
                                    input={

                                        "status": True

                                    })


        else:
            return "Could not process youtube video"


    except Exception as e:
        yield ctx.call_activity(error_handler, input=str(e))
        raise
    return [process_youtube_video, upload_file_s3, save_to_vector_store]


@wfr.activity
def error_handler(ctx, error):
    print(f'Executing error handler: {error}.')


@wfr.activity
def upload_file_s3(ctx, activity_input: any):
    with DaprClient() as d:
        try:
            with open("transcription.txt", 'rb') as file:
                transcription = file.read()

                # Encode the contents to base64
            encoded_content = base64.b64encode(transcription)

            if encoded_content is not None:

                d.invoke_binding(binding_name=s3_bucket, operation="create",
                                 data=encoded_content,
                                 binding_metadata={"key": "transcription.txt"
                                                   })
                return {
                    "message": "successful"
                }
            else:
                return {
                    "message": "encoded content was null"
                }

        except grpc.RpcError as err:
            print(f"Error={err.details()}")
            raise HTTPException(status_code=500, detail=err.details())


@wfr.activity
def process_youtube_video(ctx, activity_input: any):
    print("we in here 1")

    # Let's do this only if we haven't created the transcription file yet.
    if not os.path.exists("transcription.txt"):
        print("we in here 2")
        youtube = YouTube(YOUTUBE_VIDEO, 'WEB_CREATOR')
        audio = youtube.streams.get_audio_only()
        print("we in here 3")

        # Let's load the base model. This is not the most accurate
        # model but it's fast.
        whisper_model = whisper.load_model("base")
        print("we in here 3-1")

        with tempfile.TemporaryDirectory() as tmpdir:
            print("we in here 4")
            file = audio.download(output_path=tmpdir, mp3=True)
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


@wfr.activity
def save_to_vector_store(ctx, activity_input: any):
    with DaprClient() as d:
        try:
            loader = TextLoader("transcription.txt")
            text_documents = loader.load()
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=20)
            documents = text_splitter.split_documents(text_documents)

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

            embeddings = OpenAIEmbeddings(api_key=open_ai_api_key)
            vector_store = PineconeVectorStore.from_documents(
                documents,
                embeddings,
                index_name=index_name,

            )
            return {"message": "Successfully loaded"}

        except grpc.RpcError as err:
            print(f"Error={err.details()}")
            raise HTTPException(status_code=500, detail=err.details())
