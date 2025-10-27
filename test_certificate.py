"""
Sertifikat funksiyasini test qilish uchun skript
"""
import asyncio
import logging
from bot.utils.pdf_generator import PDFReportGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_certificate_generation():
    """Test certificate generation"""
    try:
        logger.info("Sertifikat yaratish testi boshlanmoqda...")
        
        pdf_generator = PDFReportGenerator()
        
        # Test ma'lumotlari
        test_data = {
            'student_name': 'Abbos Rahimov',
            'test_name': 'Matematika asoslari',
            'subject': 'Matematika',
            'score': 45,
            'max_score': 50,
            'percentage': 90.0,
            'theta': 1.5,
            't_score': 65.0
        }
        
        # Sertifikat yaratish
        cert_path = pdf_generator.generate_certificate(
            student_name=test_data['student_name'],
            test_name=test_data['test_name'],
            subject=test_data['subject'],
            score=test_data['score'],
            max_score=test_data['max_score'],
            percentage=test_data['percentage'],
            theta=test_data['theta'],
            t_score=test_data['t_score'],
            filename='test_certificate_demo'
        )
        
        logger.info(f"✅ Sertifikat muvaffaqiyatli yaratildi: {cert_path}")
        return cert_path
        
    except Exception as e:
        logger.error(f"❌ Xatolik: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == '__main__':
    result = asyncio.run(test_certificate_generation())
    if result:
        print(f"\n✅ Sertifikat yaratildi: {result}")
        print("Fayl data/results/ papkasida joylashgan")
    else:
        print("\n❌ Sertifikat yaratilmadi")
