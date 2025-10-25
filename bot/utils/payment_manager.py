import json
import os
from datetime import datetime
from typing import Dict, List, Optional

class PaymentManager:
    """Manage payment records and pricing for Telegram Stars payments"""
    
    def __init__(self, payments_file: str = 'data/payments.json', 
                 config_file: str = 'data/payment_config.json'):
        self.payments_file = payments_file
        self.config_file = config_file
        self._ensure_files_exist()
    
    def _ensure_files_exist(self):
        """Create data files if they don't exist"""
        os.makedirs('data', exist_ok=True)
        
        if not os.path.exists(self.payments_file):
            with open(self.payments_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
        
        if not os.path.exists(self.config_file):
            default_config = {
                'analysis_price_stars': 100,
                'currency': 'XTR',
                'admin_ids': []
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
    
    def get_config(self) -> Dict:
        """Get payment configuration"""
        with open(self.config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def update_price(self, price_stars: int):
        """Update analysis price in Stars"""
        config = self.get_config()
        config['analysis_price_stars'] = price_stars
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    def add_admin(self, admin_id: int):
        """Add admin user ID"""
        config = self.get_config()
        if admin_id not in config['admin_ids']:
            config['admin_ids'].append(admin_id)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        config = self.get_config()
        return user_id in config['admin_ids']
    
    def record_payment(self, user_id: int, amount_stars: int, 
                      telegram_payment_charge_id: str, 
                      file_name: Optional[str] = None) -> str:
        """Record a successful payment"""
        payments = self._load_payments()
        
        payment_record = {
            'payment_id': telegram_payment_charge_id,
            'user_id': user_id,
            'amount_stars': amount_stars,
            'file_name': file_name,
            'timestamp': datetime.now().isoformat(),
            'status': 'completed'
        }
        
        payments.append(payment_record)
        self._save_payments(payments)
        return telegram_payment_charge_id
    
    def get_user_payments(self, user_id: int) -> List[Dict]:
        """Get all payments by a user"""
        payments = self._load_payments()
        return [p for p in payments if p['user_id'] == user_id]
    
    def get_all_payments(self) -> List[Dict]:
        """Get all payment records (admin only)"""
        return self._load_payments()
    
    def get_payment_stats(self) -> Dict:
        """Get payment statistics"""
        payments = self._load_payments()
        
        total_payments = len(payments)
        total_stars = sum(p['amount_stars'] for p in payments)
        unique_users = len(set(p['user_id'] for p in payments))
        
        return {
            'total_payments': total_payments,
            'total_stars': total_stars,
            'unique_users': unique_users,
            'latest_payment': payments[-1] if payments else None
        }
    
    def has_paid_for_file(self, user_id: int, file_name: str) -> bool:
        """Check if user has already paid for this file"""
        payments = self.get_user_payments(user_id)
        return any(p['file_name'] == file_name and p['status'] == 'completed' 
                  for p in payments)
    
    def _load_payments(self) -> List[Dict]:
        """Load payments from file"""
        with open(self.payments_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_payments(self, payments: List[Dict]):
        """Save payments to file"""
        with open(self.payments_file, 'w', encoding='utf-8') as f:
            json.dump(payments, f, ensure_ascii=False, indent=2)
