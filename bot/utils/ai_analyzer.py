import os
from openai import OpenAI
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class AIAnalyzer:
    def __init__(self):
        api_key = os.getenv('DEEPSEEK_API_KEY')
        if not api_key:
            logger.warning("DEEPSEEK_API_KEY environment variable not set")
            self.client = None
        else:
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com"
            )
    
    def analyze_test_results(self, results: Dict[str, Any]) -> str:
        if not self.client:
            return "⚠️ AI tahlili mavjud emas (API kalit sozlanmagan)"
        
        try:
            n_persons = results.get('n_persons', 0)
            n_items = results.get('n_items', 0)
            reliability = results.get('reliability', 0)
            
            person_stats = results.get('person_statistics', {})
            individual_data = person_stats.get('individual', [])
            
            if not individual_data:
                return "⚠️ AI tahlili uchun ma'lumotlar topilmadi"
            
            scores = [p['raw_score'] for p in individual_data if 'raw_score' in p]
            t_scores = [p['t_score'] for p in individual_data if 't_score' in p]
            
            if not scores or not t_scores:
                return "⚠️ AI tahlili uchun ball ma'lumotlari topilmadi"
            
            avg_score = sum(scores) / len(scores) if scores else 0
            max_score = max(scores) if scores else 0
            min_score = min(scores) if scores else 0
            avg_t_score = sum(t_scores) / len(t_scores) if t_scores else 0
            
            grade_counts = {'A+': 0, 'A': 0, 'B+': 0, 'B': 0, 'C+': 0, 'C': 0, 'NC': 0}
            for t in t_scores:
                if t >= 70:
                    grade_counts['A+'] += 1
                elif t >= 65:
                    grade_counts['A'] += 1
                elif t >= 60:
                    grade_counts['B+'] += 1
                elif t >= 55:
                    grade_counts['B'] += 1
                elif t >= 50:
                    grade_counts['C+'] += 1
                elif t >= 46:
                    grade_counts['C'] += 1
                else:
                    grade_counts['NC'] += 1
            
            prompt = f"""Test natijalarini tahlil qilib, o'zbek tilida xulosaviy fikr va tavsiyalar bering.

Test ma'lumotlari:
- Talabgorlar soni: {n_persons}
- Savollar soni: {n_items}
- Ishonchlilik (Reliability): {reliability:.3f}
- O'rtacha ball: {avg_score:.1f}/{n_items}
- Eng yuqori ball: {max_score}
- Eng past ball: {min_score}
- O'rtacha T-Score: {avg_t_score:.1f}

Darajalar taqsimoti:
- A+ (70+): {grade_counts['A+']} ta ({grade_counts['A+']/n_persons*100:.1f}%)
- A (65-69): {grade_counts['A']} ta ({grade_counts['A']/n_persons*100:.1f}%)
- B+ (60-64): {grade_counts['B+']} ta ({grade_counts['B+']/n_persons*100:.1f}%)
- B (55-59): {grade_counts['B']} ta ({grade_counts['B']/n_persons*100:.1f}%)
- C+ (50-54): {grade_counts['C+']} ta ({grade_counts['C+']/n_persons*100:.1f}%)
- C (46-49): {grade_counts['C']} ta ({grade_counts['C']/n_persons*100:.1f}%)
- NC (<46): {grade_counts['NC']} ta ({grade_counts['NC']/n_persons*100:.1f}%)

Quyidagilarni o'zbek tilida ta'minlang:
1. Umumiy baho (test qanchalik yaxshi o'tgani)
2. Asosiy kamchiliklar va muammolar
3. O'qituvchi uchun aniq tavsiyalar
4. Keyingi qadamlar

Javobingiz qisqa, aniq va amaliy bo'lsin (maksimum 800 so'z). Professional va konstruktiv yondashuvda bo'ling."""

            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "Siz ta'lim sohasida tajribali pedagog va test tahlilchisisiz. O'zbek tilida professional va konstruktiv fikr bildirasiz."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            ai_opinion = response.choices[0].message.content
            return ai_opinion
            
        except Exception as e:
            logger.error(f"AI tahlilida xatolik: {str(e)}")
            return f"⚠️ AI tahlilida xatolik yuz berdi: {str(e)}"
    
    def is_available(self) -> bool:
        return self.client is not None
