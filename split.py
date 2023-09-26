from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
from pydub import AudioSegment
import librosa

MAX_LENGTH = 160_000
OPT_LENGTH = 30_000

FRAME_LENGTH_DECAY = 0.8
HOP_LENGTH_DECAY = 0.5

START_HOP_LENGTH = 128
MIN_HOP = 64

SEQ_LENGTH = 8_192
MIN_SEQ_LENGTH = 2_048


def segment(filename="test_data/seq_pauze.mp3"):
    suffix = Path(filename).suffix

    if suffix == ".mp3":
        with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = Path(tmp.name)

            # convert wav to mp3
            aud_seg = AudioSegment.from_mp3(filename)
            aud_seg.export(tmp_path, format="wav")

            audio, _ = librosa.load(tmp_path, sr=16000)
    else:
        audio, _ = librosa.load(filename, sr=16000)

    return segment_wave(audio)


def segment_wave(audio):
    runs = librosa.effects.split(audio, top_db=50, frame_length=MIN_SEQ_LENGTH, hop_length=MIN_HOP)
    runs = list(runs)

    while True:
        if np.all([x[1] - x[0] > OPT_LENGTH for x in runs]):
            break

        silences = [b[0] - a[1] for a, b in zip(runs[:-1], runs[1:])]
        shortest_silence_idx = np.argsort(silences)

        success = False
        for silence_idx in shortest_silence_idx:
            a = runs[silence_idx]
            b = runs[silence_idx + 1]

            if b[1] - a[0] < MAX_LENGTH:
                runs[silence_idx][1] = runs[silence_idx + 1][1]
                del runs[silence_idx + 1]
                success = True
                break

        if not success:
            print("not optimal")
            break

    chunks = []

    for run in runs:
        seg = audio[run[0]:run[1]]

        if run[1] - run[0] > MAX_LENGTH:
            chunks.append(segment_wave_recursive(seg, frame_length=SEQ_LENGTH, hop_length=START_HOP_LENGTH))
        else:
            chunks.append(seg)

    return chunks


def segment_wave_recursive(audio, frame_length=SEQ_LENGTH, hop_length=START_HOP_LENGTH):
    runs = librosa.effects.split(audio, top_db=30, frame_length=frame_length, hop_length=hop_length)

    chunks = []

    for run in runs:
        split = audio[run[0]:run[1]]

        if run[1] - run[0] < MAX_LENGTH or (hop_length <= MIN_HOP and frame_length <= MIN_SEQ_LENGTH):
            if frame_length >= MIN_SEQ_LENGTH:
                chunks.append(split)
        elif frame_length > MIN_SEQ_LENGTH and hop_length <= MIN_HOP:

            chunks.extend(segment_wave_recursive(split, int(frame_length * FRAME_LENGTH_DECAY), MIN_HOP))
        else:
            chunks.extend(segment_wave_recursive(split, frame_length, int(hop_length * HOP_LENGTH_DECAY)))

    return chunks


if __name__ == "__main__":
    print(len(segment()))
