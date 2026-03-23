#!/usr/bin/env python3
"""
AI Knowledge Base Quality Assessment Tool
Evaluates and improves the accuracy of your AI assistant
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict
import re
from datetime import datetime

class AIAccuracyEvaluator:
    def __init__(self, knowledge_base_path: str = "users.json"):
        self.knowledge_base_path = knowledge_base_path
        self.reports_dir = Path("accuracy_reports")
        self.reports_dir.mkdir(exist_ok=True)

    def load_knowledge_base(self) -> Dict:
        """Load the current knowledge base"""
        if os.path.exists(self.knowledge_base_path):
            with open(self.knowledge_base_path, 'r') as f:
                return json.load(f)
        return {}

    def analyze_content_quality(self) -> Dict:
        """Analyze the quality of content in the knowledge base"""
        kb = self.load_knowledge_base()
        analysis = {
            'total_users': len(kb),
            'total_notes': 0,
            'content_stats': defaultdict(int),
            'quality_issues': [],
            'topic_coverage': defaultdict(int),
            'content_length_distribution': defaultdict(int)
        }

        for user_id, user_data in kb.items():
            # Skip non-user data
            if not isinstance(user_data, dict) or 'email' not in user_data:
                continue

            # Load user's notes (assuming notes are stored separately)
            user_notes_file = f"notes_{user_id}.json"
            if os.path.exists(user_notes_file):
                with open(user_notes_file, 'r') as f:
                    notes = json.load(f)

                analysis['total_notes'] += len(notes)

                for note in notes.values():
                    if isinstance(note, dict):
                        self._analyze_note_quality(note, analysis)

        return analysis

    def _analyze_note_quality(self, note: Dict, analysis: Dict):
        """Analyze individual note quality"""
        content = note.get('content', '')
        title = note.get('title', '')

        # Content length analysis
        content_length = len(content)
        if content_length < 100:
            analysis['content_length_distribution']['very_short'] += 1
        elif content_length < 500:
            analysis['content_length_distribution']['short'] += 1
        elif content_length < 2000:
            analysis['content_length_distribution']['medium'] += 1
        else:
            analysis['content_length_distribution']['long'] += 1

        # Check for quality issues
        if not title.strip():
            analysis['quality_issues'].append(f"Note {note.get('id', 'unknown')} has empty title")

        if len(content.strip()) < 50:
            analysis['quality_issues'].append(f"Note '{title}' has very short content ({content_length} chars)")

        # Topic analysis (basic keyword matching)
        ai_keywords = [
            'artificial intelligence', 'machine learning', 'deep learning', 'neural network',
            'data science', 'computer vision', 'nlp', 'natural language processing',
            'reinforcement learning', 'supervised learning', 'unsupervised learning'
        ]

        content_lower = content.lower()
        for keyword in ai_keywords:
            if keyword in content_lower:
                analysis['topic_coverage'][keyword] += 1

        # Check for potentially problematic content
        if re.search(r'\b(hate|bias|discriminat)', content_lower):
            analysis['quality_issues'].append(f"Note '{title}' may contain sensitive content")

    def generate_accuracy_test_questions(self) -> List[Dict]:
        """Generate test questions to evaluate AI accuracy"""
        test_questions = [
            {
                'question': 'What is artificial intelligence?',
                'expected_keywords': ['simulation', 'human intelligence', 'machines', 'computer systems'],
                'difficulty': 'basic'
            },
            {
                'question': 'Explain machine learning',
                'expected_keywords': ['learn', 'experience', 'programming', 'algorithms'],
                'difficulty': 'basic'
            },
            {
                'question': 'What is deep learning?',
                'expected_keywords': ['neural networks', 'layers', 'subset', 'machine learning'],
                'difficulty': 'intermediate'
            },
            {
                'question': 'How does natural language processing work?',
                'expected_keywords': ['understand', 'interpret', 'human language', 'computers'],
                'difficulty': 'intermediate'
            },
            {
                'question': 'What is the difference between AI and machine learning?',
                'expected_keywords': ['subset', 'learn', 'experience', 'programming'],
                'difficulty': 'intermediate'
            },
            {
                'question': 'Explain computer vision',
                'expected_keywords': ['visual information', 'interpret', 'world', 'computers'],
                'difficulty': 'intermediate'
            },
            {
                'question': 'What are neural networks?',
                'expected_keywords': ['biological', 'algorithms', 'processing', 'compute'],
                'difficulty': 'advanced'
            }
        ]

        return test_questions

    def evaluate_ai_responses(self, responses: List[Dict]) -> Dict:
        """Evaluate AI responses for accuracy and relevance"""
        evaluation = {
            'total_questions': len(responses),
            'accurate_answers': 0,
            'partially_accurate': 0,
            'inaccurate_answers': 0,
            'no_answer': 0,
            'average_relevance_score': 0,
            'common_issues': defaultdict(int),
            'recommendations': []
        }

        total_relevance = 0

        for response in responses:
            question = response.get('question', '')
            answer = response.get('answer', '')
            relevance_score = response.get('relevance_score', 0)

            total_relevance += relevance_score

            # Basic accuracy evaluation
            if not answer or 'couldn\'t' in answer.lower():
                evaluation['no_answer'] += 1
                evaluation['common_issues']['no_answer_found'] += 1
            elif self._evaluate_answer_accuracy(question, answer):
                evaluation['accurate_answers'] += 1
            elif self._has_partial_accuracy(question, answer):
                evaluation['partially_accurate'] += 1
            else:
                evaluation['inaccurate_answers'] += 1
                evaluation['common_issues']['inaccurate_response'] += 1

        evaluation['average_relevance_score'] = total_relevance / len(responses) if responses else 0

        # Generate recommendations
        evaluation['recommendations'] = self._generate_recommendations(evaluation)

        return evaluation

    def _evaluate_answer_accuracy(self, question: str, answer: str) -> bool:
        """Basic evaluation of answer accuracy"""
        question_lower = question.lower()
        answer_lower = answer.lower()

        # Simple keyword matching for evaluation
        if 'what is artificial intelligence' in question_lower:
            return any(keyword in answer_lower for keyword in ['simulation', 'human intelligence', 'machines'])
        elif 'machine learning' in question_lower:
            return any(keyword in answer_lower for keyword in ['learn', 'experience', 'programming'])
        elif 'deep learning' in question_lower:
            return any(keyword in answer_lower for keyword in ['neural', 'layers', 'networks'])

        return True  # Default to true for questions we can't evaluate

    def _has_partial_accuracy(self, question: str, answer: str) -> bool:
        """Check if answer has partial accuracy"""
        return len(answer.strip()) > 20 and not any(phrase in answer.lower() for phrase in [
            'couldn\'t find', 'no information', 'not sure'
        ])

    def _generate_recommendations(self, evaluation: Dict) -> List[str]:
        """Generate improvement recommendations based on evaluation"""
        recommendations = []

        if evaluation['no_answer'] > evaluation['total_questions'] * 0.3:
            recommendations.append("Add more comprehensive AI/ML content to your knowledge base")

        if evaluation['inaccurate_answers'] > evaluation['total_questions'] * 0.2:
            recommendations.append("Review and correct inaccurate information in your notes")

        if evaluation['average_relevance_score'] < 0.3:
            recommendations.append("Improve content organization and add more specific AI terminology")

        if evaluation['common_issues']['no_answer_found'] > 2:
            recommendations.append("Add fundamental AI concepts and definitions to your knowledge base")

        # General recommendations
        recommendations.extend([
            "Create dedicated notes for common AI questions (What is AI?, What is ML?, etc.)",
            "Add glossary sections with clear definitions",
            "Include examples and code snippets for technical concepts",
            "Regularly review and update your knowledge base content",
            "Consider adding cross-references between related concepts"
        ])

        return recommendations

    def create_improvement_plan(self) -> Dict:
        """Create a comprehensive improvement plan"""
        plan = {
            'current_assessment': self.analyze_content_quality(),
            'test_questions': self.generate_accuracy_test_questions(),
            'priority_actions': [
                {
                    'action': 'Add core AI definitions',
                    'description': 'Create notes with accurate definitions for fundamental AI concepts',
                    'priority': 'high',
                    'estimated_time': '2-3 hours'
                },
                {
                    'action': 'Improve content quality',
                    'description': 'Review and expand short or incomplete notes',
                    'priority': 'high',
                    'estimated_time': '3-4 hours'
                },
                {
                    'action': 'Add topic cross-references',
                    'description': 'Link related concepts and create comprehensive explanations',
                    'priority': 'medium',
                    'estimated_time': '2-3 hours'
                },
                {
                    'action': 'Implement content validation',
                    'description': 'Regularly review and validate knowledge base accuracy',
                    'priority': 'medium',
                    'estimated_time': '1-2 hours'
                }
            ],
            'data_sources': [
                'Official AI/ML documentation and textbooks',
                'Peer-reviewed research papers from arXiv',
                'Wikipedia articles on AI topics',
                'Tech blogs and educational platforms',
                'Open-source AI repositories and examples'
            ],
            'monitoring_metrics': [
                'Answer accuracy rate',
                'Response relevance score',
                'User satisfaction ratings',
                'Knowledge base coverage breadth',
                'Content freshness and updates'
            ]
        }

        return plan

    def save_report(self, report_data: Dict, filename: str):
        """Save evaluation report to file"""
        report_path = self.reports_dir / filename
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        print(f"📊 Report saved to {report_path}")

def main():
    evaluator = AIAccuracyEvaluator()

    print("🧠 AI Knowledge Base Accuracy Assessment")
    print("=" * 50)

    # Analyze current content
    print("📊 Analyzing current knowledge base...")
    analysis = evaluator.analyze_content_quality()

    print(f"📈 Current Statistics:")
    print(f"   Total users: {analysis['total_users']}")
    print(f"   Total notes: {analysis['total_notes']}")
    print(f"   Content quality issues: {len(analysis['quality_issues'])}")

    # Generate test questions
    test_questions = evaluator.generate_accuracy_test_questions()
    print(f"🎯 Generated {len(test_questions)} test questions")

    # Create improvement plan
    improvement_plan = evaluator.create_improvement_plan()

    print("\n🚀 Improvement Recommendations:")
    for i, action in enumerate(improvement_plan['priority_actions'], 1):
        print(f"{i}. {action['action']} ({action['priority']} priority)")
        print(f"   {action['description']}")
        print(f"   Estimated time: {action['estimated_time']}\n")

    # Save comprehensive report
    report_data = {
        'assessment_date': datetime.now().isoformat(),
        'content_analysis': analysis,
        'test_questions': test_questions,
        'improvement_plan': improvement_plan
    }

    evaluator.save_report(report_data, f"accuracy_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

    print("✅ Assessment complete! Check the 'accuracy_reports' directory for detailed results.")
    print("\n💡 Quick Start Improvements:")
    print("1. Add a note titled 'What is Artificial Intelligence?' with a clear definition")
    print("2. Add a note titled 'Machine Learning Fundamentals' with key concepts")
    print("3. Review your existing notes for accuracy and completeness")

if __name__ == "__main__":
    main()
