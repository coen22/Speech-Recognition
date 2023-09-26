import os
import re
import librosa
import numpy as np
import unidecode
from datasets import load_dataset, load_metric
from transformers import HubertForCTC, Wav2Vec2FeatureExtractor, Wav2Vec2Processor, Wav2Vec2CTCTokenizer, Trainer, \
    TrainingArguments, WavLMForCTC, AutoModel

os.environ["WANDB_DISABLED"] = "true"

chars_to_ignore_regex = '[\,\?\.\!\-\;\:\"\“\%\‘\”\�=&\(\)]'

model_name = "../models/checkpoint-31500-161-20-07"

wer_metric = load_metric("wer")
cer_metric = load_metric("cer")

tokenizer = Wav2Vec2CTCTokenizer.from_pretrained("facebook/hubert-large-ls960-ft")

feature_extractor = Wav2Vec2FeatureExtractor(feature_size=1, sampling_rate=16000, padding_value=0.0,
                                             do_normalize=True,
                                             return_attention_mask=True)

processor = Wav2Vec2Processor(feature_extractor=feature_extractor, tokenizer=tokenizer)

model = HubertForCTC.from_pretrained(model_name)

def remove_special_characters(batch):
    try:
        batch["sentence"] = unidecode.unidecode(batch["sentence"])
        batch["sentence"] = re.sub(chars_to_ignore_regex, '', batch["sentence"]).upper() + " "
    except:
        print(batch["sentence"])

    return batch


def speech_file_to_array_fn(batch):
    audio, sr = librosa.load(batch['path'], sr=16_000)
    batch["speech"] = audio
    batch["sampling_rate"] = sr
    batch["target_text"] = batch["sentence"]
    return batch


def resample(batch):
    if batch["sampling_rate"] != 16_000:
        batch["speech"] = librosa.resample(np.asarray(batch["speech"]),
                                           batch["sampling_rate"], 16_000).astype(np.float32)
    batch["sampling_rate"] = 16_000
    return batch


def prepare_dataset(batch):
    # check that all files have the correct sampling rate
    assert (
            len(set(batch["sampling_rate"])) == 1
    ), f"Make sure all inputs have the same sampling rate of {processor.feature_extractor.sampling_rate}."

    batch["input_values"] = processor(batch["speech"], sampling_rate=batch["sampling_rate"][0],
                                      max_length=1024, padding=True).input_values

    with processor.as_target_processor():
        try:
            batch["labels"] = processor(batch["target_text"], max_length=1024, padding=True).input_ids
        except:
            batch["labels"] = processor("").input_ids
            print("FAILED:", batch["target_text"])

    return batch


def compute_metrics(pred):
    pred_logits = pred.predictions
    pred_ids = np.argmax(pred_logits, axis=-1)

    pred.label_ids[pred.label_ids == -100] = processor.tokenizer.pad_token_id

    pred_str = processor.batch_decode(pred_ids)
    # we do not want to group tokens when computing the metrics
    label_str = processor.batch_decode(pred.label_ids, group_tokens=False)

    wer = wer_metric.compute(predictions=pred_str, references=label_str)
    cer = cer_metric.compute(predictions=pred_str, references=label_str)

    return {"wer": wer, "cer": cer}


if __name__ == "__main__":
    common_voice_test = load_dataset("mozilla-foundation/common_voice_6_1", "nl", split="test", use_auth_token=True)

    common_voice_test = common_voice_test.remove_columns(
        ["accent", "age", "client_id", "down_votes", "gender", "locale", "segment", "up_votes"])

    common_voice_test = common_voice_test.map(remove_special_characters)

    common_voice_test = common_voice_test.map(speech_file_to_array_fn, remove_columns=common_voice_test.column_names)

    common_voice_test = common_voice_test.map(resample, num_proc=4)

    common_voice_test = common_voice_test.map(prepare_dataset, remove_columns=common_voice_test.column_names,
                                              batch_size=8, num_proc=4, batched=True)

    training_args = TrainingArguments(
        output_dir="hubert-nl-mcv-large-aug-fixed",
        per_device_eval_batch_size=2,
        group_by_length=True,
        fp16=True,
        eval_steps=500,
        evaluation_strategy="epoch"
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        compute_metrics=compute_metrics,
        eval_dataset=common_voice_test,
        tokenizer=processor.feature_extractor
    )

    result = trainer.evaluate(common_voice_test)

    print(result)