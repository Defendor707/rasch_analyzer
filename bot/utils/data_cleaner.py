
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
        is_valid, validation_msg = self._validate_binary_data(df)
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
        """Remove columns that contain metadata (names, IDs, timestamps) not responses"""
        columns_to_remove = []
        
        for col in df.columns:
            col_data = df[col]
            
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
                    # Check for common metadata patterns
                    sample = str(non_null.iloc[0]).lower()
                    metadata_keywords = ['name', 'email', 'id', 'time', 'date', 'user', 
                                       'ism', 'familiya', 'telegram', '@']
                    
                    if any(keyword in sample for keyword in metadata_keywords) or \
                       any(keyword in str(col).lower() for keyword in metadata_keywords):
                        columns_to_remove.append(col)
                        metadata['removed_columns'].append({
                            'name': str(col),
                            'reason': 'Metadata column (text/names)',
                            'sample': str(non_null.iloc[0])[:50]
                        })
                        continue
                    
                    # If mostly unique values (like names), it's probably metadata
                    unique_ratio = len(non_null.unique()) / len(non_null)
                    if unique_ratio > 0.8:  # More than 80% unique
                        columns_to_remove.append(col)
                        metadata['removed_columns'].append({
                            'name': str(col),
                            'reason': 'High unique ratio (likely identifiers)',
                            'unique_ratio': unique_ratio
                        })
        
        if columns_to_remove:
            df = df.drop(columns=columns_to_remove)
            logger.info(f"Removed {len(columns_to_remove)} metadata columns")
        
        return df
    
    def _convert_to_numeric(self, df: pd.DataFrame, metadata: Dict) -> pd.DataFrame:
        """Convert all columns to numeric, handling errors"""
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Fill NaN with 0 (assuming unanswered = incorrect)
        nan_count = df.isna().sum().sum()
        if nan_count > 0:
            metadata['warnings'].append(f"{nan_count} ta bo'sh qiymat 0 ga almashtirildi")
            df = df.fillna(0)
        
        return df
    
    def _validate_binary_data(self, df: pd.DataFrame) -> Tuple[bool, str]:
        """Check if data is mostly binary (0 and 1)"""
        total_values = df.size
        binary_values = np.isin(df.values, [0, 1, 0.0, 1.0]).sum()
        binary_ratio = binary_values / total_values if total_values > 0 else 0
        
        if binary_ratio < self.min_binary_ratio:
            return False, (
                f"Ogohlantirish: Faqat {binary_ratio*100:.1f}% qiymatlar 0 yoki 1. "
                f"Rasch analizi uchun dikotomik (0/1) ma'lumotlar talab qilinadi."
            )
        
        return True, f"Ma'lumotlar to'g'ri: {binary_ratio*100:.1f}% dikotomik qiymatlar"
    
    def _standardize_column_names(self, df: pd.DataFrame, metadata: Dict) -> pd.DataFrame:
        """Rename columns to standard format (Savol_1, Savol_2, etc.)"""
        n_items = len(df.columns)
        new_columns = [f"Savol_{i+1}" for i in range(n_items)]
        
        old_columns = list(df.columns)
        df.columns = new_columns
        
        metadata['column_mapping'] = dict(zip(new_columns, old_columns))
        
        return df
    
    def get_cleaning_report(self, metadata: Dict) -> str:
        """Generate a human-readable cleaning report"""
        report = []
        report.append("📋 Fayl tozalash hisoboti\n")
        report.append(f"Asl o'lcham: {metadata['original_shape'][0]} qator × {metadata['original_shape'][1]} ustun")
        report.append(f"Yakuniy o'lcham: {metadata['final_shape'][0]} talabgor × {metadata['final_shape'][1]} savol\n")
        
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
        
        if metadata['warnings']:
            report.append("⚠️ Ogohlantirishlar:")
            for warning in metadata['warnings']:
                report.append(f"  • {warning}")
        
        return "\n".join(report)
