
import json
import os
from typing import Dict, List, Any

class StudentDataManager:
    """Manage student data storage"""
    
    def __init__(self, data_file: str = "data/students.json"):
        self.data_file = data_file
        os.makedirs(os.path.dirname(data_file), exist_ok=True)
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Create data file if it doesn't exist"""
        if not os.path.exists(self.data_file):
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
    
    def get_all_students(self, teacher_id: int) -> List[Dict[str, Any]]:
        """Get all students for a teacher"""
        with open(self.data_file, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
        
        teacher_key = str(teacher_id)
        return all_data.get(teacher_key, [])
    
    def add_student(self, teacher_id: int, student_data: Dict[str, Any]) -> int:
        """Add new student and return student ID"""
        with open(self.data_file, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
        
        teacher_key = str(teacher_id)
        if teacher_key not in all_data:
            all_data[teacher_key] = []
        
        # Generate student ID
        student_id = len(all_data[teacher_key]) + 1
        student_data['id'] = student_id
        
        all_data[teacher_key].append(student_data)
        
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        
        return student_id
    
    def update_student(self, teacher_id: int, student_id: int, student_data: Dict[str, Any]):
        """Update existing student"""
        with open(self.data_file, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
        
        teacher_key = str(teacher_id)
        if teacher_key in all_data:
            for i, student in enumerate(all_data[teacher_key]):
                if student.get('id') == student_id:
                    student_data['id'] = student_id
                    all_data[teacher_key][i] = student_data
                    break
        
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    def delete_student(self, teacher_id: int, student_id: int):
        """Delete student"""
        with open(self.data_file, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
        
        teacher_key = str(teacher_id)
        if teacher_key in all_data:
            all_data[teacher_key] = [
                s for s in all_data[teacher_key] if s.get('id') != student_id
            ]
        
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    def get_student(self, teacher_id: int, student_id: int) -> Dict[str, Any]:
        """Get single student data"""
        students = self.get_all_students(teacher_id)
        for student in students:
            if student.get('id') == student_id:
                return student
        return {}
