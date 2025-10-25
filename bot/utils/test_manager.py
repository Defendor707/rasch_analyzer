import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
import pytz


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
            'allow_retake': False,  # Default: no retakes
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

    def submit_answer(self, test_id: str, user_id: int, answers: List[int]) -> Dict[str, Any]:
        """
        Submit all answers for a test and calculate results
        
        Args:
            test_id: Test identifier
            user_id: Student user ID
            answers: List of answer indices (-1 for unanswered)
            
        Returns:
            Dict with results or error
        """
        tests = self._load_tests()
        
        if test_id not in tests:
            return {'error': 'Test topilmadi'}
        
        test = tests[test_id]
        
        # Check if test time expired
        can_take, message = self.can_take_test(test_id)
        if not can_take:
            return {'error': message}

        user_id_str = str(user_id)
        
        # Migrate participants from list to dict format if needed
        participants = test.get('participants', {})
        if isinstance(participants, list):
            # Convert old list format to new dict format
            migrated_participants = {}
            for participant in participants:
                if isinstance(participant, dict):
                    p_user_id = str(participant.get('student_id', ''))
                    if p_user_id:
                        migrated_participants[p_user_id] = participant
            test['participants'] = migrated_participants
        elif not isinstance(participants, dict):
            # Initialize as empty dict if not list or dict
            test['participants'] = {}

        # Check if already submitted (prevent retake unless allowed)
        if user_id_str in test['participants']:
            participant_data = test['participants'][user_id_str]
            if isinstance(participant_data, dict) and participant_data.get('submitted'):
                if not test.get('allow_retake', False):
                    return {'error': 'Siz allaqachon ushbu testni topshirgansiz'}

        # Calculate score
        correct_count = 0
        total_questions = len(test['questions'])
        results = []
        
        for i, question in enumerate(test['questions']):
            answer_idx = answers[i] if i < len(answers) else -1
            is_correct = (answer_idx == question['correct_answer'])
            if is_correct:
                correct_count += 1
            
            results.append({
                'question_id': i + 1,
                'student_answer': answer_idx,
                'correct_answer': question['correct_answer'],
                'correct': is_correct
            })
        
        percentage = (correct_count / total_questions * 100) if total_questions > 0 else 0
        
        # Save participant data
        tz = pytz.timezone('Asia/Tashkent')
        test['participants'][user_id_str] = {
            'student_id': user_id,
            'answers': {str(i): ans for i, ans in enumerate(answers)},
            'score': correct_count,
            'max_score': total_questions,
            'percentage': percentage,
            'results': results,
            'submitted': True,
            'submitted_at': datetime.now(tz).isoformat()
        }
        
        self._save_tests(tests)
        
        return {
            'score': correct_count,
            'max_score': total_questions,
            'percentage': percentage,
            'results': results
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
        participants = test.get('participants', {})

        if not participants:
            return None

        # Create response matrix (persons x items)
        n_questions = len(test['questions'])
        response_matrix = []
        student_ids = []

        # Handle both dict and list formats for backward compatibility
        if isinstance(participants, dict):
            for user_id_str, participant in participants.items():
                if isinstance(participant, dict) and participant.get('submitted'):
                    student_ids.append(participant.get('student_id', int(user_id_str)))
                    row = []
                    for result in participant.get('results', []):
                        row.append(1 if result.get('correct') else 0)
                    response_matrix.append(row)
        elif isinstance(participants, list):
            for participant in participants:
                student_ids.append(participant['student_id'])
                row = []
                for i, result in enumerate(participant['results']):
                    row.append(1 if result['correct'] else 0)
                response_matrix.append(row)

        if not response_matrix:
            return None

        # Create item names
        item_names = [f"Savol_{i+1}" for i in range(n_questions)]

        return {
            'matrix': response_matrix,
            'student_ids': student_ids,
            'item_names': item_names,
            'test_name': test['name'],
            'test_subject': test['subject'],
            'n_questions': n_questions,
            'n_participants': len(response_matrix)
        }

    def is_test_time_valid(self, test_id: str) -> Dict[str, Any]:
        """
        Check if current time is within test time range

        Args:
            test_id: Test identifier

        Returns:
            Dict with validity status and message
        """
        test = self.get_test(test_id)

        if not test:
            return {'valid': False, 'message': 'Test topilmadi'}

        if not test.get('start_date') or not test.get('start_time'):
            # No time restrictions
            return {'valid': True, 'message': 'OK'}

        try:
            # Use Tashkent timezone
            tz = pytz.timezone('Asia/Tashkent')
            start_datetime_str = f"{test['start_date']} {test['start_time']}"
            start_datetime = datetime.strptime(start_datetime_str, '%Y-%m-%d %H:%M').replace(tzinfo=tz)

            # Calculate end datetime
            duration_minutes = test.get('duration', 60)
            end_datetime = start_datetime + timedelta(minutes=duration_minutes)

            # Get current time
            current_datetime = datetime.now(tz)

            # Auto-finalize if time expired
            if current_datetime > end_datetime:
                self.finalize_test(test_id)
                return {
                    'valid': False,
                    'message': f"Test vaqti tugagan va avtomatik yakunlandi. Tugash vaqti: {end_datetime.strftime('%Y-%m-%d %H:%M')}"
                }

            # Check if before start
            if current_datetime < start_datetime:
                remaining_minutes = int((start_datetime - current_datetime).total_seconds() / 60)
                return {
                    'valid': False,
                    'message': f"Test hali boshlanmagan. Boshlanishiga {remaining_minutes} daqiqa qoldi."
                }

            # Within valid time range
            remaining_minutes = int((end_datetime - current_datetime).total_seconds() / 60)
            return {
                'valid': True,
                'message': f"Test davom etmoqda. Qolgan vaqt: {remaining_minutes} daqiqa"
            }

        except Exception as e:
            logging.error(f"Error checking test time for {test_id}: {e}")
            # If parsing fails or any other error, consider it valid to avoid blocking tests
            return {'valid': True, 'message': 'OK (vaqt tekshirishda xatolik)'}

    def has_student_taken_test(self, test_id: str, student_id: int) -> bool:
        """
        Check if student has already taken this test

        Args:
            test_id: Test identifier
            student_id: Student user ID

        Returns:
            True if student has taken test, False otherwise
        """
        test = self.get_test(test_id)

        if not test:
            return False

        student_id_str = str(student_id)
        participants = test.get('participants', {})
        
        # Handle both dict and list formats for backward compatibility
        if isinstance(participants, dict):
            if student_id_str in participants:
                participant_data = participants[student_id_str]
                if isinstance(participant_data, dict) and participant_data.get('submitted'):
                    return True
        elif isinstance(participants, list):
            for participant in participants:
                if str(participant.get('student_id')) == student_id_str:
                    return True

        return False

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

    def can_take_test(self, test_id: str) -> tuple[bool, str]:
        """Check if test can be taken now"""
        test = self.get_test(test_id)
        if not test:
            return False, "Test topilmadi"

        if test.get('is_active') is False and 'finalized_at' in test:
             return False, "Test yakunlangan"
        elif test.get('is_active') is False and 'finalized_at' not in test:
            # If it's not active and not finalized, it might be in the past or future
            pass


        # Use Tashkent timezone
        tz = pytz.timezone('Asia/Tashkent')
        now = datetime.now(tz)

        # If start date/time are not set, consider it always available until finalized
        if not test.get('start_date') or not test.get('start_time'):
             if test.get('is_active', False): # Only allow if explicitly activated
                return True, "Test topshirish mumkin"
             else:
                 return False, "Test faol emas"


        try:
            start_datetime_str = f"{test['start_date']} {test['start_time']}"
            start_datetime = datetime.strptime(start_datetime_str, '%Y-%m-%d %H:%M').replace(tzinfo=tz)

            # If test hasn't started yet
            if now < start_datetime:
                time_left = start_datetime - now
                hours = int(time_left.total_seconds() // 3600)
                minutes = int((time_left.total_seconds() % 3600) // 60)
                return False, f"Test hali boshlanmagan. Boshlanishiga {hours} soat {minutes} daqiqa qoldi"

            # Calculate end time if duration is provided
            if 'duration' in test:
                duration_minutes = test['duration']
                end_datetime = start_datetime + timedelta(minutes=duration_minutes)

                # Auto-finalize if time expired
                if now > end_datetime:
                    self.finalize_test(test_id)
                    return False, "Test vaqti tugagan va avtomatik yakunlandi"
            else:
                # If no duration, and it has started, it's considered ongoing until finalized
                pass


            # If the test is active and started (and not expired if duration was set)
            if test.get('is_active', False):
                return True, "Test topshirish mumkin"
            else:
                return False, "Test faol emas yoki yakunlangan"

        except Exception as e:
            logging.error(f"Error in can_take_test for {test_id}: {e}")
            return False, "Testni tekshirishda xatolik yuz berdi"

    def calculate_score(self, test_id: str, user_id: int) -> Optional[Dict[str, Any]]:
        """Calculate user's score for the test"""
        tests = self._load_tests()
        
        if test_id not in tests:
            return None
            
        test = tests[test_id]
        user_id_str = str(user_id)

        if user_id_str not in test.get('participants', {}):
            return None

        participant_data = test['participants'][user_id_str]
        user_answers = participant_data.get('answers', {})
        
        # Build correct answer map
        correct_answer_map = {str(q['id']): q['correct_answer'] for q in test.get('questions', [])}

        total_questions_in_test = len(test.get('questions', []))

        correct_count = 0
        question_results = []

        # Iterate through all questions defined in the test
        for question_id_str, correct_answer_index in correct_answer_map.items():
            student_answer_index = user_answers.get(question_id_str)
            is_correct = False
            if student_answer_index is not None and student_answer_index == correct_answer_index:
                is_correct = True
                correct_count += 1

            question_results.append({
                'question_id': int(question_id_str),
                'correct': is_correct
            })

        # Mark as submitted and record submit time
        participant_data['submitted'] = True
        tz = pytz.timezone('Asia/Tashkent')
        participant_data['submit_time'] = datetime.now(tz).isoformat()
        self._save_tests(tests)

        return {
            'total_possible_score': total_questions_in_test,
            'correct_answers': correct_count,
            'percentage': (correct_count / total_questions_in_test * 100) if total_questions_in_test > 0 else 0,
            'results_details': question_results
        }