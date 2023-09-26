import os
from dataclasses import make_dataclass
import pandas as pd
import io
import base64
import soundfile as sf
import json
from datasets import Dataset


AudioSample = make_dataclass("Point", [("path", str), ("audio", str), ("sentence", str)])


def read_directory(directory_names):
    samples = []

    for directory_name in directory_names:
        for file in [pos_json for pos_json in os.listdir(directory_name) if pos_json.endswith('.json')]:
            json_path = os.path.join(directory_name, file)

            print(json_path)

            samples += read_audio_file(json_path)

    return pd.DataFrame(samples)


def read_audio_file(file_name):
    samples = []

    with open(file_name) as f:
        audio_obj = json.load(f)

        for record in audio_obj:
            if 'score' in record and record['score'] < 0.9:
                continue

            sentence = record['label']
            data, sample_rate = read_audio(record['audio'])

            data_json = json.dumps({
                "path": "",
                "array": data.tolist(),
                "sample_rate": sample_rate
            })

            samples.append(AudioSample("", data_json, sentence))

    return samples


def read_audio(audio_base64_string):
    audio_base64_bytes = audio_base64_string.encode("utf-8")
    audio_bas64 = base64.b64decode(audio_base64_bytes)
    audio_bytes = io.BytesIO(audio_bas64)

    return sf.read(audio_bytes)


if __name__ == "__main__":
    result = read_directory([
        "C:/new_data",
        "C:/Users/P70070113/Documents/GitHub/WebSpeech/alignment/new_test_data"
    ])

    print(result)

    dataset = Dataset.from_pandas(result)

    dataset.save_to_disk("./interview_data")
