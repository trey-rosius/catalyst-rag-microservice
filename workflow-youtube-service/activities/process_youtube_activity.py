import dapr.ext.workflow as wf
import logging
import os
import tempfile
import whisper
from pytubefix import YouTube

user_db = os.getenv('DAPR_USER_DB', '')

PINECONE_API_KEY = os.getenv('PINECONE_API_KEY', "")
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
os.environ['PINECONE_API_KEY'] = PINECONE_API_KEY
os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY
logging.basicConfig(level=logging.INFO)

YOUTUBE_VIDEO = "https://www.youtube.com/watch?v=cdiD-9MMpb0"
wfr = wf.WorkflowRuntime()
wf_client = wf.DaprWorkflowClient()
wfr.start()


@wfr.activity
def process_youtube_video(ctx, activity_input: any):
    print("we in here 1")

    # Let's do this only if we haven't created the transcription file yet.
    if not os.path.exists("../transcription.txt"):
        print("we in here 2")
        youtube = YouTube(YOUTUBE_VIDEO)
        audio = youtube.streams.filter(only_audio=True).first()
        print("we in here 3")

        # Let's load the base model. This is not the most accurate
        # model but it's fast.
        whisper_model = whisper.load_model("base")
        print("we in here 3-1")

        with tempfile.TemporaryDirectory() as tmpdir:
            print("we in here 4")
            file = audio.download(output_path=tmpdir)
            transcription = whisper_model.transcribe(file, fp16=False)["text"].strip()
            print("we in here 5")

            with open("../transcription.txt", "w") as file:
                print("we in here 6")
                file.write(transcription)
        with open("../transcription.txt") as file:
            print("we in here 7")
            transcription = file.read()

        return transcription[:100]
    else:
        with open("../transcription.txt") as file:
            transcription = file.read()

        return transcription[:100]
