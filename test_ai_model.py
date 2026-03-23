#!/usr/bin/env python3
"""
AI Education Model Testing and Evaluation Script
Test the trained BlenderBot model on AI/ML educational tasks
"""

import json
import torch
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging
from transformers import BlenderbotTokenizer, BlenderbotForConditionalGeneration
from peft import PeftModel
import numpy as np
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIEducationTester:
    """Test and evaluate the trained AI education model"""

    def __init__(self, model_path: str = "models/ai_education_model"):
        self.model_path = Path(model_path)
        self.model = None
        self.tokenizer = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        logger.info(f"Using device: {self.device}")

    def load_model(self):
        """Load the trained model and tokenizer"""
        logger.info(f"Loading trained model from {self.model_path}...")

        try:
            # Load tokenizer first (this has the correct vocabulary size)
            self.tokenizer = BlenderbotTokenizer.from_pretrained(self.model_path)

            # Load base model
            base_model = BlenderbotForConditionalGeneration.from_pretrained(
                "facebook/blenderbot-400M-distill",
                device_map="auto" if self.device.type == "cuda" else None,
            )

            # Resize token embeddings to match tokenizer vocabulary
            base_model.resize_token_embeddings(len(self.tokenizer))

            # Load the fine-tuned LoRA adapters
            self.model = PeftModel.from_pretrained(base_model, self.model_path)
            self.model.eval()

            logger.info("✅ Model loaded successfully")

        except Exception as e:
            logger.error(f"❌ Failed to load model: {e}")
            raise

    def generate_response(self, input_text: str, max_length: int = 128) -> str:
        """Generate a response from the model"""
        try:
            # Tokenize input
            inputs = self.tokenizer(
                input_text,
                return_tensors="pt",
                max_length=512,
                truncation=True,
                padding=True
            ).to(self.device)

            # Generate response
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=max_length,
                    min_length=10,
                    do_sample=True,
                    temperature=0.8,
                    top_p=0.9,
                    num_beams=2,
                    repetition_penalty=1.2,
                    pad_token_id=self.tokenizer.pad_token_id,
                )

            # Decode response
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            # Clean up response (remove input if it's included)
            if input_text in response:
                response = response.replace(input_text, "").strip()

            return response

        except Exception as e:
            logger.error(f"❌ Error generating response: {e}")
            return f"Error: {str(e)}"

    def test_basic_functionality(self) -> Dict[str, any]:
        """Test basic model functionality with simple queries"""
        logger.info("🧪 Testing basic functionality...")

        test_queries = [
            "Hello! Can you help me learn about machine learning?",
            "What is supervised learning?",
            "Explain neural networks in simple terms.",
            "How does gradient descent work?",
            "What are the differences between classification and regression?"
        ]

        results = {}
        for query in test_queries:
            response = self.generate_response(query)
            results[query] = response
            logger.info(f"Query: {query}")
            logger.info(f"Response: {response[:200]}...")
            logger.info("-" * 50)

        return results

    def test_academic_scenarios(self) -> Dict[str, any]:
        """Test model with academic AI/ML scenarios"""
        logger.info("📚 Testing academic scenarios...")

        academic_tests = [
            {
                "query": "Explain the concept of overfitting in machine learning and how to prevent it.",
                "expected_concepts": ["overfitting", "validation", "regularization", "cross-validation"]
            },
            {
                "query": "What is the difference between bagging and boosting ensemble methods?",
                "expected_concepts": ["bagging", "boosting", "random forest", "gradient boosting"]
            },
            {
                "query": "How do convolutional neural networks work for image classification?",
                "expected_concepts": ["convolution", "filters", "pooling", "feature maps"]
            },
            {
                "query": "Explain the attention mechanism in transformer architectures.",
                "expected_concepts": ["attention", "transformer", "self-attention", "encoder-decoder"]
            }
        ]

        results = {}
        for test in academic_tests:
            response = self.generate_response(test["query"], max_length=200)
            results[test["query"]] = {
                "response": response,
                "expected_concepts": test["expected_concepts"],
                "word_count": len(response.split()),
                "contains_concepts": self._check_concept_coverage(response, test["expected_concepts"])
            }

            logger.info(f"Academic Test: {test['query'][:50]}...")
            logger.info(f"Response length: {len(response.split())} words")
            logger.info(f"Concepts covered: {results[test['query']]['contains_concepts']}")
            logger.info("-" * 50)

        return results

    def test_conversation_continuity(self) -> Dict[str, any]:
        """Test conversation continuity and context awareness"""
        logger.info("💬 Testing conversation continuity...")

        conversation_scenarios = [
            {
                "scenario": "Learning progression",
                "messages": [
                    "I'm new to machine learning. Can you explain what it is?",
                    "That makes sense. Now what about neural networks?",
                    "How do I train a neural network?",
                    "What are some common problems I might encounter?"
                ]
            },
            {
                "scenario": "Concept building",
                "messages": [
                    "Explain supervised learning.",
                    "How does it differ from unsupervised learning?",
                    "Can you give me examples of both?",
                    "Which one should I learn first?"
                ]
            }
        ]

        results = {}
        for scenario in conversation_scenarios:
            conversation_responses = []

            for message in scenario["messages"]:
                response = self.generate_response(message)
                conversation_responses.append({
                    "user": message,
                    "assistant": response
                })

            results[scenario["scenario"]] = {
                "conversation": conversation_responses,
                "coherence_score": self._evaluate_conversation_coherence(conversation_responses)
            }

        return results

    def _check_concept_coverage(self, response: str, expected_concepts: List[str]) -> List[str]:
        """Check which expected concepts are mentioned in the response"""
        response_lower = response.lower()
        covered = []

        for concept in expected_concepts:
            if concept.lower() in response_lower:
                covered.append(concept)

        return covered

    def _evaluate_conversation_coherence(self, conversation: List[Dict]) -> float:
        """Simple coherence evaluation (placeholder for more sophisticated metrics)"""
        # This is a basic implementation - in practice, you'd use more sophisticated
        # NLP metrics like coherence scoring, topic consistency, etc.

        total_responses = len(conversation)
        coherent_responses = 0

        for exchange in conversation:
            response = exchange["assistant"]
            # Basic checks for coherence
            if len(response.split()) > 5:  # Reasonable response length
                coherent_responses += 1

        return coherent_responses / total_responses if total_responses > 0 else 0.0

    def run_comprehensive_evaluation(self) -> Dict[str, any]:
        """Run comprehensive evaluation of the trained model"""
        logger.info("🚀 Starting comprehensive model evaluation...")

        # Load model
        self.load_model()

        # Run all tests
        evaluation_results = {
            "timestamp": datetime.now().isoformat(),
            "model_path": str(self.model_path),
            "device": str(self.device),
            "basic_functionality": self.test_basic_functionality(),
            "academic_performance": self.test_academic_scenarios(),
            "conversation_continuity": self.test_conversation_continuity(),
            "summary": {}
        }

        # Generate summary statistics
        evaluation_results["summary"] = self._generate_evaluation_summary(evaluation_results)

        # Save results
        self.save_evaluation_results(evaluation_results)

        logger.info("✅ Evaluation completed!")
        return evaluation_results

    def _generate_evaluation_summary(self, results: Dict) -> Dict[str, any]:
        """Generate summary statistics from evaluation results"""
        summary = {
            "total_tests": 0,
            "average_concept_coverage": 0.0,
            "average_response_length": 0.0,
            "conversation_coherence": 0.0,
            "overall_score": 0.0
        }

        # Academic performance summary
        academic_results = results.get("academic_performance", {})
        if academic_results:
            concept_coverage_scores = []
            response_lengths = []

            for query, data in academic_results.items():
                expected_concepts = len(data.get("expected_concepts", []))
                covered_concepts = len(data.get("contains_concepts", []))
                coverage_ratio = covered_concepts / expected_concepts if expected_concepts > 0 else 0
                concept_coverage_scores.append(coverage_ratio)

                response_lengths.append(data.get("word_count", 0))

            summary["academic_tests"] = len(academic_results)
            summary["average_concept_coverage"] = np.mean(concept_coverage_scores)
            summary["average_response_length"] = np.mean(response_lengths)

        # Conversation continuity summary
        conversation_results = results.get("conversation_continuity", {})
        if conversation_results:
            coherence_scores = [data.get("coherence_score", 0.0) for data in conversation_results.values()]
            summary["conversation_coherence"] = np.mean(coherence_scores)

        # Overall score (weighted average)
        weights = {"concept_coverage": 0.4, "response_quality": 0.3, "coherence": 0.3}
        summary["overall_score"] = (
            summary["average_concept_coverage"] * weights["concept_coverage"] +
            (min(summary["average_response_length"] / 50, 1.0)) * weights["response_quality"] +  # Normalize response length
            summary["conversation_coherence"] * weights["coherence"]
        )

        return summary

    def save_evaluation_results(self, results: Dict[str, any], output_file: str = "evaluation_results.json"):
        """Save evaluation results to file"""
        output_path = self.model_path.parent / output_file

        # Convert numpy types to native Python types for JSON serialization
        def convert_numpy_types(obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {key: convert_numpy_types(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy_types(item) for item in obj]
            else:
                return obj

        serializable_results = convert_numpy_types(results)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)

        logger.info(f"📊 Evaluation results saved to {output_path}")

    def interactive_test(self):
        """Interactive testing mode for manual evaluation"""
        logger.info("🎮 Starting interactive testing mode...")
        logger.info("Type your questions about AI/ML. Type 'quit' to exit.")

        self.load_model()

        while True:
            try:
                user_input = input("\n🤖 Your question: ").strip()

                if user_input.lower() in ['quit', 'exit', 'q']:
                    break

                if not user_input:
                    continue

                response = self.generate_response(user_input, max_length=150)
                print(f"\n🧠 AI Assistant: {response}")
                print("-" * 80)

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        # Interactive testing mode
        tester = AIEducationTester()
        tester.interactive_test()
    else:
        # Comprehensive evaluation mode
        tester = AIEducationTester()
        results = tester.run_comprehensive_evaluation()

        print("\n" + "="*80)
        print("📊 EVALUATION SUMMARY")
        print("="*80)
        print(".2f")
        print(".2f")
        print(".1f")
        print(".2f")
        print("="*80)
