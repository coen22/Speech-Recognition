import uvicorn
import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, PlainTextResponse
from datetime import datetime

from recognize import predict_file, predict_file_async, init

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:8080",
    'http://localhost:8000',
    "http://localhost:8001",
    "http://fhmlhsrwks0140.wired.unimaas.local:8001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/ping")
def ping():
    return True


@app.post("/transcribe/{model_id}")
async def transcribe(model_id: str = '1', file: UploadFile = File(...)):
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    print(dt_string, "transcribe()")

    suffix = Path(file.filename).suffix
    with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

        result = await predict_file(tmp_path)

        return result


@app.post("/transcribe_async/{model_id}")
def transcribe_async(model_id: str = '1', file: UploadFile = File(...)):
    print("transcribe_async()")

    tmp_path = save_upload_file_tmp(file)
    return StreamingResponse(predict_file_async(tmp_path), media_type='text/plain')


@app.post("/save_data")
def save_data(file_data: str = Form(...)):
    print("save_datas()")

    suffix = '.json'

    with NamedTemporaryFile(delete=False, suffix=suffix, mode="w", dir="C:/new_data") as tmp:
        tmp.write(file_data)

    return 'success'


# TODO remove file afterwards
def save_upload_file_tmp(upload_file: UploadFile) -> Path:
    try:
        suffix = Path(upload_file.filename).suffix
        with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(upload_file.file, tmp)
            tmp_path = Path(tmp.name)
    finally:
        upload_file.file.close()
    return tmp_path


if __name__ == "__main__":
    init()

    uvicorn.run(app, host="0.0.0.0", port=8000)
