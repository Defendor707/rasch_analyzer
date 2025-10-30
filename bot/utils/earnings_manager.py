import json
import os
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class EarningsManager:
    """O'qituvchilar daromadlarini boshqarish"""

    def __init__(self, data_file: str = "data/teacher_earnings.json"):
        self.data_file = data_file
        self._ensure_file_exists()
        self.TEACHER_SHARE_PERCENT = 80  # O'qituvchiga 80%
        self.PLATFORM_SHARE_PERCENT = 20  # Platformaga 20%

    def _ensure_file_exists(self):
        """Create data file if it doesn't exist"""
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        if not os.path.exists(self.data_file):
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'earnings': [],
                    'withdrawals': [],
                    'teacher_balances': {}
                }, f, ensure_ascii=False)

    def _load_data(self) -> Dict:
        """Load all earnings data"""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {
                'earnings': [],
                'withdrawals': [],
                'teacher_balances': {}
            }

    def _save_data(self, data: Dict):
        """Save earnings data"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def record_test_payment(self, teacher_id: str, student_id: str, 
                           test_id: str, amount: int, payment_id: str = None) -> Dict:
        """
        Test to'lovi uchun daromadni qayd qilish
        
        Args:
            teacher_id: Test yaratuvchi ID
            student_id: Talaba ID
            test_id: Test ID
            amount: To'langan miqdor (Stars)
            payment_id: To'lov ID
        
        Returns:
            Daromad ma'lumotlari
        """
        data = self._load_data()
        
        # Daromadni taqsimlash
        teacher_share = int(amount * self.TEACHER_SHARE_PERCENT / 100)
        platform_share = int(amount * self.PLATFORM_SHARE_PERCENT / 100)
        
        earning = {
            'id': len(data['earnings']) + 1,
            'teacher_id': str(teacher_id),
            'student_id': str(student_id),
            'test_id': test_id,
            'payment_id': payment_id,
            'total_amount': amount,
            'teacher_share': teacher_share,
            'platform_share': platform_share,
            'status': 'completed',
            'created_at': datetime.now().isoformat()
        }
        
        data['earnings'].append(earning)
        
        # O'qituvchi balansini yangilash
        teacher_id_str = str(teacher_id)
        if teacher_id_str not in data['teacher_balances']:
            data['teacher_balances'][teacher_id_str] = {
                'available': 0,
                'withdrawn': 0,
                'pending': 0,
                'total_earned': 0
            }
        
        data['teacher_balances'][teacher_id_str]['available'] += teacher_share
        data['teacher_balances'][teacher_id_str]['total_earned'] += teacher_share
        
        self._save_data(data)
        logger.info(f"Daromad qayd qilindi: Teacher {teacher_id}, Amount {amount}, Share {teacher_share}")
        
        return earning

    def get_teacher_balance(self, teacher_id: str) -> Dict:
        """O'qituvchi balansini olish"""
        data = self._load_data()
        teacher_id_str = str(teacher_id)
        
        if teacher_id_str not in data['teacher_balances']:
            return {
                'available': 0,
                'withdrawn': 0,
                'pending': 0,
                'total_earned': 0
            }
        
        return data['teacher_balances'][teacher_id_str]

    def get_teacher_earnings(self, teacher_id: str) -> List[Dict]:
        """O'qituvchining barcha daromadlarini olish"""
        data = self._load_data()
        teacher_id_str = str(teacher_id)
        
        earnings = [e for e in data['earnings'] if e['teacher_id'] == teacher_id_str]
        return sorted(earnings, key=lambda x: x['created_at'], reverse=True)

    def create_withdrawal_request(self, teacher_id: str, amount: int, 
                                  method: str, wallet_address: str = None) -> Dict:
        """
        Pul yechib olish so'rovi yaratish
        
        Args:
            teacher_id: O'qituvchi ID
            amount: Yechib olinadigan miqdor
            method: To'lov usuli (TON, bank, etc.)
            wallet_address: Hamyon manzili
        
        Returns:
            So'rov ma'lumotlari yoki xato
        """
        data = self._load_data()
        teacher_id_str = str(teacher_id)
        
        balance = self.get_teacher_balance(teacher_id)
        
        if balance['available'] < amount:
            return {
                'error': f"Yetarli mablag' yo'q. Mavjud: {balance['available']} ⭐"
            }
        
        if amount < 10:
            return {
                'error': "Minimal yechib olish miqdori 10 ⭐"
            }
        
        withdrawal = {
            'id': len(data['withdrawals']) + 1,
            'teacher_id': teacher_id_str,
            'amount': amount,
            'method': method,
            'wallet_address': wallet_address,
            'status': 'pending',
            'requested_at': datetime.now().isoformat(),
            'processed_at': None,
            'admin_note': None
        }
        
        data['withdrawals'].append(withdrawal)
        
        # Balansni yangilash
        data['teacher_balances'][teacher_id_str]['available'] -= amount
        data['teacher_balances'][teacher_id_str]['pending'] += amount
        
        self._save_data(data)
        
        logger.info(f"Withdrawal request yaratildi: Teacher {teacher_id}, Amount {amount}")
        
        return withdrawal

    def get_withdrawal_requests(self, teacher_id: str = None, status: str = None) -> List[Dict]:
        """
        Withdrawal so'rovlarini olish
        
        Args:
            teacher_id: O'qituvchi ID (agar berilmasa, barcha so'rovlar)
            status: Status filter (pending, approved, rejected, completed)
        """
        data = self._load_data()
        withdrawals = data['withdrawals']
        
        if teacher_id:
            withdrawals = [w for w in withdrawals if w['teacher_id'] == str(teacher_id)]
        
        if status:
            withdrawals = [w for w in withdrawals if w['status'] == status]
        
        return sorted(withdrawals, key=lambda x: x['requested_at'], reverse=True)

    def process_withdrawal(self, withdrawal_id: int, admin_id: str, 
                          status: str, admin_note: str = None) -> bool:
        """
        Withdrawal so'rovini qayta ishlash (admin tomonidan)
        
        Args:
            withdrawal_id: So'rov ID
            admin_id: Admin ID
            status: Yangi status (approved, rejected, completed)
            admin_note: Admin izohi
        """
        data = self._load_data()
        
        withdrawal = None
        for w in data['withdrawals']:
            if w['id'] == withdrawal_id:
                withdrawal = w
                break
        
        if not withdrawal:
            return False
        
        if withdrawal['status'] != 'pending':
            return False
        
        old_status = withdrawal['status']
        withdrawal['status'] = status
        withdrawal['processed_at'] = datetime.now().isoformat()
        withdrawal['admin_note'] = admin_note
        withdrawal['processed_by'] = str(admin_id)
        
        teacher_id = withdrawal['teacher_id']
        amount = withdrawal['amount']
        
        # Balansni yangilash
        if teacher_id in data['teacher_balances']:
            if status == 'completed':
                # Withdrawn balansini oshirish
                data['teacher_balances'][teacher_id]['pending'] -= amount
                data['teacher_balances'][teacher_id]['withdrawn'] += amount
            elif status == 'rejected':
                # Available balansga qaytarish
                data['teacher_balances'][teacher_id]['pending'] -= amount
                data['teacher_balances'][teacher_id]['available'] += amount
        
        self._save_data(data)
        
        logger.info(f"Withdrawal processed: ID {withdrawal_id}, Status {status}")
        
        return True

    def get_platform_earnings(self) -> Dict:
        """Platform daromadlarini hisoblash"""
        data = self._load_data()
        
        total_platform_share = sum(e['platform_share'] for e in data['earnings'])
        total_teacher_share = sum(e['teacher_share'] for e in data['earnings'])
        total_amount = sum(e['total_amount'] for e in data['earnings'])
        
        return {
            'total_earnings': total_amount,
            'platform_share': total_platform_share,
            'teacher_share': total_teacher_share,
            'total_transactions': len(data['earnings'])
        }

    def get_earnings_stats(self, teacher_id: str = None) -> Dict:
        """Daromad statistikasini olish"""
        data = self._load_data()
        
        if teacher_id:
            earnings = [e for e in data['earnings'] if e['teacher_id'] == str(teacher_id)]
        else:
            earnings = data['earnings']
        
        if not earnings:
            return {
                'total_earnings': 0,
                'total_transactions': 0,
                'average_earning': 0
            }
        
        total = sum(e.get('teacher_share', 0) for e in earnings)
        count = len(earnings)
        
        return {
            'total_earnings': total,
            'total_transactions': count,
            'average_earning': total / count if count > 0 else 0
        }
