import ray
from ray.train.torch import TorchTrainer
from ray.air.config import ScalingConfig
import ray.train.huggingface.transformers
from datasets import load_dataset
from transformers import WhisperTokenizer, WhisperForConditionalGeneration, WhisperProcessor, TrainingArguments, Trainer as HFTrainer
import torch

# Initialize Ray
ray.init()

# Load the Whisper tokenizer and processor
tokenizer = WhisperTokenizer.from_pretrained("openai/whisper-tiny")
processor = WhisperProcessor.from_pretrained("openai/whisper-tiny")

# Define a preprocessing function
def preprocess_function(examples):
    inputs = processor(examples["audio"]["array"], sampling_rate=16000, return_tensors="pt").input_features
    targets = processor.tokenizer(examples["sentence"], return_tensors="pt", padding="max_length", max_length=448, truncation=True).input_ids
    return {"input_features": inputs.squeeze(0), "labels": targets.squeeze(0)}

# Define the training function
def train_function():
    # Load and preprocess the dataset inside the train function
    dataset = load_dataset("mozilla-foundation/common_voice_11_0", "de", split={"train": "train[:1000]", "validation": "validation[:1000]"}, trust_remote_code=True)
    encoded_train_dataset = dataset["train"].map(preprocess_function, remove_columns=["audio", "sentence"])
    encoded_validation_dataset = dataset["validation"].map(preprocess_function, remove_columns=["audio", "sentence"])

    model = WhisperForConditionalGeneration.from_pretrained("openai/whisper-tiny")

    # Configuration parameters for TrainingArguments
    training_args = TrainingArguments(
        output_dir="./results",
        per_device_train_batch_size=16,  # Adjust based on your resources
        per_device_eval_batch_size=72,   # Adjust based on your resources
        evaluation_strategy="epoch",
        learning_rate=2e-5,
        weight_decay=0.01,
        num_train_epochs=3,
        save_steps=10_000,
        save_total_limit=2,
        logging_dir="./logs",
        logging_steps=200,
        fp16=True
    )

    trainer = HFTrainer(
        model=model,
        args=training_args,
        train_dataset=encoded_train_dataset,
        eval_dataset=encoded_validation_dataset,
    )

    trainer = ray.train.huggingface.transformers.prepare_trainer(trainer)

    trainer.train()
    model.save_pretrained("./fine-tuned-whisper")
    tokenizer.save_pretrained("./fine-tuned-whisper")
    print("Training complete and model saved.")

# Define the Ray Train configuration
scaling_config = ScalingConfig(
    num_workers=5,  # Number of workers
    use_gpu=True,   # Use GPU
)

# Setup the Ray Train Trainer
trainer = TorchTrainer(
    train_loop_per_worker=train_function,
    scaling_config=scaling_config,
)

# Run the training
trainer.fit()
