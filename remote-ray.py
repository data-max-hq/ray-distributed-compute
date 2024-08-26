import ray
import torch
from datasets import load_dataset
from transformers import WhisperForConditionalGeneration, WhisperProcessor, Trainer, TrainingArguments
import boto3
import os

# Initialize Ray
ray.init(address="auto")

# Define the preprocessing function
@ray.remote(num_cpus=8)
def preprocess_data():
    dataset = load_dataset("mozilla-foundation/common_voice_11_0", "de", split="train+validation", trust_remote_code=True)
    dataset = dataset.select(range(1000))

    processor = WhisperProcessor.from_pretrained("openai/whisper-tiny")

    def preprocess_function(examples):
        inputs = processor(examples["audio"]["array"], sampling_rate=16000, return_tensors="pt").input_features
        targets = processor.tokenizer(examples["sentence"], return_tensors="pt", padding="max_length", max_length=448, truncation=True).input_ids
        return {"input_features": inputs.squeeze(0), "labels": targets.squeeze(0)}

    dataset = dataset.map(preprocess_function, remove_columns=["audio", "sentence"])
    dataset = ray.put(dataset)
    return dataset

# Define the fine-tuning function
@ray.remote(num_gpus=1)
def train_and_upload_model(preprocessed_dataset, s3_model_path):
    processor = WhisperProcessor.from_pretrained("openai/whisper-tiny")
    model = WhisperForConditionalGeneration.from_pretrained("openai/whisper-tiny")

    training_args = TrainingArguments(
        output_dir="./results",
        per_device_train_batch_size=24,
        gradient_accumulation_steps=8,
        num_train_epochs=3,
        logging_dir="./logs",
        logging_steps=10,
        save_steps=500,
        save_total_limit=2,
        fp16=True,
        report_to="none"
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=preprocessed_dataset,
    )

    trainer.train()

    model_save_path = "./trained_whisper_model"
    trainer.save_model(model_save_path)

    s3 = boto3.client('s3')
    bucket_name = "raybucket-test"
    for root, dirs, files in os.walk(model_save_path):
        for file in files:
            local_path = os.path.join(root, file)
            s3_path = os.path.join(s3_model_path, file)
            s3.upload_file(local_path, bucket_name, s3_path)
    
    return f"s3://{bucket_name}/{s3_model_path}"

s3_model_path = "output_dir/"

preprocessed_dataset_ref = preprocess_data.remote()
train_result_ref = train_and_upload_model.remote(preprocessed_dataset_ref, s3_model_path)

s3_model_location = ray.get(train_result_ref)
print(f"Model uploaded to: {s3_model_location}")

ray.shutdown()
