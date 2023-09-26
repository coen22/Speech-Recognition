import json
import traceback

import swalign
import re

import textract
from num2words import num2words

match_score = 1
mismatch_score = -20
scoring = swalign.NucleotideScoringMatrix(match_score, mismatch_score)
sw = swalign.LocalAlignment(scoring, gap_penalty=-1, gap_extension_penalty=-1)


WINDOW_SIZE = 0.75
MIN_ACCURACY = 0.0
MIN_LENGTH_DIFF = 0.0


def replace_numbers(text):
    split = re.split(r'(\d+)', text)

    for i in range(len(split)):
        if split[i].isnumeric():
            split[i] = num2words(split[i], lang='nl')

    text = ' '.join(split)

    return re.sub(r'  +', " ", text)


def preprocess(transcript_text):
    # make lower case
    transcript_text = transcript_text.lower()

    # remove speaker information (e.g. 'SP1', 'Z:')
    transcript_text = re.sub(r'\w+[0-9:]', " ", transcript_text)

    # remove irrelevant characters
    transcript_text = re.sub(r'[:|.?!\r\n \[\]\-]+', " ", transcript_text)

    # change numbers into words
    transcript_text = replace_numbers(transcript_text)

    # other mismatch fixes
    transcript_text = re.sub(r'\bst\b', "sint", transcript_text)  # (e.g. st anna -> sint anna)

    return transcript_text


# choose your own values here… 2 and -1 are common.
def align_text(transcript_text, guesses):
    transcript_text = preprocess(transcript_text)

    accuracies = []
    sentences = []

    transcript_length = len(transcript_text)

    for i in range(len(guesses)):
        guess = guesses[i]

        # skip very short sequences (as these may result in error)
        if guess is None or len(guess) < 15:
            accuracies.append(0)
            sentences.append("")
            continue

        try:
            # limit the search window
            search_window_min = i / len(guesses) - WINDOW_SIZE
            search_window_min = max(0, int(search_window_min * transcript_length))
            search_window_max = i / len(guesses) + WINDOW_SIZE
            search_window_max = min(transcript_length - 1, int(search_window_max * transcript_length))
            search_window = transcript_text[search_window_min:search_window_max]

            alignment = sw.align(search_window, guess)
            match = search_window[alignment.r_pos:alignment.r_end]

            if match is None or len(match) < 2:
                sentences.append("")
                continue

            prefix = ''
            prefix_match = re.search(r"\w", match[0])
            prefix_search = re.search(r"\w", transcript_text[alignment.r_pos + search_window_min - 1])
            # print(match[0], transcript_text[alignment.r_pos + search_window_min - 1])
            if bool(prefix_match) and bool(prefix_search):
                words = transcript_text[0:alignment.r_pos + search_window_min].split()
                prefix = words[-1]

            suffix = ''
            suffix_match = re.search(r"\w", match[-1])
            suffix_search = re.search(r"\w", transcript_text[alignment.r_end + search_window_min])
            # print(match[-1], transcript_text[alignment.r_end + search_window_min])
            if bool(suffix_match) and bool(suffix_search):
                words = transcript_text[alignment.r_end + search_window_min:].split()
                suffix = words[0]

            sentence = (prefix + match + suffix).strip()

            # print(sentence)

            accuracies.append(alignment.identity)

            if alignment.identity > MIN_ACCURACY and len(sentence) >= len(guess) * MIN_LENGTH_DIFF:
                sentences.append(sentence)
                transcript_text = transcript_text.replace(sentence, "")
            else:
                sentences.append("")

        except:
            sentences.append("")
            traceback.print_exc()

    return accuracies, sentences, guesses


if __name__ == "__main__":
    transcript_path = "C:/Users/P70070113/data/transcripts/747.doc"
    predictions_path = "C:/Users/P70070113/data/predictions/747.json"

    text = textract.process(transcript_path).decode("utf-8")

    with open(predictions_path, "r") as f:
        predictions = json.load(f)
    text_predictions = [x['label'] for x in predictions]

    for x in align_text(text, text_predictions)[1]:
        print(x)
