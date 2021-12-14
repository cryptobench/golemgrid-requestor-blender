import time
from pydantic import BaseModel
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, File, Form, UploadFile
import os
import subprocess
import requests

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/ready", status_code=200)
async def ping():
    return


@app.post("/files/")
async def receive_file(scene_file: UploadFile = File(...)):
    file_location = f"/requestor/scene/{scene_file.filename}"
    with open(file_location, "wb+") as file_object:
        file_object.write(scene_file.file.read())
    return {"stored_at": file_location}


@app.post("/params/")
async def receive_file(params: UploadFile = File(...)):
    file_location = f"/requestor/{params.filename}"
    with open(file_location, "wb+") as file_object:
        file_object.write(params.file.read())
    with open('/requestor/data.config') as f:
        for line in f:
            command = line
    proc = subprocess.Popen(command, shell=True)
    proc.wait()
    return {"stored_at": file_location}

taskid = os.getenv("TASKID")
url = f"http://container-manager-api:8003/v1/container/ping/ready/{taskid}"
r = requests.get(url)
