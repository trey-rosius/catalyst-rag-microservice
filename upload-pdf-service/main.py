import json
import grpc
import base64
import os
from dapr.clients import DaprClient
from fastapi import FastAPI, HTTPException
from models.upload_model import UploadModel

app = FastAPI()
pubsub_name = os.getenv('DAPR_PUB_SUB', '')
s3_bucket = os.getenv('DAPR_BUCKET', '')
topic_name = os.getenv('UPLOADED_PDF_TOPIC_NAME', '')


def decode_base64_to_pdf(base64_string, output_file_path):
    # Decode the Base64 string to binary data
    pdf_data = base64.b64decode(base64_string)
    # Write the binary data to a PDF file
    with open(output_file_path, "wb") as pdf_file:
        pdf_file.write(pdf_data)
        print(f"PDF file has been saved to {output_file_path}")


@app.post('/v1.0/binding/files')
def getUploadedFile(uploadModel: UploadModel):
    with DaprClient() as d:
        try:

            d.invoke_binding(binding_name=s3_bucket, operation="create",
                             data=uploadModel.base_64_encoded,
                             binding_metadata={"key": uploadModel.file_name_ext
                                               })

            d.publish_event(
                pubsub_name=pubsub_name,
                topic_name=topic_name,
                data=json.dumps({
                    "key": uploadModel.file_name_ext
                }),
                data_content_type='application/json',
            )

            return {
                "message": "successful"
            }


        except grpc.RpcError as err:
            print(f"Error={err.details()}")
            raise HTTPException(status_code=500, detail=err.details())
