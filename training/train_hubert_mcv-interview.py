import os

from datasets import load_dataset, load_metric, concatenate_datasets, load_from_disk, Sequence, Audio, Features, Value
import torch
import gc
import numpy as np
import json

from transformers import Wav2Vec2FeatureExtractor, Wav2Vec2CTCTokenizer, Wav2Vec2Processor, HubertForCTC, \
    TrainingArguments, Trainer
import librosa
import random
import pandas as pd
from IPython.display import display, HTML
import re
import unidecode
from data_collator import DataCollatorCTCWithPadding
import wandb

cache_dir = "/projects/0/einf2504/cache/"

os.environ['TRANSFORMERS_CACHE'] = cache_dir
os.environ['HF_DATASETS_CACHE'] = cache_dir
os.environ['HF_HOME'] = cache_dir

temp_dir = "/projects/0/einf2504/temp/"

os.environ['TMPDIR'] = temp_dir
os.environ['TEMP'] = temp_dir
os.environ['TMP'] = temp_dir


gc.collect()
torch.cuda.empty_cache()

interview_data = load_from_disk("./interview_data")


model_name = "facebook/hubert-xlarge-ls960-ft"
# model_name = "facebook/hubert-large-ls960-ft"
# model_path = "/projects/0/einf2504/checkpoint-166980-aug-rev1"
model_path = "/projects/0/einf2504/checkpoint-391368-xl"

def convert_json(batch):
    audio = json.loads(batch['audio'])
    audio['array'] = np.array(audio['array']).astype(np.float32)

    batch['audio'] = {
        "path": "test.wav",
        "array": audio['array'],
        "sampling_rate": audio['sampling_rate']
    }

    # remove samples if they do not include a correct sentence
    batch["sentence"] = batch["sentence"] or "[ERROR]"

    return batch


interview_data = interview_data.map(convert_json, features=Features({
                                        "path": Value(dtype='string'),
                                        "audio": Audio(sampling_rate=16_000, decode=True),
                                        "sentence": Value(dtype='string')
                                    }))
interview_data = interview_data.filter(lambda example: example['sentence'] != "[ERROR]")

common_voice_train = load_dataset("mozilla-foundation/common_voice_9_0", "nl", split="train+validation")
common_voice_test = load_dataset("mozilla-foundation/common_voice_9_0", "nl", split="test")

# interview_data = interview_data.remove_columns(
#     ["sampling_rate"])
common_voice_train = common_voice_train.remove_columns(
    ["accent", "age", "client_id", "down_votes", "gender", "locale", "segment", "up_votes"])
common_voice_test = common_voice_test.remove_columns(
    ["accent", "age", "client_id", "down_votes", "gender", "locale", "segment", "up_votes"])

common_voice_train = common_voice_train.cast_column("audio", Audio(sampling_rate=16_000))

# print('common_voice_train.features', common_voice_train.features)
# print('interview_data.features', interview_data.features)
#
# interview_data = interview_data.cast(interview_data.features)

print('common_voice_train.features', common_voice_train.features)
print('interview_data.features', interview_data.features)

common_voice_train = concatenate_datasets([common_voice_train, interview_data])


def show_random_elements(dataset, num_examples=10):
    assert num_examples <= len(dataset), "Can't pick more elements than there are in the dataset."
    picks = []
    for _ in range(num_examples):
        pick = random.randint(0, len(dataset) - 1)
        while pick in picks:
            pick = random.randint(0, len(dataset) - 1)
        picks.append(pick)

    df = pd.DataFrame(dataset[picks])
    display(HTML(df.to_html()))


show_random_elements(common_voice_train)

chars_to_ignore_regex = '[\,\?\.\!\-\;\:\"\“\%\‘\”\�=&\(\)]'


def remove_special_characters(batch):
    try:
        batch["sentence"] = unidecode.unidecode(batch["sentence"])
        batch["sentence"] = re.sub(chars_to_ignore_regex, '', batch["sentence"]).upper() + " "
    except:
        print(batch["sentence"])

    return batch


# interview_data = interview_data.map(remove_special_characters)
common_voice_train = common_voice_train.map(remove_special_characters)
common_voice_test = common_voice_test.map(remove_special_characters)

print(interview_data.features)

tokenizer = Wav2Vec2CTCTokenizer.from_pretrained('facebook/hubert-large-ls960-ft')


def speech_file_to_array_fn(batch):
    batch["speech"] = batch['audio']['array'].astype(np.float32)
    batch["sampling_rate"] = batch['audio']['sampling_rate']
    batch["target_text"] = batch["sentence"]
    return batch


common_voice_train = common_voice_train.map(speech_file_to_array_fn, remove_columns=common_voice_train.column_names)
common_voice_test = common_voice_test.map(speech_file_to_array_fn, remove_columns=common_voice_test.column_names)


def resample(batch):
    if batch["sampling_rate"] != 16_000:
        batch["speech"] = librosa.resample(np.asarray(batch["speech"]),
                                           batch["sampling_rate"], 16_000).astype(np.float32)
    batch["sampling_rate"] = 16_000
    return batch


# interview_data = interview_data.map(resample, num_proc=4)
common_voice_train = common_voice_train.map(resample, num_proc=4)
common_voice_test = common_voice_test.map(resample, num_proc=4)

feature_extractor = Wav2Vec2FeatureExtractor(feature_size=1, sampling_rate=16000, padding_value=0.0, do_normalize=True,
                                             return_attention_mask=True)

processor = Wav2Vec2Processor(feature_extractor=feature_extractor, tokenizer=tokenizer)


def prepare_dataset(batch):
    # check that all files have the correct sampling rate
    assert (
            len(set(batch["sampling_rate"])) == 1
    ), f"Make sure all inputs have the same sampling rate of {processor.feature_extractor.sampling_rate}."

    batch["input_values"] = processor(batch["speech"], sampling_rate=batch["sampling_rate"][0]).input_values

    with processor.as_target_processor():
        try:
            batch["labels"] = processor(batch["target_text"]).input_ids
        except:
            batch["labels"] = processor("").input_ids
            print("FAILED:", batch["target_text"])

    return batch


common_voice_train = common_voice_train.map(prepare_dataset, remove_columns=common_voice_train.column_names,
                                            batch_size=8, num_proc=4, batched=True)
common_voice_test = common_voice_test.map(prepare_dataset, remove_columns=common_voice_test.column_names, batch_size=8,
                                          num_proc=4, batched=True)

data_collator = DataCollatorCTCWithPadding(processor=processor, padding=True)

wer_metric = load_metric("wer")
cer_metric = load_metric("cer")


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


model = HubertForCTC.from_pretrained(
    model_path or model_name,
    attention_dropout=0.1,
    hidden_dropout=0.1,
    feat_proj_dropout=0.0,
    mask_time_prob=0.05,
    layerdrop=0.1,
    ctc_loss_reduction="mean",
    pad_token_id=processor.tokenizer.pad_token_id,
    vocab_size=len(processor.tokenizer)
)

model.freeze_feature_extractor()

wandb.login()

wandb.init(project="hubert-mcv-xlarge-aug", entity="coen22")

training_args = TrainingArguments(
    output_dir="hubert-mcv-xlarge-aug-cgn",
    per_device_train_batch_size=2,
    per_device_eval_batch_size=2,
    group_by_length=True,
    gradient_accumulation_steps=2,
    num_train_epochs=40,
    fp16=True,
    save_steps=500,
    eval_steps=500,
    evaluation_strategy="steps",
    logging_steps=400,
    learning_rate=3e-5,
    warmup_steps=500,
    save_total_limit=2,
    report_to="wandb"
)

torch.cuda.empty_cache()

trainer = Trainer(
    model=model,
    data_collator=data_collator,
    args=training_args,
    compute_metrics=compute_metrics,
    train_dataset=common_voice_train,
    eval_dataset=common_voice_test,
    tokenizer=processor.feature_extractor,
)

trainer.train()

wandb.finish()
