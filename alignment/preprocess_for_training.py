import json
import asyncio
import os
import traceback
from os.path import exists

import textract
from alignment import align_text
from recognize import predict_file

audio_prefix = "C:/Users/P70070113/data/audio/"
audio_suffix = ".mp3"
transcript_prefix = "C:/Users/P70070113/data/transcripts/"
transcript_suffix = ".doc"
predictions_prefix = "C:/Users/P70070113/data/predictions/"
predictions_suffix = ".json"


async def process(name, audio_path, transcript_path):
    text = textract.process(transcript_path).decode("utf-8")

    file_path = predictions_prefix + name + predictions_suffix

    if exists(file_path):
        with open(file_path, "r") as f:
            predictions = json.load(f)
    else:
        predictions = await predict_file(audio_path)
        with open(file_path, "w") as f:
            json.dump(predictions, f)

    text_predictions = [x['label'] for x in predictions]
    accuracies, sentences, guesses = align_text(text, text_predictions)

    if len(sentences) != len(predictions):
        raise ValueError("Lengths are not the same")

    correct_predictions = []
    for i in range(len(predictions)):
        if sentences[i] != "":
            correct_predictions.append({
                "audio": predictions[i]['audio'],
                "label": sentences[i],
                "score": accuracies[i]
            })

    return correct_predictions


async def process_file(name, audio_path, transcript_path, offline=True):
    try:
        if not exists("./new_test_data/" + name + ".json"):
            result = await process(name, audio_path, transcript_path)

            if result is not None and len(result) > 0:
                with open("./new_test_data/" + name + ".json", "w") as f:
                    json.dump(result, f)
    except Exception as e:
        print("Processing", name, "has failed")
        traceback.print_exc()


async def main():

    files = []

    transcript_files = os.listdir(transcript_prefix)
    files_sorted_by_size = sorted(transcript_files, key=lambda filename: os.path.getsize(os.path.join(transcript_prefix, filename)))

    for file in files_sorted_by_size:
        if not file.startswith("~$") and file.endswith(".doc"):
            files.append(file.split(".")[0])

    print("")
    print(files)
    print("")

    for file in files:
        print("Processing file:", file)

        audio_path = audio_prefix + file + audio_suffix
        transcript_path = transcript_prefix + file + transcript_suffix
        await process_file(file, audio_path, transcript_path)


if __name__ == "__main__":
    asyncio.run(main())
