
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime


class TestManager:
    """Manages public tests creation and storage"""
    
    def __init__(self, data_file: str = "data/tests.json"):
        self.data_file = data_file
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Create data file if it doesn't exist"""
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        if not os.path.exists(self.data_file):
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False)
    
    def _load_tests(self) -> Dict:
        """Load all tests from file"""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    
    def _save_tests(self, tests: Dict):
        """Save tests to file"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(tests, f, ensure_ascii=False, indent=2)
    
    def create_test(self, teacher_id: int, test_data: Dict[str, Any]) -> str:
        """
        Create a new test
        
        Args:
            teacher_id: ID of the teacher creating the test
            test_data: Dict with test information (name, subject, duration, etc.)
            
        Returns:
            test_id: Unique test identifier
        """
        tests = self._load_tests()
        
        # Generate unique test ID
        test_id = f"test_{teacher_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Initialize test structure
        tests[test_id] = {
            'teacher_id': teacher_id,
            'name': test_data.get('name', 'Nomsiz test'),
            'subject': test_data.get('subject', ''),
            'start_date': test_data.get('start_date', ''),
            'start_time': test_data.get('start_time', ''),
            'duration': test_data.get('duration', 60),  # minutes
            'questions': [],
            'created_at': datetime.now().isoformat(),
            'is_active': False,
            'participants': []
        }
        
        self._save_tests(tests)
        return test_id
    
    def add_question(self, test_id: str, question_data: Dict[str, Any]) -> bool:
        """
        Add a question to a test
        
        Args:
            test_id: Test identifier
            question_data: Dict with question text, options, correct answer
            
        Returns:
            Success status
        """
        tests = self._load_tests()
        
        if test_id not in tests:
            return False
        
        question = {
            'id': len(tests[test_id]['questions']) + 1,
            'text': question_data.get('text', ''),
            'options': question_data.get('options', []),
            'correct_answer': question_data.get('correct_answer', 0),
            'points': question_data.get('points', 1)
        }
        
        tests[test_id]['questions'].append(question)
        self._save_tests(tests)
        return True
    
    def get_test(self, test_id: str) -> Optional[Dict]:
        """Get test by ID"""
        tests = self._load_tests()
        return tests.get(test_id)
    
    def get_teacher_tests(self, teacher_id: int) -> List[Dict]:
        """Get all tests created by a teacher"""
        tests = self._load_tests()
        teacher_tests = []
        
        for test_id, test_data in tests.items():
            if test_data['teacher_id'] == teacher_id:
                teacher_tests.append({
                    'id': test_id,
                    **test_data
                })
        
        return teacher_tests
    
    def activate_test(self, test_id: str) -> bool:
        """Activate a test for participants"""
        tests = self._load_tests()
        
        if test_id not in tests:
            return False
        
        tests[test_id]['is_active'] = True
        self._save_tests(tests)
        return True
    
    def deactivate_test(self, test_id: str) -> bool:
        """Deactivate a test"""
        tests = self._load_tests()
        
        if test_id not in tests:
            return False
        
        tests[test_id]['is_active'] = False
        self._save_tests(tests)
        return True
    
    def delete_test(self, test_id: str, teacher_id: int) -> bool:
        """Delete a test (only by owner)"""
        tests = self._load_tests()
        
        if test_id not in tests or tests[test_id]['teacher_id'] != teacher_id:
            return False
        
        del tests[test_id]
        self._save_tests(tests)
        return True
    
    def submit_answer(self, test_id: str, student_id: int, answers: List[int]) -> Dict:
        """
        Submit student answers and calculate score
        
        Args:
            test_id: Test identifier
            student_id: Student's user ID
            answers: List of selected answer indices
            
        Returns:
            Results dict with score and details
        """
        tests = self._load_tests()
        
        if test_id not in tests:
            return {'error': 'Test topilmadi'}
        
        test = tests[test_id]
        
        if not test['is_active']:
            return {'error': 'Test faol emas'}
        
        # Calculate score
        total_points = 0
        earned_points = 0
        question_results = []
        
        for i, question in enumerate(test['questions']):
            total_points += question['points']
            
            if i < len(answers) and answers[i] == question['correct_answer']:
                earned_points += question['points']
                question_results.append({
                    'question_id': question['id'],
                    'correct': True
                })
            else:
                question_results.append({
                    'question_id': question['id'],
                    'correct': False
                })
        
        # Save participant result
        participant_data = {
            'student_id': student_id,
            'submitted_at': datetime.now().isoformat(),
            'score': earned_points,
            'max_score': total_points,
            'percentage': (earned_points / total_points * 100) if total_points > 0 else 0,
            'answers': answers,
            'results': question_results
        }
        
        tests[test_id]['participants'].append(participant_data)
        self._save_tests(tests)
        
        return {
            'score': earned_points,
            'max_score': total_points,
            'percentage': participant_data['percentage'],
            'results': question_results
        }
    
    def get_test_results_matrix(self, test_id: str) -> Optional[Dict]:
        """
        Get test results as a dichotomous response matrix for Rasch analysis
        
        Args:
            test_id: Test identifier
            
        Returns:
            Dict with response matrix and metadata
        """
        tests = self._load_tests()
        
        if test_id not in tests:
            return None
        
        test = tests[test_id]
        participants = test.get('participants', [])
        
        if not participants:
            return None
        
        # Create response matrix (persons x items)
        n_questions = len(test['questions'])
        response_matrix = []
        student_ids = []
        
        for participant in participants:
            student_ids.append(participant['student_id'])
            row = []
            
            for i, result in enumerate(participant['results']):
                row.append(1 if result['correct'] else 0)
            
            response_matrix.append(row)
        
        # Create item names
        item_names = [f"Savol_{i+1}" for i in range(n_questions)]
        
        return {
            'matrix': response_matrix,
            'student_ids': student_ids,
            'item_names': item_names,
            'test_name': test['name'],
            'test_subject': test['subject'],
            'n_questions': n_questions,
            'n_participants': len(participants)
        }
    
    def finalize_test(self, test_id: str) -> bool:
        """
        Mark test as finalized (no more submissions allowed)
        
        Args:
            test_id: Test identifier
            
        Returns:
            Success status
        """
        tests = self._load_tests()
        
        if test_id not in tests:
            return False
        
        tests[test_id]['is_active'] = False
        tests[test_id]['finalized_at'] = datetime.now().isoformat()
        self._save_tests(tests)
        return True
