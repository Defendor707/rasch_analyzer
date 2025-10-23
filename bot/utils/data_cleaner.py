
import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any
import logging

logger = logging.getLogger(__name__)


class DataCleaner:
    """Smart data cleaner for test export files from various platforms"""
    
    def __init__(self):
        self.min_binary_ratio = 0.7  # At least 70% of values should be 0 or 1
        
    def clean_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Clean and prepare data for Rasch analysis
        
        Args:
            df: Raw DataFrame from uploaded file
            
        Returns:
            Tuple of (cleaned_df, metadata_dict)
        """
        metadata = {
            'original_shape': df.shape,
            'removed_columns': [],
            'removed_rows': [],
            'warnings': []
        }
        
        logger.info(f"Starting data cleaning. Original shape: {df.shape}")
        
        # Step 1: Remove completely empty rows and columns
        df = self._remove_empty_rows_cols(df, metadata)
        
        # Step 2: Detect and remove header/metadata rows
        df = self._remove_metadata_rows(df, metadata)
        
        # Step 3: Detect and remove non-response columns (names, IDs, timestamps, etc.)
        df = self._remove_metadata_columns(df, metadata)
        
        # Step 4: Convert to numeric and handle missing values
        df = self._convert_to_numeric(df, metadata)
        
        # Step 5: Validate that we have binary data
        is_valid, validation_msg = self._validate_binary_data(df, metadata)
        if not is_valid:
            metadata['warnings'].append(validation_msg)
        
        # Step 6: Clean column names (rename to Item1, Item2, etc.)
        df = self._standardize_column_names(df, metadata)
        
        metadata['final_shape'] = df.shape
        
        logger.info(f"Data cleaning completed. Final shape: {df.shape}")
        logger.info(f"Removed {len(metadata['removed_columns'])} columns, {len(metadata['removed_rows'])} rows")
        
        return df, metadata
    
    def _remove_empty_rows_cols(self, df: pd.DataFrame, metadata: Dict) -> pd.DataFrame:
        """Remove completely empty rows and columns"""
        initial_shape = df.shape
        
        # Remove empty columns
        df = df.dropna(axis=1, how='all')
        
        # Remove empty rows
        df = df.dropna(axis=0, how='all')
        
        if df.shape != initial_shape:
            logger.info(f"Removed empty rows/columns: {initial_shape} -> {df.shape}")
        
        return df
    
    def _remove_metadata_rows(self, df: pd.DataFrame, metadata: Dict) -> pd.DataFrame:
        """Remove header/metadata rows that contain text or non-response data"""
        rows_to_remove = []
        
        for idx in range(min(5, len(df))):  # Check first 5 rows
            row = df.iloc[idx]
            
            # Check if row contains mostly text (not numbers)
            try:
                numeric_count = pd.to_numeric(row, errors='coerce').notna().sum()
                total_count = row.notna().sum()
                
                if total_count > 0 and numeric_count / total_count < 0.5:
                    # More than 50% non-numeric - likely a header row
                    rows_to_remove.append(idx)
                    metadata['removed_rows'].append({
                        'index': idx,
                        'reason': 'Header/metadata row',
                        'sample': str(row.iloc[:3].tolist())
                    })
            except Exception:
                pass
        
        if rows_to_remove:
            df = df.drop(rows_to_remove).reset_index(drop=True)
            logger.info(f"Removed {len(rows_to_remove)} metadata rows")
        
        return df
    
    def _remove_metadata_columns(self, df: pd.DataFrame, metadata: Dict) -> pd.DataFrame:
        """Remove columns that contain metadata (names, IDs, timestamps) not responses
        
        IMPORTANT: Preserves the first column and any column with participant/student names
        """
        columns_to_remove = []
        preserved_participant_columns = []  # Track which columns contain participant names
        first_column = df.columns[0] if len(df.columns) > 0 else None
        
        # Keywords that indicate this is a participant name column (KEEP these)
        participant_name_keywords = [
            'talabgor', 'f.i.o', 'fio', 'student', 'participant', 
            'o\'quvchi', 'oquvchi', 'abituriyent', 'ism-familiya',
            'full name', 'fullname', 'name surname', 'ism', 'name'
        ]
        
        for col_idx, col in enumerate(df.columns):
            col_data = df[col]
            col_name_lower = str(col).lower()
            
            # ALWAYS keep the first column (usually participant names)
            if col_idx == 0:
                preserved_participant_columns.append(col)
                logger.info(f"Keeping first column as participant names: {col}")
                continue
            
            # ALWAYS keep columns with participant name keywords in column name
            if any(keyword in col_name_lower for keyword in participant_name_keywords):
                preserved_participant_columns.append(col)
                logger.info(f"Keeping participant name column: {col}")
                continue
            
            # Skip if already numeric and looks like response data
            try:
                numeric_data = pd.to_numeric(col_data, errors='coerce')
                if numeric_data.notna().sum() / len(col_data) > 0.8:
                    # Check if values are mostly 0 or 1
                    unique_vals = numeric_data.dropna().unique()
                    if len(unique_vals) <= 10:  # Small number of unique values
                        binary_count = np.isin(unique_vals, [0, 1, 0.0, 1.0]).sum()
                        if binary_count >= len(unique_vals) * 0.5:
                            continue  # This looks like response data
            except Exception:
                pass
            
            # Check if column contains text/string data
            if col_data.dtype == 'object':
                # Check if it's mostly text (names, emails, etc.)
                non_null = col_data.dropna()
                if len(non_null) > 0:
                    # Check for OTHER metadata patterns (NOT participant names)
                    # Remove keywords like email, telegram, timestamp, ID
                    sample = str(non_null.iloc[0]).lower()
                    removable_metadata_keywords = ['email', 'time', 'date', 'telegram', '@', 
                                                   'timestamp', 'created', 'updated', 'phone']
                    
                    if any(keyword in sample for keyword in removable_metadata_keywords) or \
                       any(keyword in col_name_lower for keyword in removable_metadata_keywords):
                        columns_to_remove.append(col)
                        metadata['removed_columns'].append({
                            'name': str(col),
                            'reason': 'Metadata column (email/time/ID)',
                            'sample': str(non_null.iloc[0])[:50]
                        })
                        continue
                    
                    # If mostly unique values AND not participant names, likely an identifier to remove
                    unique_ratio = len(non_null.unique()) / len(non_null)
                    if unique_ratio > 0.95:  # Increased threshold - very high uniqueness
                        # Check if this looks like an ID column
                        if any(id_keyword in col_name_lower for id_keyword in ['id', 'uuid', 'guid', 'code']):
                            columns_to_remove.append(col)
                            metadata['removed_columns'].append({
                                'name': str(col),
                                'reason': 'ID column (high unique ratio + ID keyword)',
                                'unique_ratio': unique_ratio
                            })
        
        if columns_to_remove:
            df = df.drop(columns=columns_to_remove)
            logger.info(f"Removed {len(columns_to_remove)} metadata columns")
        
        # Store preserved participant columns in metadata for later use
        metadata['preserved_participant_columns'] = preserved_participant_columns
        logger.info(f"Preserved {len(preserved_participant_columns)} participant columns: {preserved_participant_columns}")
        
        return df
    
    def _convert_to_numeric(self, df: pd.DataFrame, metadata: Dict) -> pd.DataFrame:
        """Convert response columns to numeric, but preserve ALL participant name columns"""
        # Get list of preserved participant columns from metadata
        preserved_columns = metadata.get('preserved_participant_columns', [])
        
        # Save original data for preserved columns
        preserved_data = {}
        for col in preserved_columns:
            if col in df.columns and df[col].dtype == 'object':
                preserved_data[col] = df[col].copy()
                logger.info(f"Saving participant column data: {col}")
        
        # Convert all columns to numeric
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Restore all preserved participant columns
        for col, data in preserved_data.items():
            df[col] = data
            logger.info(f"Restored participant column: {col}")
        
        # Fill NaN with 0 in RESPONSE columns only (skip preserved participant columns)
        response_columns = [col for col in df.columns if col not in preserved_columns]
        if response_columns:
            nan_count = df[response_columns].isna().sum().sum()
            if nan_count > 0:
                metadata['warnings'].append(f"{nan_count} ta bo'sh qiymat 0 ga almashtirildi")
                df[response_columns] = df[response_columns].fillna(0)
        
        return df
    
    def _validate_binary_data(self, df: pd.DataFrame, metadata: Dict) -> Tuple[bool, str]:
        """Check if response data is mostly binary (0 and 1), excluding participant columns"""
        # Get preserved participant columns from metadata
        preserved_columns = metadata.get('preserved_participant_columns', [])
        
        # Validate only response columns (exclude preserved participant columns)
        response_columns = [col for col in df.columns if col not in preserved_columns]
        
        if not response_columns:
            return False, "Xatolik: Javob ustunlari topilmadi"
        
        response_data = df[response_columns]
        
        total_values = response_data.size
        binary_values = np.isin(response_data.values, [0, 1, 0.0, 1.0]).sum()
        binary_ratio = binary_values / total_values if total_values > 0 else 0
        
        if binary_ratio < self.min_binary_ratio:
            return False, (
                f"Ogohlantirish: Faqat {binary_ratio*100:.1f}% qiymatlar 0 yoki 1. "
                f"Rasch analizi uchun dikotomik (0/1) ma'lumotlar talab qilinadi."
            )
        
        return True, f"Ma'lumotlar to'g'ri: {binary_ratio*100:.1f}% dikotomik qiymatlar"
    
    def _standardize_column_names(self, df: pd.DataFrame, metadata: Dict) -> pd.DataFrame:
        """Rename columns to standard format: Preserved participant columns first, then Savol_1, Savol_2, etc."""
        n_cols = len(df.columns)
        
        if n_cols == 0:
            return df
        
        # Get list of preserved participant columns
        preserved_columns = metadata.get('preserved_participant_columns', [])
        old_columns = list(df.columns)
        
        # Create mapping for new column names
        new_columns = []
        savol_counter = 1
        participant_counter = 1
        
        for col in old_columns:
            if col in preserved_columns:
                # This is a participant name column
                if participant_counter == 1:
                    new_columns.append('Talabgor')
                else:
                    new_columns.append(f'Talabgor_{participant_counter}')
                participant_counter += 1
            else:
                # This is a response column
                new_columns.append(f'Savol_{savol_counter}')
                savol_counter += 1
        
        df.columns = new_columns
        metadata['column_mapping'] = dict(zip(new_columns, old_columns))
        
        logger.info(f"Standardized column names: {len(preserved_columns)} participant columns, {savol_counter-1} response columns")
        for new_name, old_name in zip(new_columns[:5], old_columns[:5]):
            logger.info(f"  {old_name} → {new_name}")
        
        return df
    
    def standardize_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Standartlashtirish - faqat ustun nomlarini o'zgartiradi
        Birinchi ustunni Talabgor deb nomlaydi, qolganlarini Savol_1, Savol_2, ... formatiga keltiradi
        
        Args:
            df: DataFrame (har qanday shaklda)
            
        Returns:
            Tuple of (standardized_df, metadata_dict)
        """
        metadata = {
            'original_shape': df.shape,
            'original_columns': list(df.columns),
            'operation': 'standardization_only',
            'removed_columns': [],
            'removed_rows': [],
            'warnings': []
        }
        
        logger.info(f"Starting data standardization. Shape: {df.shape}")
        
        # Mark first column as participant column (always preserve it)
        if len(df.columns) > 0:
            metadata['preserved_participant_columns'] = [df.columns[0]]
        else:
            metadata['preserved_participant_columns'] = []
        
        # Faqat ustun nomlarini o'zgartirish
        df = self._standardize_column_names(df, metadata)
        
        metadata['final_shape'] = df.shape
        
        logger.info(f"Data standardization completed. Final shape: {df.shape}")
        
        return df, metadata
    
    def get_cleaning_report(self, metadata: Dict) -> str:
        """Generate a human-readable cleaning report"""
        report = []
        report.append("📋 Fayl tozalash hisoboti\n")
        report.append(f"Asl o'lcham: {metadata['original_shape'][0]} qator × {metadata['original_shape'][1]} ustun")
        
        # Calculate columns: participant columns + response columns
        final_shape = metadata['final_shape']
        preserved_columns = metadata.get('preserved_participant_columns', [])
        participant_cols = len(preserved_columns)
        response_cols = final_shape[1] - participant_cols if final_shape[1] > 0 else 0
        
        report.append(f"Yakuniy o'lcham: {final_shape[0]} talabgor × {final_shape[1]} ustun")
        if participant_cols == 1:
            report.append(f"  • 1 ta talabgorlar ustuni (Talabgor)")
        elif participant_cols > 1:
            report.append(f"  • {participant_cols} ta talabgorlar ustuni (Talabgor, Talabgor_2, ...)")
        if response_cols > 0:
            report.append(f"  • {response_cols} ta javob ustuni (Savol_1 ... Savol_{response_cols})\n")
        else:
            report.append("")
        
        if metadata['removed_rows']:
            report.append(f"O'chirilgan qatorlar: {len(metadata['removed_rows'])} ta")
            for row in metadata['removed_rows'][:3]:  # Show first 3
                report.append(f"  • Qator {row['index']}: {row['reason']}")
            if len(metadata['removed_rows']) > 3:
                report.append(f"  • ... va yana {len(metadata['removed_rows']) - 3} ta")
            report.append("")
        
        if metadata['removed_columns']:
            report.append(f"O'chirilgan ustunlar: {len(metadata['removed_columns'])} ta")
            for col in metadata['removed_columns'][:3]:  # Show first 3
                report.append(f"  • {col['name']}: {col['reason']}")
            if len(metadata['removed_columns']) > 3:
                report.append(f"  • ... va yana {len(metadata['removed_columns']) - 3} ta")
            report.append("")
        
        report.append("✅ Saqlanganlar:")
        report.append("  • Talabgorlar ism-familyasi (birinchi ustun)")
        report.append("  • Barcha javob ustunlari (0/1 matritsasi)\n")
        
        if metadata['warnings']:
            report.append("⚠️ Ogohlantirishlar:")
            for warning in metadata['warnings']:
                report.append(f"  • {warning}")
        
        return "\n".join(report)
    
    def get_standardization_report(self, metadata: Dict) -> str:
        """Generate a report for standardization-only operation"""
        report = []
        report.append("📋 Standartlashtirish hisoboti\n")
        
        final_shape = metadata['final_shape']
        response_cols = final_shape[1] - 1 if final_shape[1] > 0 else 0
        
        report.append(f"O'lcham: {final_shape[0]} qator × {final_shape[1]} ustun")
        report.append(f"\n✅ Ustun nomlari standart shaklga keltirildi:")
        report.append(f"   • Talabgor (birinchi ustun - ism-familya)")
        if response_cols > 0:
            report.append(f"   • Savol_1, Savol_2, ... Savol_{response_cols}")
        
        if 'column_mapping' in metadata and len(metadata['column_mapping']) > 0:
            report.append(f"\n📝 Eski ustun nomlari:")
            mapping_items = list(metadata['column_mapping'].items())
            for new_name, old_name in mapping_items[:5]:
                report.append(f"   {new_name} ← {old_name}")
            if len(mapping_items) > 5:
                report.append(f"   ... va yana {len(mapping_items) - 5} ta ustun")
        
        return "\n".join(report)
