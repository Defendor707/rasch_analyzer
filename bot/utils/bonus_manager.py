
import json
import os
from datetime import datetime
from typing import Dict, List

class BonusManager:
    """Bonus ballar tizimini boshqarish"""
    
    def __init__(self, bonus_file: str = 'data/bonus_points.json',
                 config_file: str = 'data/bonus_config.json'):
        self.bonus_file = bonus_file
        self.config_file = config_file
        self._ensure_files_exist()
    
    def _ensure_files_exist(self):
        """Fayllarni yaratish"""
        os.makedirs('data', exist_ok=True)
        
        if not os.path.exists(self.bonus_file):
            with open(self.bonus_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
        
        if not os.path.exists(self.config_file):
            default_config = {
                'test_creation_bonus': 50,  # Har bir test uchun
                'student_added_bonus': 10,  # Har bir o'quvchi uchun
                'test_completion_bonus': 100,  # Test yakunlanganda
                'stars_per_bonus_point': 1,  # 1 bonus = 1 star chegirma
                'bonus_expiry_days': 90  # 90 kun amal qiladi
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
    
    def _load_bonuses(self) -> Dict:
        """Bonus ballarni yuklash"""
        with open(self.bonus_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_bonuses(self, bonuses: Dict):
        """Bonus ballarni saqlash"""
        with open(self.bonus_file, 'w', encoding='utf-8') as f:
            json.dump(bonuses, f, ensure_ascii=False, indent=2)
    
    def get_config(self) -> Dict:
        """Konfiguratsiyani olish"""
        with open(self.config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_user_bonus(self, user_id: int) -> int:
        """Foydalanuvchi bonus balini olish"""
        bonuses = self._load_bonuses()
        user_data = bonuses.get(str(user_id), {'points': 0, 'history': []})
        return user_data.get('points', 0)
    
    def add_bonus(self, user_id: int, points: int, reason: str) -> int:
        """Bonus qo'shish"""
        bonuses = self._load_bonuses()
        user_key = str(user_id)
        
        if user_key not in bonuses:
            bonuses[user_key] = {'points': 0, 'history': []}
        
        bonuses[user_key]['points'] += points
        bonuses[user_key]['history'].append({
            'points': points,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        })
        
        self._save_bonuses(bonuses)
        return bonuses[user_key]['points']
    
    def use_bonus(self, user_id: int, points: int) -> bool:
        """Bonus ishlatish"""
        bonuses = self._load_bonuses()
        user_key = str(user_id)
        
        if user_key not in bonuses or bonuses[user_key]['points'] < points:
            return False
        
        bonuses[user_key]['points'] -= points
        bonuses[user_key]['history'].append({
            'points': -points,
            'reason': 'Tahlil uchun ishlatildi',
            'timestamp': datetime.now().isoformat()
        })
        
        self._save_bonuses(bonuses)
        return True
    
    def get_bonus_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Bonus tarixini olish"""
        bonuses = self._load_bonuses()
        user_data = bonuses.get(str(user_id), {'history': []})
        return user_data.get('history', [])[-limit:]
    
    def calculate_discount(self, user_id: int, original_price: int) -> tuple:
        """Chegirma hisoblash (discount_amount, final_price)"""
        config = self.get_config()
        user_bonus = self.get_user_bonus(user_id)
        
        max_discount = original_price  # 100% gacha chegirma
        discount = min(user_bonus * config['stars_per_bonus_point'], max_discount)
        
        final_price = max(0, original_price - discount)
        return discount, final_price
