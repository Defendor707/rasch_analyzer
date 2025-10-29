
import os
from openai import OpenAI
from typing import Dict, Any
import logging
import numpy as np

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
            # Extract comprehensive data
            n_persons = results.get('n_persons', 0)
            n_items = results.get('n_items', 0)
            reliability = results.get('reliability', 0)
            
            # Item difficulty analysis
            item_difficulties = results.get('item_difficulty', [])
            item_names = results.get('item_names', [])
            
            # Person statistics
            person_stats = results.get('person_statistics', {})
            individual_data = person_stats.get('individual', [])
            ability_mean = person_stats.get('ability_mean', 0)
            ability_sd = person_stats.get('ability_sd', 0)
            
            if not individual_data:
                return "⚠️ AI tahlili uchun ma'lumotlar topilmadi"
            
            # Calculate detailed statistics
            scores = [p['raw_score'] for p in individual_data if 'raw_score' in p]
            abilities = [p['ability'] for p in individual_data if 'ability' in p and not np.isnan(p['ability'])]
            t_scores = [p['t_score'] for p in individual_data if 't_score' in p and not np.isnan(p['t_score'])]
            se_values = [p['se'] for p in individual_data if 'se' in p and not np.isnan(p['se'])]
            
            if not scores or not t_scores or not abilities:
                return "⚠️ AI tahlili uchun ball ma'lumotlari topilmadi"
            
            # Basic statistics
            avg_score = sum(scores) / len(scores)
            max_score = max(scores)
            min_score = min(scores)
            avg_t_score = sum(t_scores) / len(t_scores)
            avg_ability = sum(abilities) / len(abilities)
            avg_se = sum(se_values) / len(se_values) if se_values else 0
            
            # Item difficulty analysis
            if item_difficulties and len(item_difficulties) > 0:
                avg_item_diff = float(np.mean(item_difficulties))
                item_diff_sd = float(np.std(item_difficulties))
                easiest_items = sorted(enumerate(item_difficulties), key=lambda x: x[1])[:3]
                hardest_items = sorted(enumerate(item_difficulties), key=lambda x: x[1], reverse=True)[:3]
            else:
                avg_item_diff = 0
                item_diff_sd = 0
                easiest_items = []
                hardest_items = []
            
            # Person-item alignment (targeting)
            item_person_match = abs(avg_item_diff - avg_ability)
            
            # Grade distribution
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
            
            # Calculate percentages
            excellent_pct = ((grade_counts['A+'] + grade_counts['A']) / n_persons) * 100
            failing_pct = (grade_counts['NC'] / n_persons) * 100
            
            # Build comprehensive prompt for AI
            prompt = f"""Siz pedagog-tadqiqotchi sifatida Rasch Model (IRT 1PL) natijalarini tahlil qilasiz.

📊 **TEST MA'LUMOTLARI**
• Talabalar: {n_persons} ta
• Savollar: {n_items} ta
• Reliability (Person Separation): {reliability:.3f}

📈 **BALL TAQSIMOTI**
• O'rtacha ball: {avg_score:.1f}/{n_items} ({(avg_score/n_items)*100:.1f}%)
• Eng yuqori: {max_score}/{n_items}
• Eng past: {min_score}/{n_items}
• T-Score o'rtacha: {avg_t_score:.1f}

🎯 **RASCH MODEL KO'RSATKICHLARI**
• Person Ability (θ) o'rtacha: {avg_ability:.3f} (SD: {ability_sd:.3f})
• Item Difficulty (β) o'rtacha: {avg_item_diff:.3f} (SD: {item_diff_sd:.3f})
• Person-Item Targeting: {item_person_match:.3f} (0ga yaqin = yaxshi)
• O'rtacha Standard Error: {avg_se:.3f}

📝 **SAVOL TAHLILI**
{"• Eng oson savollar: " + ", ".join([f"{item_names[i]} (β={item_difficulties[i]:.2f})" for i, _ in easiest_items[:3]]) if easiest_items else "Ma'lumot yo'q"}
{"• Eng qiyin savollar: " + ", ".join([f"{item_names[i]} (β={item_difficulties[i]:.2f})" for i, _ in hardest_items[:3]]) if hardest_items else "Ma'lumot yo'q"}

🏆 **NATIJALAR TAQSIMOTI**
• A-daraja (A+/A): {grade_counts['A+']+grade_counts['A']} ta ({excellent_pct:.1f}%)
• B-daraja (B+/B): {grade_counts['B+']+grade_counts['B']} ta
• C-daraja (C+/C): {grade_counts['C+']+grade_counts['C']} ta
• NC (baholash chegarasidan past): {grade_counts['NC']} ta ({failing_pct:.1f}%)

TAHLIL VAZIFASI (15-20 qator):

1️⃣ **Reliability tahlili** ({reliability:.3f}):
   - 0.7+ bo'lsa: "Test yuqori ishonchli"
   - 0.5-0.7: "O'rtacha ishonchli"
   - 0.5 dan past: "Past ishonchli, qayta ko'rib chiqish kerak"
   - Sabablari va yechim yo'llari

2️⃣ **Person-Item Targeting** ({item_person_match:.3f}):
   - 0.5 dan kichik: "Yaxshi - savol qiyinligi talabalar darajasiga mos"
   - 0.5-1.0: "Qoniqarli"
   - 1.0 dan katta: "Muammo - savol qiyinligi mos kelmayapti"
   - Aniq tavsiyalar

3️⃣ **Item Difficulty taqsimoti**:
   - Eng oson va qiyin savollarni izohlash
   - Savol qiyinligi taqsimoti to'g'ri yoki noto'g'riligi
   - Qanday savollar qo'shish kerakligi

4️⃣ **Talabalar natijalari**:
   - Natijalar taqsimoti normal yoki yo'qligi
   - NC talabalar uchun aniq tavsiyalar
   - Qanday qo'shimcha yordam kerakligi

5️⃣ **ASOSIY XULOSALAR va TAVSIYALAR**:
   - 3 ta eng muhim muammo
   - Har bir muammo uchun aniq yechim
   - Keyingi testlar uchun tavsiyalar

Shuni yodda tuting:
• Rasch modeli terminologiyasini ishlatib tushuntiring
• Pedagog-tadqiqotchi sifatida professional yondoshing
• Aniq, amaliy tavsiyalar bering
• Emoji ishlatib, o'qish oson bo'lsin"""

            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {
                        "role": "system", 
                        "content": "Siz Rasch Model (IRT) bo'yicha mutaxassis pedagog-tadqiqotchisiz. O'zbek tilida professional, lekin tushunarli tahlil berasiz. Rasch model terminologiyasini (Person Ability, Item Difficulty, Reliability, Targeting) ishlatib, chuqur va foydali tavsiyalar berasiz. Har doim aniq, amaliy yo'riqnomalar taqdim etasiz."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            ai_opinion = response.choices[0].message.content
            return ai_opinion
            
        except Exception as e:
            logger.error(f"AI tahlilida xatolik: {str(e)}")
            return f"⚠️ AI tahlilida xatolik yuz berdi: {str(e)}"
    
    def is_available(self) -> bool:
        return self.client is not None
