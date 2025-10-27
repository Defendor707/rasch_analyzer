import re
from typing import Dict, List, Optional, Tuple


def parse_answer_string(answer_string: str, total_questions: int) -> Tuple[bool, Optional[List[Dict]], Optional[str]]:
    """
    Parse answer string in format: 1a2b3c4d32a+33b++43(ayb)
    
    Format rules:
    - Standard: number + letter (e.g., "1a" = question 1, answer A)
    - Extra options: number + letter + "+" (e.g., "32a+" = question 32, 5 options, answer A)
    - Each "+" adds one more option (max 26 options A-Z)
    - Text answer: number + (text) (e.g., "43(ayb)" = question 43, answer is "ayb")
    
    Args:
        answer_string: String containing all answers
        total_questions: Expected number of questions
        
    Returns:
        Tuple of (success, parsed_data, error_message)
        parsed_data format: [
            {
                'question_num': 1,
                'option_count': 4,  # Default A,B,C,D
                'correct_answer': 0,  # Index (0=A, 1=B, etc.) or None for text
                'text_answer': None,  # Text answer if using ()
                'is_text_answer': False
            },
            ...
        ]
    """
    # Remove spaces and convert to lowercase for easier parsing
    answer_string = answer_string.replace(' ', '').strip()
    
    # Pattern to match: number + letter + optional "+" OR number + (text)
    # Examples: 1a, 32a+, 33b++, 43(ayb), 44(alisher Navoiy)
    pattern = r'(\d+)([a-zA-Z])(\+*)|(\d+)\(([^)]+)\)'
    
    matches = re.findall(pattern, answer_string)
    
    if not matches:
        return False, None, "❌ Javoblar formati noto'g'ri! Misol: 1a2b3c4d"
    
    parsed_answers = []
    question_numbers = set()
    
    for match in matches:
        if match[0]:  # Letter-based answer (with optional +)
            question_num = int(match[0])
            answer_letter = match[1].upper()
            plus_count = len(match[2])
            
            # Validate question number
            if question_num < 1 or question_num > total_questions:
                return False, None, f"❌ Savol raqami noto'g'ri: {question_num} (1-{total_questions} oralig'ida bo'lishi kerak)"
            
            # Check for duplicates
            if question_num in question_numbers:
                return False, None, f"❌ {question_num}-savol uchun javob takrorlangan!"
            
            question_numbers.add(question_num)
            
            # Calculate option count (default 4: A,B,C,D)
            option_count = 4 + plus_count
            
            # Validate answer letter
            answer_index = ord(answer_letter) - ord('A')
            if answer_index < 0 or answer_index >= option_count:
                max_letter = chr(ord('A') + option_count - 1)
                return False, None, f"❌ {question_num}-savol uchun javob noto'g'ri! A-{max_letter} oralig'ida bo'lishi kerak"
            
            parsed_answers.append({
                'question_num': question_num,
                'option_count': option_count,
                'correct_answer': answer_index,
                'text_answer': None,
                'is_text_answer': False
            })
            
        elif match[3]:  # Text-based answer
            question_num = int(match[3])
            text_answer = match[4].strip()
            
            # Validate question number
            if question_num < 1 or question_num > total_questions:
                return False, None, f"❌ Savol raqami noto'g'ri: {question_num} (1-{total_questions} oralig'ida bo'lishi kerak)"
            
            # Check for duplicates
            if question_num in question_numbers:
                return False, None, f"❌ {question_num}-savol uchun javob takrorlangan!"
            
            question_numbers.add(question_num)
            
            if not text_answer:
                return False, None, f"❌ {question_num}-savol uchun matn javob bo'sh!"
            
            parsed_answers.append({
                'question_num': question_num,
                'option_count': 0,  # Text answers don't have options
                'correct_answer': None,
                'text_answer': text_answer,
                'is_text_answer': True
            })
    
    # Check if all questions are answered
    if len(parsed_answers) != total_questions:
        missing = set(range(1, total_questions + 1)) - question_numbers
        return False, None, f"❌ Barcha savollarga javob berilmagan! Javob berilmagan savollar: {sorted(missing)}"
    
    # Sort by question number
    parsed_answers.sort(key=lambda x: x['question_num'])
    
    return True, parsed_answers, None


def generate_option_labels(option_count: int) -> List[str]:
    """
    Generate option labels based on count
    
    Args:
        option_count: Number of options (4 = A,B,C,D; 5 = A,B,C,D,E; etc.)
        
    Returns:
        List of option labels
    """
    if option_count <= 0:
        return []
    
    labels = []
    for i in range(option_count):
        labels.append(chr(ord('A') + i))
    
    return labels


def format_answer_example(total_questions: int) -> str:
    """
    Generate example answer format for given number of questions
    
    Args:
        total_questions: Number of questions
        
    Returns:
        Example string
    """
    examples = []
    
    # Standard examples
    if total_questions >= 3:
        examples.append("Standart (4 variant): 1a2b3c")
    
    # Extra options examples
    if total_questions >= 5:
        examples.append("5 variant: 4a+")
        examples.append("6 variant: 5b++")
    
    # Text answer examples
    if total_questions >= 7:
        examples.append("Matn javob: 6(ayb)7(11)")
    
    # Combined example
    if total_questions >= 10:
        full_example = "1a2b3c4a+5b++6(ayb)7(11)8d9c10a"
        examples.append(f"\nTo'liq misol: {full_example}")
    
    return "\n".join(examples)
