import asyncio
import base64
import heapq
import math
from numpy import array
import numpy as np
import soundfile as sf
import torch.nn.functional
import torch
import os
import json
from math import log

from scipy.io import wavfile
from transformers import (
    HubertForCTC,
    Wav2Vec2Processor,
    RobertaForMaskedLM,
    RobertaTokenizer
)
from split import segment
from tempfile import NamedTemporaryFile

lm_name = "pdelobelle/robbert-v2-dutch-base"
tokenizer_name = "facebook/hubert-large-ls960-ft"
model_name = "coen22/Speech-Recognition-AWO-L"

dirname = os.path.dirname(__file__)
model_path = os.path.join(dirname, model_name)

beam_size = 30
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

working = False

processor: Wav2Vec2Processor = None
model:HubertForCTC = None
tokenizer:RobertaTokenizer = None
lm_model:RobertaForMaskedLM = None


def init():
    global processor
    global model
    global tokenizer
    global lm_model

    print("Loading am")

    processor = Wav2Vec2Processor.from_pretrained(tokenizer_name)
    model = HubertForCTC.from_pretrained(model_path).to(device)

    print("Loading lm")

    tokenizer = RobertaTokenizer.from_pretrained(lm_name)
    lm_model = RobertaForMaskedLM.from_pretrained(lm_name)

    print("Done")


# lm prob function
def lm_prob(sentence):
    if tokenizer is None:
        init()

    tokenize_input = tokenizer(sentence, return_tensors='pt')
    output = lm_model(**tokenize_input)
    loss_fct = torch.nn.CrossEntropyLoss()
    loss = loss_fct(output.logits.squeeze(),tokenize_input.input_ids.squeeze()).data
    return loss.item()


# beam search
def beam_search_decoder(data, k):
    """
    data: (n, m) where n is number of words in sequence.
        and m is number of classes (words in target vocab).
    k: beam search parameter
    """
    sequences = [[[], 0.0]]
    # walk over each step in sequence
    for row in data: # ----> n
        all_candidates = []

        # find the indexes of k largest probabilities in the row
        k_largest = heapq.nlargest(k, range(len(row)), row.take) # -----> m

        # expand each current candidate
        for seq, score in sequences: # ----> k
            for j in k_largest: # -----> k
                s = score - math.log(row[j])
                candidate = [seq + [j], s]
                all_candidates.append(candidate)

        # sort all candidates by score
        ordered = sorted(all_candidates, key=lambda tup:tup[1]) # -----> k log k

        # select best k
        sequences = ordered[:k]

    return sequences


def predict(audio, sampling_rate=16000):
    if len(audio) > 160_000:
        # TODO split further
        return '<too long segment>'

    tokens = processor(audio, sampling_rate=sampling_rate, return_tensors='pt').to(device)

    # Store logits (non-normalized predictions)
    logits = model(tokens.input_values, tokens.attention_mask).logits

    # normalize
    min_range = torch.min(logits)
    max_range = torch.max(logits)
    logits = (logits - min_range) / (max_range - min_range)

    logits = array(logits[0].cpu().detach().numpy())

    # print(logits)

    # Store predicted id's
    # predicted_ids = torch.argmax(logits, dim=-1)
    predicted_ids = beam_search_decoder(logits, beam_size)

    # decode the audio to generate text
    with processor.as_target_processor():
        scores = []
        transcriptions = []

        for predicted_id in predicted_ids:
            transcription = processor.decode(predicted_id[0])
            # print(transcription)
            lm_score = lm_prob(transcription)
            scores.append(0.5 * lm_score + 0.5 * predicted_id[1])
            transcriptions.append(transcription)

    best_idx = np.argmax(scores)

    # print("best id = ", best_idx)

    if transcriptions[best_idx] != '':
        return transcriptions[best_idx]


async def predict_file(filename="test_data/seq_pauze.wav"):
    global working

    if working:
        print("Waiting for other task")
        await asyncio.sleep(5)

    working = True

    if tokenizer is None:
        init()

    output = []

    for seg in segment(filename):

        # print("len", len(seg))

        if len(seg) < 2_048:
            print("Too short")
            continue

        torch_arr = torch.FloatTensor(seg)
        label = predict(torch_arr)

        try:
            with NamedTemporaryFile(delete=True, suffix=".wav", mode="wb+") as f:
                sf.write(f, seg, 16_000)

                f.seek(0)

                # print(label)

                output.append({
                    "audio": base64.b64encode(f.read()).decode("utf-8"),
                    "label": label
                })
        except:
            print("Failed to add file")

    working = False

    return output


async def predict_file_async(filename="test_data/seq_pauze.wav"):
    for seg in segment(filename):

        print("len", len(seg))

        if len(seg) < 2_048:
            print("Too short")
            continue

        torch_arr = torch.FloatTensor(seg)
        label = predict(torch_arr)

        with NamedTemporaryFile(delete=True, suffix=".wav", mode="wb+") as f:
            sf.write(f, seg, 16_000)

            f.seek(0)

            print(label)

            yield json.dumps({
                "audio": base64.b64encode(f.read()).decode("utf-8"),
                "label": label
            })


async def main():
    result = await predict_file()
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
