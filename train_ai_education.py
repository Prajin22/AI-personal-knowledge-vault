#!/usr/bin/env python3
"""
AI Education Model Training Pipeline
Fine-tune BlenderBot for educational conversations using LoRA
"""

import json
import torch
from pathlib import Path
from typing import List, Dict, Optional
import logging
from transformers import (
    BlenderbotTokenizer,
    BlenderbotForConditionalGeneration,
    TrainingArguments,
    Trainer,
    DataCollatorForSeq2Seq
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from datasets import Dataset
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIEducationTrainer:
    """Fine-tune BlenderBot for AI/ML educational conversations"""

    def __init__(self, model_name: str = "facebook/blenderbot-400M-distill"):
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        self.lora_config = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        logger.info(f"Using device: {self.device}")

    def load_model(self):
        """Load the base model and tokenizer"""
        logger.info(f"Loading {self.model_name}...")

        self.tokenizer = BlenderbotTokenizer.from_pretrained(self.model_name)
        self.model = BlenderbotForConditionalGeneration.from_pretrained(
            self.model_name,
            torch_dtype=torch.float16 if self.device.type == "cuda" else torch.float32,
            device_map="auto" if self.device.type == "cuda" else None,
        )

        # Add special tokens for educational context
        special_tokens = {
            "additional_special_tokens": [
                "[EXPLAIN]", "[EXAMPLE]", "[CONCEPT]", "[PREREQUISITE]",
                "[FORMULA]", "[ALGORITHM]", "[APPLICATION]", "[QUIZ]"
            ]
        }
        self.tokenizer.add_special_tokens(special_tokens)
        self.model.resize_token_embeddings(len(self.tokenizer))

        logger.info("Model loaded successfully")

    def setup_lora(self):
        """Configure LoRA for efficient fine-tuning"""
        logger.info("Setting up LoRA configuration...")

        self.lora_config = LoraConfig(
            r=16,  # Low-rank adaptation dimension
            lora_alpha=32,  # Scaling parameter
            target_modules=["q_proj", "v_proj", "k_proj", "out_proj"],  # Attention layers
            lora_dropout=0.05,  # Dropout for LoRA layers
            bias="none",
            task_type="SEQ_2_SEQ_LM",  # BlenderBot is sequence-to-sequence
        )

        # Prepare model for LoRA training
        self.model = prepare_model_for_kbit_training(self.model)
        self.model = get_peft_model(self.model, self.lora_config)

        # Print trainable parameters info
        self.model.print_trainable_parameters()

    def load_training_data(self, data_dir: str = "data/training_data") -> Dataset:
        """Load and preprocess training data"""
        logger.info("Loading training data...")

        data_path = Path(data_dir)
        all_conversations = []

        # Load different data types
        data_files = {
            "research_papers": "research_papers.json",
            "course_materials": "course_materials.json",
            "tutorials": "tutorials.json",
            "documentation": "documentation.json"
        }

        for data_type, filename in data_files.items():
            file_path = data_path / filename
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    items = json.load(f)

                conversations = self._convert_to_conversations(items, data_type)
                all_conversations.extend(conversations)

                logger.info(f"Loaded {len(conversations)} conversations from {filename}")

        # Create dataset
        dataset = Dataset.from_list(all_conversations)

        logger.info(f"Total training examples: {len(dataset)}")
        return dataset

    def _convert_to_conversations(self, items: List[Dict], data_type: str) -> List[Dict]:
        """Convert different data types to conversational format"""
        conversations = []

        for item in items:
            if data_type == "research_papers":
                # Convert paper abstract to Q&A format
                conversations.extend(self._paper_to_qa(item))
            elif data_type == "course_materials":
                # Convert course content to explanatory dialogues
                conversations.extend(self._course_to_dialogue(item))
            elif data_type == "tutorials":
                # Convert tutorials to step-by-step explanations
                conversations.extend(self._tutorial_to_steps(item))
            elif data_type == "documentation":
                # Convert docs to usage explanations
                conversations.extend(self._docs_to_explanations(item))

        return conversations

    def _paper_to_qa(self, paper: Dict) -> List[Dict]:
        """Convert research paper to Q&A pairs"""
        conversations = []

        title = paper.get("title", "")
        abstract = paper.get("abstract", "")

        if not title or not abstract:
            return conversations

        # Generate educational Q&A pairs
        qa_pairs = [
            {
                "input": f"What is the main topic of the paper '{title}'?",
                "output": f"This paper discusses: {abstract[:500]}..."
            },
            {
                "input": f"Can you explain the key findings from '{title}'?",
                "output": f"The paper presents research on: {abstract[:300]}..."
            }
        ]

        for qa in qa_pairs:
            conversations.append({
                "input_text": qa["input"],
                "target_text": qa["output"],
                "source": "research_paper",
                "topic": "academic_research"
            })

        return conversations

    def _course_to_dialogue(self, course: Dict) -> List[Dict]:
        """Convert course material to educational dialogue"""
        conversations = []

        title = course.get("title", "")
        content = course.get("content", "")

        if not content:
            return conversations

        # Break content into educational chunks
        chunks = self._chunk_text(content, 1000)

        for i, chunk in enumerate(chunks):
            conversations.append({
                "input_text": f"[CONCEPT] Explain this AI/ML concept from {title}: {chunk[:200]}...",
                "target_text": f"[EXPLAIN] Here's an explanation of this concept: {chunk}",
                "source": "course_material",
                "topic": "educational_content"
            })

        return conversations

    def _tutorial_to_steps(self, tutorial: Dict) -> List[Dict]:
        """Convert tutorial to step-by-step learning dialogue"""
        conversations = []

        title = tutorial.get("title", "")
        content = tutorial.get("content", "")

        if not content:
            return conversations

        # Create progressive learning steps
        steps = self._create_learning_steps(content)

        for step in steps:
            conversations.append({
                "input_text": f"[EXAMPLE] Show me how to {step['question']} in AI/ML",
                "target_text": f"[ALGORITHM] Here's how you {step['answer']}",
                "source": "tutorial",
                "topic": "practical_ai_ml"
            })

        return conversations

    def _docs_to_explanations(self, doc: Dict) -> List[Dict]:
        """Convert documentation to explanatory conversations"""
        conversations = []

        title = doc.get("title", "")
        content = doc.get("content", "")
        library = doc.get("library", "")

        if not content:
            return conversations

        conversations.append({
            "input_text": f"How do I use {title} in {library}?",
            "target_text": f"[APPLICATION] Here's how to use {title}: {content[:800]}...",
            "source": "documentation",
            "topic": "library_usage"
        })

        return conversations

    def _chunk_text(self, text: str, chunk_size: int = 1000) -> List[str]:
        """Split text into manageable chunks"""
        words = text.split()
        chunks = []

        for i in range(0, len(words), chunk_size // 10):  # Rough word-based chunking
            chunk = " ".join(words[i:i + chunk_size // 10])
            if len(chunk) > 100:  # Minimum chunk size
                chunks.append(chunk)

        return chunks

    def _create_learning_steps(self, content: str) -> List[Dict]:
        """Create progressive learning steps from tutorial content"""
        # Simple heuristic to create learning progression
        sentences = content.split('.')
        steps = []

        for i, sentence in enumerate(sentences[:5]):  # First 5 sentences
            if len(sentence.strip()) > 20:
                steps.append({
                    "question": f"understand step {i+1}",
                    "answer": f"complete step {i+1}: {sentence.strip()}"
                })

        return steps

    def preprocess_data(self, dataset: Dataset) -> Dataset:
        """Preprocess data for training"""
        logger.info("Preprocessing data...")

        # Get model max length (BlenderBot typically supports up to 512 tokens)
        max_length = min(self.tokenizer.model_max_length, 512)  # Conservative limit
        logger.info(f"Using maximum sequence length: {max_length}")

        def tokenize_function(examples):
            inputs = self.tokenizer(
                examples["input_text"],
                max_length=max_length,
                truncation=True,
                padding="max_length"
            )

            targets = self.tokenizer(
                examples["target_text"],
                max_length=max_length,
                truncation=True,
                padding="max_length"
            )

            return {
                "input_ids": inputs["input_ids"],
                "attention_mask": inputs["attention_mask"],
                "labels": targets["input_ids"]
            }

        tokenized_dataset = dataset.map(
            tokenize_function,
            batched=True,
            remove_columns=dataset.column_names
        )

        return tokenized_dataset

    def train(self, train_dataset: Dataset, eval_dataset: Optional[Dataset] = None, output_dir: str = "models/ai_education_model"):
        """Execute the training process"""
        logger.info("Starting training...")

        # Training arguments optimized for educational fine-tuning
        training_args = TrainingArguments(
            output_dir=output_dir,
            per_device_train_batch_size=4,  # Small batch size for stability
            gradient_accumulation_steps=8,   # Effective batch size of 32
            learning_rate=2e-4,              # Conservative learning rate
            num_train_epochs=3,              # Multiple epochs for thorough learning
            warmup_steps=100,                # Warmup for stable training
            logging_steps=50,
            save_steps=500,
            eval_strategy="steps" if eval_dataset is not None else "no",  # Only evaluate if eval_dataset provided
            eval_steps=500,
            save_strategy="steps",
            load_best_model_at_end=True,
            metric_for_best_model="eval_loss",
            greater_is_better=False,
            fp16=self.device.type == "cuda",  # Mixed precision on GPU
            dataloader_pin_memory=False,      # Memory optimization
            remove_unused_columns=False,
        )

        # Data collator for sequence-to-sequence tasks
        data_collator = DataCollatorForSeq2Seq(
            tokenizer=self.tokenizer,
            model=self.model,
            padding=True
        )

        # Initialize trainer
        trainer_kwargs = {
            "model": self.model,
            "args": training_args,
            "train_dataset": train_dataset,
            "data_collator": data_collator,
            "tokenizer": self.tokenizer,
        }

        # Add eval_dataset if provided
        if eval_dataset is not None:
            trainer_kwargs["eval_dataset"] = eval_dataset

        trainer = Trainer(**trainer_kwargs)

        # Start training
        logger.info("Beginning fine-tuning...")
        trainer.train()

        # Save the final model
        trainer.save_model(output_dir)
        self.tokenizer.save_pretrained(output_dir)

        logger.info(f"Training completed! Model saved to {output_dir}")

        return trainer

    def evaluate_model(self, trainer: Trainer, eval_dataset: Optional[Dataset] = None):
        """Evaluate the trained model"""
        if eval_dataset:
            results = trainer.evaluate(eval_dataset)
            logger.info(f"Evaluation results: {results}")
            return results

        # Basic evaluation on training data
        results = trainer.evaluate()
        logger.info(f"Training evaluation results: {results}")
        return results

    def run_complete_pipeline(self):
        """Run the complete training pipeline"""
        logger.info("🚀 Starting AI Education Training Pipeline")

        # Step 1: Load model and setup LoRA
        self.load_model()
        self.setup_lora()

        # Step 2: Load and preprocess data
        raw_dataset = self.load_training_data()
        processed_dataset = self.preprocess_data(raw_dataset)

        # Step 3: Split data (if needed for evaluation)
        split_dataset = processed_dataset.train_test_split(test_size=0.1, seed=42)

        # Step 4: Train model
        trainer = self.train(split_dataset["train"], split_dataset["test"])

        # Step 5: Evaluate
        self.evaluate_model(trainer, split_dataset["test"])

        logger.info("✅ Training pipeline completed successfully!")

        return trainer


if __name__ == "__main__":
    trainer = AIEducationTrainer()
    trained_model = trainer.run_complete_pipeline()
