import json
import os
import re
import traceback

import pandas as pd
import swalign

predictions_suffix = ".json"
alignment_prefix = "C:/Users/P70070113/Documents/Github/WebSpeech/alignment/new_test_data/"

match = 1
mismatch = -1
scoring = swalign.NucleotideScoringMatrix(match, mismatch)
nw = swalign.LocalAlignment(scoring, globalalign=True)


def cigar_to_ints(cigar_str):
    insertions = 0
    substitutions = 0
    deletions = 0
    matches = 0

    search = re.findall(r'[0-9]*[A-Z]', cigar_str)
    for el in search:
        num = int(el[:-1])
        op = el[-1]

        if op == "D":
            deletions += num
        elif op == "I":
            insertions += num
        elif op == "X":
            substitutions += num
        elif op == "M":
            matches += num

    return {
        "insertions": insertions,
        "substitutions": substitutions,
        "deletions": deletions,
        "matches": matches
    }


def process_file(file_without_ext, align_path):
    print(align_path)

    insertions = 0
    substitutions = 0
    deletions = 0
    matches = 0

    insertions_r = 0
    substitutions_r = 0
    deletions_r = 0
    matches_r = 0

    insertions_f = 0
    substitutions_f = 0
    deletions_f = 0
    matches_f = 0

    insertions_z = 0
    substitutions_z = 0
    deletions_z = 0
    matches_z = 0

    with open(align_path, "r") as f:
        alignments = json.load(f)

    for el in alignments:
        dists = nw.align(el['label'], el['predicted_label'])

        result = cigar_to_ints(dists.extended_cigar_str)

        insertions += result['insertions']
        substitutions += result['substitutions']
        deletions += result['deletions']
        matches += result['matches']

        if el['type'] == 'R':
            insertions_r += result['insertions']
            substitutions_r += result['substitutions']
            deletions_r += result['deletions']
            matches_r += result['matches']
        elif el['type'] == 'F':
            insertions_f += result['insertions']
            substitutions_f += result['substitutions']
            deletions_f += result['deletions']
            matches_f += result['matches']
        elif el['type'] == 'Z':
            insertions_z += result['insertions']
            substitutions_z += result['substitutions']
            deletions_z += result['deletions']
            matches_z += result['matches']

    return {
        "insertions": insertions,
        "substitutions": substitutions,
        "deletions": deletions,
        "matches": matches,

        "insertions_r": insertions_r,
        "substitutions_r": substitutions_r,
        "deletions_r": deletions_r,
        "matches_r": matches_r,

        "insertions_f": insertions_f,
        "substitutions_f": substitutions_f,
        "deletions_f": deletions_f,
        "matches_f": matches_f,

        "insertions_z": insertions_z,
        "substitutions_z": substitutions_z,
        "deletions_z": deletions_z,
        "matches_z": matches_z
    }


if __name__ == "__main__":
    files = []

    audio_files = os.listdir(alignment_prefix)
    audio_sorted_by_size = sorted(audio_files, key=lambda filename: os.path.getsize(os.path.join(alignment_prefix, filename)))

    print(audio_sorted_by_size)

    for file in audio_sorted_by_size:
        file = file.lower()
        if not file.startswith("~$") and file.endswith(predictions_suffix):
            files.append(file)

    print("")
    print(files)
    print("")

    insertions = 0
    substitutions = 0
    deletions = 0
    matches = 0

    insertions_r = 0
    substitutions_r = 0
    deletions_r = 0
    matches_r = 0

    insertions_f = 0
    substitutions_f = 0
    deletions_f = 0
    matches_f = 0

    insertions_z = 0
    substitutions_z = 0
    deletions_z = 0
    matches_z = 0

    for file in files:
        print("Processing file:", file)

        try:
            file_without_ext = os.path.splitext(file)[0]
            align_path = alignment_prefix + file_without_ext + predictions_suffix

            result = process_file(file_without_ext, align_path)

            insertions += result['insertions']
            substitutions += result['substitutions']
            deletions += result['deletions']
            matches += result['matches']

            insertions_r += result['insertions_r']
            substitutions_r += result['substitutions_r']
            deletions_r += result['deletions_r']
            matches_r += result['matches_r']

            insertions_f += result['insertions_f']
            substitutions_f += result['substitutions_f']
            deletions_f += result['deletions_f']
            matches_f += result['matches']

            insertions_z += result['insertions_z']
            substitutions_z += result['substitutions_z']
            deletions_z += result['deletions_z']
            matches_z += result['matches_z']
        except:
            print("Processing", file, "has failed")
            traceback.print_exc()

    total = insertions + substitutions + deletions
    total_r = insertions_r + substitutions_r + deletions_r
    total_f = insertions_f + substitutions_f + deletions_f
    total_z = insertions_z + substitutions_z + deletions_z

    pd_dict = {
        "total": [
            round(insertions / total * 100, 2),
            round(substitutions / total * 100, 2),
            round(deletions / total * 100, 2),
        ],

        "resident": [
            round(insertions_r / total_r * 100, 2),
            round(substitutions_r / total_r * 100, 2),
            round(deletions_r / total_r * 100, 2)
        ],

        "family": [
            round(insertions_f / total_f * 100, 2),
            round(substitutions_f / total_f * 100, 2),
            round(deletions_f / total_f * 100, 2)
        ],

        "care_professional": [
            round(insertions_z / total_f * 100, 2),
            round(substitutions_z / total_f * 100, 2),
            round(deletions_z / total_f * 100, 2)
        ]
    }

    print(pd_dict)

    columns = ['insertions', 'substitutions', 'deletions']

    df = pd.DataFrame(pd_dict, columns=columns)

    print(df.to_markdown(index=False))