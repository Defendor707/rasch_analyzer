
import json
import os
from typing import Dict, Any

class UserDataManager:
    """Manage user profile data storage"""
    
    def __init__(self, data_file: str = "data/user_profiles.json"):
        self.data_file = data_file
        os.makedirs(os.path.dirname(data_file), exist_ok=True)
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Create data file if it doesn't exist"""
        if not os.path.exists(self.data_file):
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
    
    def get_user_data(self, user_id: int) -> Dict[str, Any]:
        """Get user profile data"""
        with open(self.data_file, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
        
        return all_data.get(str(user_id), {
            'first_name': '',
            'last_name': '',
            'bio': '',
            'subject': '',
            'school': '',
            'phone': '',
            'experience_years': '',
            'profile_photo_id': None,
            'file_analyzer_mode': False
        })
    
    def save_user_data(self, user_id: int, data: Dict[str, Any]):
        """Save user profile data"""
        with open(self.data_file, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
        
        all_data[str(user_id)] = data
        
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    def update_user_field(self, user_id: int, field: str, value: Any):
        """Update specific field in user profile"""
        user_data = self.get_user_data(user_id)
        user_data[field] = value
        self.save_user_data(user_id, user_data)
