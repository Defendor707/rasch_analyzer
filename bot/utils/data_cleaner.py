
import pandas as pd
import numpy as np
import re
from typing import Tuple, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class DataCleaner:
    """Super aqlli data cleaner - turli xil test fayllarini aniqlash va tozalash"""
    
    def __init__(self):
        self.min_binary_ratio = 0.7  # At least 70% of values should be 0 or 1
        
        # SAVOL USTUNLARI UCHUN KEYWORDS (ko'proq variant)
        self.question_keywords = [
            # O'zbekcha
            'savol', 'savol_', 'so\'roq', 'soroq', 'test', 'topshiriq',
            # Inglizcha
            'question', 'q', 'item', 'problem', 'task', 'quiz',
            # Fanlar
            'matematik', 'mantiq', 'fizika', 'kimyo', 'biologiya',
            'ingliz', 'ona tili', 'adabiyot', 'tarix', 'geografiya',
            'informatika', 'matematika', 'algebra', 'geometriya',
            # Qisqa shakllar
            'mat', 'fiz', 'kim', 'bio', 'geo', 'inf', 'ing'
        ]
        
        # ISM-FAMILIYA USTUNLARI UCHUN KEYWORDS (ko'proq variant)
        self.participant_name_keywords = [
            # O'zbekcha
            'talabgor', 'talabgor_ismi', 'o\'quvchi', 'oquvchi', 
            'abituriyent', 'ism', 'familiya', 'f.i.o', 'fio',
            'ism-familiya', 'ismfamiliya', 'ismi', 'familyasi',
            'to\'liq ism', 'toliq_ism',
            # Inglizcha
            'student', 'participant', 'name', 'full name', 
            'fullname', 'full_name', 'student_name', 'learner',
            'candidate', 'examinee', 'name surname', 'surname',
            # Ruscha
            'фио', 'имя', 'студент', 'участник'
        ]
        
        # O'CHIRISH KERAK BO'LGAN USTUNLAR UCHUN KEYWORDS
        self.removable_metadata_keywords = [
            'email', 'e-mail', 'time', 'date', 'timestamp',
            'telegram', '@', 'phone', 'tel', 'created', 'updated',
            'id', 'uuid', 'guid', 'code', 'key', 'session',
            'duration', 'ip', 'address', 'score', 'ball', 'natija'
        ]
        
    def clean_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Faylni to'liq tozalash va tahlil uchun tayyorlash
        
        Args:
            df: Raw DataFrame from uploaded file
            
        Returns:
            Tuple of (cleaned_df, metadata_dict)
        """
        metadata = {
            'original_shape': df.shape,
            'removed_columns': [],
            'removed_rows': [],
            'warnings': [],
            'detected_question_columns': [],
            'detected_name_columns': []
        }
        
        logger.info(f"🔍 Fayl tahlili boshlandi. Asl o'lcham: {df.shape}")
        
        # Step 1: Bo'sh qatorlar va ustunlarni o'chirish
        df = self._remove_empty_rows_cols(df, metadata)
        
        # Step 2: Header/metadata qatorlarini o'chirish
        df = self._remove_metadata_rows(df, metadata)
        
        # Step 3: SUPER SMART: Savol va ism-familiya ustunlarini aniqlash
        df = self._smart_column_detection(df, metadata)
        
        # Step 4: Raqamga aylantirish va bo'sh qiymatlarni to'ldirish
        df = self._convert_to_numeric(df, metadata)
        
        # Step 5: Binary data tekshiruvi
        is_valid, validation_msg = self._validate_binary_data(df, metadata)
        if not is_valid:
            metadata['warnings'].append(validation_msg)
        
        # Step 6: Ustun nomlarini standartlashtirish
        df = self._standardize_column_names(df, metadata)
        
        metadata['final_shape'] = df.shape
        
        logger.info(f"✅ Tozalash yakunlandi. Yakuniy o'lcham: {df.shape}")
        logger.info(f"📊 Topildi: {len(metadata['detected_name_columns'])} ism ustuni, "
                   f"{len(metadata['detected_question_columns'])} savol ustuni")
        
        return df, metadata
    
    def _remove_empty_rows_cols(self, df: pd.DataFrame, metadata: Dict) -> pd.DataFrame:
        """Bo'sh qatorlar va ustunlarni o'chirish"""
        initial_shape = df.shape
        
        # Bo'sh ustunlarni o'chirish
        df = df.dropna(axis=1, how='all')
        
        # Bo'sh qatorlarni o'chirish
        df = df.dropna(axis=0, how='all')
        
        if df.shape != initial_shape:
            removed_cols = initial_shape[1] - df.shape[1]
            removed_rows = initial_shape[0] - df.shape[0]
            logger.info(f"🧹 Bo'sh ustunlar: {removed_cols}, bo'sh qatorlar: {removed_rows}")
        
        return df
    
    def _remove_metadata_rows(self, df: pd.DataFrame, metadata: Dict) -> pd.DataFrame:
        """Header va metadata qatorlarini aniqlash va o'chirish"""
        rows_to_remove = []
        
        # Faqat birinchi 10 qatorni tekshirish
        for idx in range(min(10, len(df))):
            row = df.iloc[idx]
            
            try:
                # Raqamga aylantirib ko'rish
                numeric_count = pd.to_numeric(row, errors='coerce').notna().sum()
                total_count = row.notna().sum()
                
                if total_count > 0:
                    numeric_ratio = numeric_count / total_count
                    
                    # Agar 50% dan kam raqam bo'lsa - bu header qator
                    if numeric_ratio < 0.5:
                        rows_to_remove.append(idx)
                        metadata['removed_rows'].append({
                            'index': idx,
                            'reason': 'Header/metadata qator (matn)',
                            'sample': str(row.iloc[:3].tolist())[:50]
                        })
            except Exception as e:
                logger.warning(f"Qator {idx} tahlilida xatolik: {e}")
        
        if rows_to_remove:
            df = df.drop(rows_to_remove).reset_index(drop=True)
            logger.info(f"🗑️ {len(rows_to_remove)} ta metadata qator o'chirildi")
        
        return df
    
    def _smart_column_detection(self, df: pd.DataFrame, metadata: Dict) -> pd.DataFrame:
        """
        SUPER SMART: Savol va ism-familiya ustunlarini aqlli ravishda aniqlash
        """
        columns_to_remove = []
        detected_name_columns = []
        detected_question_columns = []
        
        logger.info("🔍 SMART DETECTION: Ustunlarni tahlil qilish...")
        
        for col_idx, col in enumerate(df.columns):
            col_name = str(col).strip()
            col_name_lower = col_name.lower()
            col_data = df[col]
            
            # ===========================================
            # 1. ISM-FAMILIYA USTUNLARINI ANIQLASH
            # ===========================================
            
            # 1.1: Birinchi ustun har doim ism-familiya (default)
            if col_idx == 0:
                detected_name_columns.append(col)
                metadata['detected_name_columns'].append({
                    'column': col_name,
                    'reason': 'Birinchi ustun (default)',
                    'confidence': 'high'
                })
                logger.info(f"✅ {col_name} → ISM (birinchi ustun)")
                continue
            
            # 1.2: Keyword matching - ism-familiya uchun
            name_keyword_found = False
            for keyword in self.participant_name_keywords:
                if keyword in col_name_lower:
                    detected_name_columns.append(col)
                    metadata['detected_name_columns'].append({
                        'column': col_name,
                        'reason': f'Keyword topildi: "{keyword}"',
                        'confidence': 'high'
                    })
                    logger.info(f"✅ {col_name} → ISM (keyword: {keyword})")
                    name_keyword_found = True
                    break
            
            if name_keyword_found:
                continue
            
            # ===========================================
            # 2. SAVOL USTUNLARINI ANIQLASH
            # ===========================================
            
            is_question_column = False
            detection_reason = ""
            
            # 2.1: Raqam bilan boshlanadi (1, 2, 3, ...)
            if re.match(r'^\d+$', col_name):
                is_question_column = True
                detection_reason = f"Raqam bilan boshlangan: {col_name}"
            
            # 2.2: Q yoki q bilan boshlanadi (Q1, q2, Q_1, ...)
            elif re.match(r'^[Qq][\s_-]?\d+', col_name):
                is_question_column = True
                detection_reason = f"Q/q pattern: {col_name}"
            
            # 2.3: Savol, Question, Item keywords
            elif any(keyword in col_name_lower for keyword in self.question_keywords):
                is_question_column = True
                for keyword in self.question_keywords:
                    if keyword in col_name_lower:
                        detection_reason = f"Keyword: {keyword}"
                        break
            
            # 2.4: Item pattern (Item1, Item_2, ...)
            elif re.match(r'^item[\s_-]?\d+', col_name_lower):
                is_question_column = True
                detection_reason = f"Item pattern: {col_name}"
            
            # 2.5: Column nomi juda qisqa va boshida raqam bor
            elif len(col_name) <= 5 and any(char.isdigit() for char in col_name):
                is_question_column = True
                detection_reason = f"Qisqa nom + raqam: {col_name}"
            
            # 2.6: Binary data check - agar ko'p qiymati 0 yoki 1 bo'lsa
            if not is_question_column:
                try:
                    numeric_data = pd.to_numeric(col_data, errors='coerce')
                    if numeric_data.notna().sum() / len(col_data) > 0.7:  # 70% raqam
                        unique_vals = numeric_data.dropna().unique()
                        if len(unique_vals) <= 10:  # Kam unique qiymatlar
                            binary_count = np.isin(unique_vals, [0, 1, 0.0, 1.0]).sum()
                            if binary_count >= len(unique_vals) * 0.5:  # 50% binary
                                is_question_column = True
                                detection_reason = f"Binary data (0/1): {binary_count}/{len(unique_vals)} unique"
                except Exception:
                    pass
            
            if is_question_column:
                detected_question_columns.append(col)
                metadata['detected_question_columns'].append({
                    'column': col_name,
                    'reason': detection_reason,
                    'confidence': 'medium' if '0/1' in detection_reason else 'high'
                })
                logger.info(f"✅ {col_name} → SAVOL ({detection_reason})")
                continue
            
            # ===========================================
            # 3. O'CHIRISH KERAK BO'LGAN USTUNLAR
            # ===========================================
            
            should_remove = False
            remove_reason = ""
            
            # 3.1: Removable metadata keywords
            for keyword in self.removable_metadata_keywords:
                if keyword in col_name_lower:
                    should_remove = True
                    remove_reason = f"Metadata keyword: {keyword}"
                    break
            
            # 3.2: Matn ustunlari (email, telegram, va h.k.)
            if not should_remove and col_data.dtype == 'object':
                non_null = col_data.dropna()
                if len(non_null) > 0:
                    sample = str(non_null.iloc[0]).lower()
                    
                    # Email, @ belgisi, va h.k.
                    if '@' in sample or 'email' in sample:
                        should_remove = True
                        remove_reason = "Email/telegram ma'lumot"
                    
                    # Juda unique qiymatlar (ID, code, va h.k.)
                    elif len(non_null.unique()) / len(non_null) > 0.95:
                        if any(id_kw in col_name_lower for id_kw in ['id', 'code', 'key', 'uuid']):
                            should_remove = True
                            remove_reason = "ID ustuni (yuqori uniqueness)"
            
            if should_remove:
                columns_to_remove.append(col)
                metadata['removed_columns'].append({
                    'name': col_name,
                    'reason': remove_reason,
                    'type': 'metadata'
                })
                logger.info(f"❌ {col_name} → O'CHIRILDI ({remove_reason})")
            else:
                # Agar hech narsa aniqlanmagan bo'lsa, default savol ustuni deb hisoblash
                detected_question_columns.append(col)
                metadata['detected_question_columns'].append({
                    'column': col_name,
                    'reason': 'Default (aniqlanmadi)',
                    'confidence': 'low'
                })
                logger.info(f"⚠️ {col_name} → SAVOL (default, aniqlanmadi)")
        
        # O'chirish kerak bo'lgan ustunlarni o'chirish
        if columns_to_remove:
            df = df.drop(columns=columns_to_remove)
            logger.info(f"🗑️ {len(columns_to_remove)} ta metadata ustun o'chirildi")
        
        # Metadata'ga saqlash
        metadata['preserved_participant_columns'] = detected_name_columns
        
        logger.info(f"📊 JAMI: {len(detected_name_columns)} ism, "
                   f"{len(detected_question_columns)} savol, "
                   f"{len(columns_to_remove)} o'chirildi")
        
        return df
    
    def _convert_to_numeric(self, df: pd.DataFrame, metadata: Dict) -> pd.DataFrame:
        """Savol ustunlarini raqamga aylantirish, ism ustunlarini saqlash"""
        preserved_columns = metadata.get('preserved_participant_columns', [])
        
        # Ism ustunlari ma'lumotini saqlash
        preserved_data = {}
        for col in preserved_columns:
            if col in df.columns and df[col].dtype == 'object':
                preserved_data[col] = df[col].copy()
                logger.info(f"💾 Saqlash: {col}")
        
        # Barcha ustunlarni raqamga aylantirish
        for col in df.columns:
            if col not in preserved_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Ism ustunlarini qayta tiklash
        for col, data in preserved_data.items():
            df[col] = data
            logger.info(f"♻️ Tiklash: {col}")
        
        # Bo'sh qiymatlarni 0 ga almashtirish (faqat javob ustunlarida)
        response_columns = [col for col in df.columns if col not in preserved_columns]
        if response_columns:
            nan_count = df[response_columns].isna().sum().sum()
            if nan_count > 0:
                metadata['warnings'].append(f"{nan_count} ta bo'sh qiymat 0 ga almashtirildi")
                df[response_columns] = df[response_columns].fillna(0)
                logger.info(f"🔢 {nan_count} ta bo'sh qiymat 0 ga almashtirildi")
        
        return df
    
    def _validate_binary_data(self, df: pd.DataFrame, metadata: Dict) -> Tuple[bool, str]:
        """Binary data (0/1) ekanligini tekshirish"""
        preserved_columns = metadata.get('preserved_participant_columns', [])
        response_columns = [col for col in df.columns if col not in preserved_columns]
        
        if not response_columns:
            return False, "❌ Xatolik: Javob ustunlari topilmadi"
        
        response_data = df[response_columns]
        total_values = response_data.size
        binary_values = np.isin(response_data.values, [0, 1, 0.0, 1.0]).sum()
        binary_ratio = binary_values / total_values if total_values > 0 else 0
        
        if binary_ratio < self.min_binary_ratio:
            return False, (
                f"⚠️ Ogohlantirish: Faqat {binary_ratio*100:.1f}% qiymatlar 0 yoki 1. "
                f"Rasch analizi uchun dikotomik (0/1) ma'lumotlar kerak."
            )
        
        return True, f"✅ Ma'lumotlar to'g'ri: {binary_ratio*100:.1f}% dikotomik"
    
    def _standardize_column_names(self, df: pd.DataFrame, metadata: Dict) -> pd.DataFrame:
        """Ustun nomlarini standart formatga keltirish"""
        if len(df.columns) == 0:
            return df
        
        preserved_columns = metadata.get('preserved_participant_columns', [])
        old_columns = list(df.columns)
        new_columns = []
        savol_counter = 1
        participant_counter = 1
        
        for col in old_columns:
            if col in preserved_columns:
                # Ism-familiya ustuni
                if participant_counter == 1:
                    new_columns.append('Talabgor')
                else:
                    new_columns.append(f'Talabgor_{participant_counter}')
                participant_counter += 1
            else:
                # Savol ustuni
                new_columns.append(f'Savol_{savol_counter}')
                savol_counter += 1
        
        df.columns = new_columns
        metadata['column_mapping'] = dict(zip(new_columns, old_columns))
        
        logger.info(f"📝 Standartlashtirildi: {len(preserved_columns)} ism, "
                   f"{savol_counter-1} savol")
        
        return df
    
    def standardize_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Faqat ustun nomlarini standartlashtirish (tozalamasdan)"""
        metadata = {
            'original_shape': df.shape,
            'original_columns': list(df.columns),
            'operation': 'standardization_only',
            'removed_columns': [],
            'removed_rows': [],
            'warnings': []
        }
        
        logger.info(f"📝 Standartlashtirish: {df.shape}")
        
        # Birinchi ustunni ism ustuni deb belgilash
        if len(df.columns) > 0:
            metadata['preserved_participant_columns'] = [df.columns[0]]
        else:
            metadata['preserved_participant_columns'] = []
        
        df = self._standardize_column_names(df, metadata)
        metadata['final_shape'] = df.shape
        
        return df, metadata
    
    def get_cleaning_report(self, metadata: Dict) -> str:
        """Batafsil tozalash hisoboti"""
        report = []
        report.append("📋 *FAYL TAHLILI VA TOZALASH HISOBOTI*\n")
        
        # Asl va yakuniy o'lcham
        orig_rows, orig_cols = metadata['original_shape']
        final_rows, final_cols = metadata['final_shape']
        report.append(f"📏 Asl o'lcham: {orig_rows} qator × {orig_cols} ustun")
        report.append(f"📏 Yakuniy: {final_rows} qator × {final_cols} ustun\n")
        
        # Topilgan ustunlar
        name_cols = metadata.get('detected_name_columns', [])
        question_cols = metadata.get('detected_question_columns', [])
        
        if name_cols:
            report.append(f"✅ *ISM-FAMILIYA USTUNLARI* ({len(name_cols)} ta):")
            for item in name_cols[:3]:
                col_info = item if isinstance(item, dict) else {'column': str(item), 'reason': 'Topildi'}
                col_name = col_info.get('column', str(item))
                reason = col_info.get('reason', '')
                report.append(f"   • {col_name}")
                if reason:
                    report.append(f"     Sabab: {reason}")
            if len(name_cols) > 3:
                report.append(f"   • ... va yana {len(name_cols)-3} ta")
            report.append("")
        
        if question_cols:
            report.append(f"✅ *SAVOL USTUNLARI* ({len(question_cols)} ta):")
            for item in question_cols[:5]:
                col_info = item if isinstance(item, dict) else {'column': str(item), 'reason': 'Topildi'}
                col_name = col_info.get('column', str(item))
                reason = col_info.get('reason', '')
                report.append(f"   • {col_name}")
                if reason and 'default' not in reason.lower():
                    report.append(f"     Sabab: {reason}")
            if len(question_cols) > 5:
                report.append(f"   • ... va yana {len(question_cols)-5} ta")
            report.append("")
        
        # O'chirilgan ustunlar
        if metadata['removed_columns']:
            report.append(f"❌ *O'CHIRILGAN USTUNLAR* ({len(metadata['removed_columns'])} ta):")
            for col in metadata['removed_columns'][:5]:
                report.append(f"   • {col['name']}")
                report.append(f"     Sabab: {col['reason']}")
            if len(metadata['removed_columns']) > 5:
                report.append(f"   • ... va yana {len(metadata['removed_columns'])-5} ta")
            report.append("")
        
        # O'chirilgan qatorlar
        if metadata['removed_rows']:
            report.append(f"🗑️ *O'chirilgan qatorlar*: {len(metadata['removed_rows'])} ta")
            report.append("   (header va metadata qatorlari)\n")
        
        # Ogohlantirishlar
        if metadata['warnings']:
            report.append("⚠️ *Ogohlantirishlar*:")
            for warning in metadata['warnings']:
                report.append(f"   • {warning}")
        
        return "\n".join(report)
    
    def get_standardization_report(self, metadata: Dict) -> str:
        """Standartlashtirish hisoboti"""
        report = []
        report.append("📋 *STANDARTLASHTIRISH HISOBOTI*\n")
        
        final_rows, final_cols = metadata['final_shape']
        report.append(f"📏 O'lcham: {final_rows} qator × {final_cols} ustun\n")
        
        response_cols = final_cols - 1 if final_cols > 0 else 0
        
        report.append("✅ *Ustun nomlari standart shaklga keltirildi*:")
        report.append("   • Talabgor (ism-familiya)")
        if response_cols > 0:
            report.append(f"   • Savol_1, Savol_2, ... Savol_{response_cols}\n")
        
        if 'column_mapping' in metadata and metadata['column_mapping']:
            report.append("📝 *Eski ustun nomlari*:")
            mapping_items = list(metadata['column_mapping'].items())
            for new_name, old_name in mapping_items[:5]:
                report.append(f"   {new_name} ← {old_name}")
            if len(mapping_items) > 5:
                report.append(f"   ... va yana {len(mapping_items)-5} ta")
        
        return "\n".join(report)
    
    def create_sample_file_explanation(self) -> str:
        """Namuna fayl tushuntirish"""
        explanation = """
📄 *NAMUNA FAYL FORMATI*

File Analyzer quyidagi ustunlarni avtomatik aniqlaydi:

✅ *ISM-FAMILIYA USTUNLARI* (saqlanadi):
   • Birinchi ustun (har doim)
   • "talabgor", "ism", "name", "student" nomlari
   • "F.I.O", "full_name", "o'quvchi" va h.k.

✅ *SAVOL USTUNLARI* (saqlanadi):
   • Raqam bilan: 1, 2, 3, ...
   • Q bilan: Q1, Q2, q1, q2, ...
   • "savol", "question", "item" nomlari
   • Fanlar: "matematik", "mantiq", "fizika", ...
   • Binary data (0/1 qiymatlar)

❌ *O'CHIRILADIGAN USTUNLAR*:
   • Email, telefon, telegram
   • ID, code, timestamp
   • Vaqt, sana, address
   • Ball, natija (score)

💡 *MASLAHAT*:
Faylingizda faqat talabgor ismlari va javoblar (0/1) bo'lishi kerak. Qolgan barcha ma'lumotlar avtomatik o'chiriladi!
"""
        return explanation
