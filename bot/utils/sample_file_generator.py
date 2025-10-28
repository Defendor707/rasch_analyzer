"""
Namuna Excel fayllar yaratish uchun utility
"""
import pandas as pd
import os
import logging

logger = logging.getLogger(__name__)


class SampleFileGenerator:
    """Turli formatdagi namuna fayllar yaratish"""
    
    def __init__(self, output_dir='data/samples'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def create_clean_sample(self) -> str:
        """Toza, standart format - tahlil uchun tayyor"""
        data = {
            'Talabgor': [
                'Ali Valiyev',
                'Bobur Karimov',
                'Dilnoza Tosheva',
                'Eldor Mahmudov',
                'Feruza Rustamova'
            ],
            'Q1': [1, 0, 1, 1, 0],
            'Q2': [1, 1, 1, 0, 1],
            'Q3': [0, 1, 1, 1, 1],
            'Q4': [1, 1, 0, 1, 0],
            'Q5': [1, 0, 1, 1, 1]
        }
        
        df = pd.DataFrame(data)
        filepath = os.path.join(self.output_dir, 'namuna_toza.xlsx')
        df.to_excel(filepath, index=False)
        logger.info(f"✅ Toza namuna yaratildi: {filepath}")
        return filepath
    
    def create_messy_sample(self) -> str:
        """Noto'g'ri format - File Analyzer kerak bo'lgan variant"""
        data = {
            'ID': ['001', '002', '003', '004', '005'],
            'F.I.O': [
                'Ali Valiyev',
                'Bobur Karimov', 
                'Dilnoza Tosheva',
                'Eldor Mahmudov',
                'Feruza Rustamova'
            ],
            'Email': [
                'ali@test.uz',
                'bobur@test.uz',
                'dilnoza@test.uz',
                'eldor@test.uz',
                'feruza@test.uz'
            ],
            'Telegram': [
                '@ali_v',
                '@bobur_k',
                '@dilnoza_t',
                '@eldor_m',
                '@feruza_r'
            ],
            'Savol 1': [1, 0, 1, 1, 0],
            'Savol 2': [1, 1, 1, 0, 1],
            'Savol 3': [0, 1, 1, 1, 1],
            'Savol 4': [1, 1, 0, 1, 0],
            'Savol 5': [1, 0, 1, 1, 1],
            'Ball': [4, 3, 4, 4, 3],
            'Vaqt': [
                '2024-01-15 10:30',
                '2024-01-15 11:00',
                '2024-01-15 11:30',
                '2024-01-15 12:00',
                '2024-01-15 12:30'
            ]
        }
        
        df = pd.DataFrame(data)
        filepath = os.path.join(self.output_dir, 'namuna_iflos.xlsx')
        df.to_excel(filepath, index=False)
        logger.info(f"✅ Iflos namuna yaratildi: {filepath}")
        return filepath
    
    def create_various_formats_sample(self) -> str:
        """Turli xil ustun nomlari - smart detection test uchun"""
        data = {
            'Student Name': [
                'Ali Valiyev',
                'Bobur Karimov',
                'Dilnoza Tosheva',
                'Eldor Mahmudov',
                'Feruza Rustamova'
            ],
            '1': [1, 0, 1, 1, 0],
            '2': [1, 1, 1, 0, 1],
            'matematik_3': [0, 1, 1, 1, 1],
            'fizika_4': [1, 1, 0, 1, 0],
            'mantiq_5': [1, 0, 1, 1, 1],
            'question_6': [0, 1, 1, 0, 1],
            'Item7': [1, 1, 0, 1, 1]
        }
        
        df = pd.DataFrame(data)
        filepath = os.path.join(self.output_dir, 'namuna_turli_format.xlsx')
        df.to_excel(filepath, index=False)
        logger.info(f"✅ Turli format namuna yaratildi: {filepath}")
        return filepath
    
    def create_all_samples(self):
        """Barcha namuna fayllarni yaratish"""
        samples = []
        samples.append(('Toza format', self.create_clean_sample()))
        samples.append(('Iflos format', self.create_messy_sample()))
        samples.append(('Turli formatlar', self.create_various_formats_sample()))
        
        logger.info(f"✅ {len(samples)} ta namuna fayl yaratildi")
        return samples
    
    def get_sample_description(self) -> str:
        """Namuna fayllar haqida ma'lumot"""
        description = """
📚 *NAMUNA FAYLLAR*

1️⃣ *namuna_toza.xlsx*
   Toza, standart format. Bevosita tahlil qilish mumkin.
   Ustunlar: Talabgor, Q1, Q2, Q3, ...

2️⃣ *namuna_iflos.xlsx*
   Real hayotdagi format - ortiqcha ustunlar bilan.
   File Analyzer kerak: ID, Email, Telegram, Ball, Vaqt o'chiriladi.

3️⃣ *namuna_turli_format.xlsx*
   Turli xil ustun nomlari.
   Smart detection test: "1", "matematik_3", "question_6", va h.k.

💡 Bu fayllarni yuklab oling va o'z ma'lumotlaringiz uchun namuna sifatida ishlating!
"""
        return description


# Global instance
sample_generator = SampleFileGenerator()


if __name__ == '__main__':
    # Test uchun
    logging.basicConfig(level=logging.INFO)
    generator = SampleFileGenerator()
    generator.create_all_samples()
    print("✅ Barcha namuna fayllar yaratildi!")
