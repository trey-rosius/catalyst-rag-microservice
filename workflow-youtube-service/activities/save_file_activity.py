import json
import grpc
import base64
import os
from dapr.clients import DaprClient
from fastapi import FastAPI, HTTPException
import dapr.ext.workflow as wf


pubsub_name = os.getenv('DAPR_PUB_SUB', '')
s3_bucket = os.getenv('DAPR_BUCKET', '')
topic_name = os.getenv('UPLOADED_PDF_TOPIC_NAME', '')

wfr = wf.WorkflowRuntime()
wf_client = wf.DaprWorkflowClient()
wfr.start()

@wfr.activity
def upload_file_s3(ctx, activity_input: any):
    with DaprClient() as d:
        try:
            with open('../transcription.txt', 'rb') as file:
                file_content = file.read()

                # Encode the contents to base64
            encoded_content = base64.b64encode(file_content)

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
                    "message":"encoded content was null"
                }

        except grpc.RpcError as err:
            print(f"Error={err.details()}")
            raise HTTPException(status_code=500, detail=err.details())
