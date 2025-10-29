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
            
            prompt = f"""Test natijalari:
👥 {n_persons} talaba | 📝 {n_items} savol | 📊 Reliability: {reliability:.3f}
📈 O'rtacha: {avg_score:.1f}/{n_items} | T-Score: {avg_t_score:.1f}
🏆 A+/A: {grade_counts['A+']+grade_counts['A']} | ⚠️ NC: {grade_counts['NC']}

JUDA QISQA (5-7 qator) va ANIQ yozing:
1️⃣ Test holati: yaxshi/o'rtacha/yomon? Nima uchun?
2️⃣ ENG MUHIM muammo (bitta!)
3️⃣ ASOSIY tavsiya (bitta!)

Emoji ishlatib, sodda va qiziq yozing. Rasmiy emas, do'stona."""

            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "Siz do'stona pedagog bo'lib, qisqa va aniq fikr bildirasiz. Emoji ishlatib, sodda tilda gaplashing. Ortiqcha rasmiyatsiz!"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=400
            )
            
            ai_opinion = response.choices[0].message.content
            return ai_opinion
            
        except Exception as e:
            logger.error(f"AI tahlilida xatolik: {str(e)}")
            return f"⚠️ AI tahlilida xatolik yuz berdi: {str(e)}"
    
    def is_available(self) -> bool:
        return self.client is not None
