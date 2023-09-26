import json
import asyncio
import os
import re
from os.path import exists

import numpy as np
import pandas as pd
import textract

predictions_prefix = "C:/Users/P70070113/data/predictions/"
predictions_suffix = ".json"
alignment_prefix = "./new_test_data/"
alignment_suffix = ".json"
transcript_prefix = "C:/Users/P70070113/data/transcripts/"
transcript_suffix = ".doc"


def print_info(array):
    print("median=", np.quantile(array, 0.5), ",", sep="")
    print("lower quartile=", np.quantile(array, 0.25), ",", sep="")
    print("upper quartile=", np.quantile(array, 0.75), ",", sep="")
    print("lower whisker=", np.amin(array), ",", sep="")
    print("upper whisker=", np.amax(array), sep="")


async def main():
    transcript_files = os.listdir(alignment_prefix)
    files_sorted_by_size = sorted(transcript_files, key=lambda filename: os.path.getsize(os.path.join(alignment_prefix, filename)))

    name_df = []
    alignments_df = []
    predictions_df = []
    ratios_df = []
    type_df = []

    obj_list = []

    for file in files_sorted_by_size:
        alignment_path = alignment_prefix + file
        predictions_path = predictions_prefix + file
        transcript_path = transcript_prefix + file.split(".")[0] + transcript_suffix

        text = textract.process(transcript_path).decode("utf-8")
        text_sub = re.sub("[\t \n]+[ \t]+", " ", text).lower()

        # skip Limburgish fragments
        if "|nederlands" not in text_sub:
            continue

        type = "-"
        if "aan uw leven" in text_sub or "van uw leven" in text_sub or "wat doet u dan" in text_sub:
            type = "R"
        elif "contact met de zorgverlener" in text_sub or "uw moeder" in text_sub:
            type = "F"
        elif "contact met familie" in text_sub or "contact met de familie" in text_sub:
            type = "Z"

        if type == "-":
            # print(text)
            continue

        print(transcript_path, type)

        with open(alignment_path, "r") as f:
            alignments = json.load(f)

        with open(predictions_path, "r") as f:
            predictions = json.load(f)

        alignment_score = 0
        segments_used_for_training = 0

        for alignment in alignments:
            alignment_score += alignment['score']
            if alignment['score'] > 0.9:
                segments_used_for_training += 1

        alignment_score /= len(predictions)

        name_df.append(file.split(".")[0])
        alignments_df.append(len(alignments))
        predictions_df.append(len(predictions))
        ratios_df.append(alignment_score)
        type_df.append(type)

        data = {
            'name': file.split(".")[0],
            'alignments': len(alignments),
            'segments': len(predictions),
            'ratio': alignment_score,
            "segments_used_for_training": segments_used_for_training,
            'type': type
        }

        obj_list.append(data)

    d = {
        'name': name_df,
        'alignments': alignments_df,
        'segments': predictions_df,
        'ratio': ratios_df,
        'type': type_df
    }

    df = pd.DataFrame(data=d)
    print(df)

    residents = [obj['ratio'] for obj in obj_list if obj['type'] == "R"]
    print_info(residents)

    residents = [obj['ratio'] for obj in obj_list if obj['type'] == "F"]
    print_info(residents)

    residents = [obj['ratio'] for obj in obj_list if obj['type'] == "Z"]
    print_info(residents)

    residents = [obj['segments_used_for_training'] for obj in obj_list]
    print(np.sum(residents))

    residents = [obj['segments'] for obj in obj_list]
    print(np.sum(residents))

if __name__ == "__main__":
    asyncio.run(main())
