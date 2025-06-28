#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具类模块
提供文件处理、数据清理和性能优化功能
"""

import os
import re
import hashlib
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union, Any
import pandas as pd
import numpy as np
from loguru import logger
from config import Config


class FileUtils:
    """文件处理工具类"""
    
    @staticmethod
    def validate_pdf_file(file_path: Union[str, Path]) -> Tuple[bool, str]:
        """验证PDF文件
        
        Returns:
            (is_valid, error_message)
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            return False, Config.ERROR_MESSAGES['file_not_found']
        
        if file_path.stat().st_size > Config.MAX_FILE_SIZE:
            return False, Config.ERROR_MESSAGES['file_too_large']
        
        if file_path.suffix.lower() != '.pdf':
            return False, Config.ERROR_MESSAGES['invalid_format']
        
        return True, ""
    
    @staticmethod
    def get_file_hash(file_path: Union[str, Path]) -> str:
        """获取文件MD5哈希值"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(Config.CHUNK_SIZE), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    @staticmethod
    def create_temp_file(suffix: str = '.pdf') -> str:
        """创建临时文件"""
        temp_dir = Config.get_temp_dir()
        fd, temp_path = tempfile.mkstemp(suffix=suffix, dir=temp_dir)
        os.close(fd)
        return temp_path
    
    @staticmethod
    def cleanup_temp_file(file_path: str):
        """清理临时文件"""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
        except Exception as e:
            logger.warning(f"清理临时文件失败: {e}")
    
    @staticmethod
    def get_safe_filename(filename: str) -> str:
        """获取安全的文件名"""
        # 移除或替换不安全的字符
        safe_chars = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # 限制长度
        if len(safe_chars) > 200:
            name, ext = os.path.splitext(safe_chars)
            safe_chars = name[:200-len(ext)] + ext
        return safe_chars
    
    @staticmethod
    def ensure_directory(dir_path: Union[str, Path]):
        """确保目录存在"""
        Path(dir_path).mkdir(parents=True, exist_ok=True)


class DataUtils:
    """数据处理工具类"""
    
    @staticmethod
    def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """清理DataFrame数据"""
        if df.empty:
            return df
        
        # 创建副本避免修改原数据
        df_clean = df.copy()
        
        # 移除完全空白的行和列
        df_clean = df_clean.dropna(how='all').dropna(axis=1, how='all')
        
        if df_clean.empty:
            return df_clean
        
        # 清理字符串数据
        for col in df_clean.columns:
            if df_clean[col].dtype == 'object':
                # 转换为字符串并清理
                df_clean[col] = df_clean[col].astype(str)
                df_clean[col] = df_clean[col].str.strip()
                
                # 替换常见的空值表示
                df_clean[col] = df_clean[col].replace({
                    'nan': '',
                    'None': '',
                    'null': '',
                    'NULL': '',
                    'NaN': '',
                    '<NA>': ''
                })
                
                # 移除多余的空白字符
                df_clean[col] = df_clean[col].str.replace(r'\s+', ' ', regex=True)
        
        # 尝试自动检测和转换数值列
        df_clean = DataUtils._auto_convert_types(df_clean)
        
        return df_clean
    
    @staticmethod
    def _auto_convert_types(df: pd.DataFrame) -> pd.DataFrame:
        """自动转换数据类型"""
        for col in df.columns:
            if df[col].dtype == 'object':
                # 尝试转换为数值类型
                try:
                    # 移除货币符号和千位分隔符
                    cleaned_series = df[col].str.replace(r'[,$¥€£]', '', regex=True)
                    cleaned_series = cleaned_series.str.replace(r'[()]', '', regex=True)
                    
                    # 尝试转换为数值
                    numeric_series = pd.to_numeric(cleaned_series, errors='coerce')
                    
                    # 如果转换成功的比例超过80%，则使用数值类型
                    if numeric_series.notna().sum() / len(df) > 0.8:
                        df[col] = numeric_series
                        continue
                except Exception:
                    pass
                
                # 尝试转换为日期类型
                try:
                    date_series = pd.to_datetime(df[col], errors='coerce', infer_datetime_format=True)
                    if date_series.notna().sum() / len(df) > 0.8:
                        df[col] = date_series
                except Exception:
                    pass
        
        return df
    
    @staticmethod
    def merge_similar_tables(tables: List[pd.DataFrame], similarity_threshold: float = 0.8) -> List[pd.DataFrame]:
        """合并相似的表格"""
        if len(tables) <= 1:
            return tables
        
        merged_tables = []
        used_indices = set()
        
        for i, table1 in enumerate(tables):
            if i in used_indices:
                continue
            
            similar_tables = [table1]
            used_indices.add(i)
            
            for j, table2 in enumerate(tables[i+1:], i+1):
                if j in used_indices:
                    continue
                
                if DataUtils._are_tables_similar(table1, table2, similarity_threshold):
                    similar_tables.append(table2)
                    used_indices.add(j)
            
            # 合并相似表格
            if len(similar_tables) > 1:
                merged_table = DataUtils._merge_tables(similar_tables)
                merged_tables.append(merged_table)
            else:
                merged_tables.append(table1)
        
        return merged_tables
    
    @staticmethod
    def _are_tables_similar(table1: pd.DataFrame, table2: pd.DataFrame, threshold: float) -> bool:
        """判断两个表格是否相似"""
        if table1.empty or table2.empty:
            return False
        
        # 比较列数
        if abs(len(table1.columns) - len(table2.columns)) > 2:
            return False
        
        # 比较列名相似度
        cols1 = set(str(col).lower().strip() for col in table1.columns)
        cols2 = set(str(col).lower().strip() for col in table2.columns)
        
        if not cols1 or not cols2:
            return False
        
        intersection = len(cols1.intersection(cols2))
        union = len(cols1.union(cols2))
        
        similarity = intersection / union if union > 0 else 0
        return similarity >= threshold
    
    @staticmethod
    def _merge_tables(tables: List[pd.DataFrame]) -> pd.DataFrame:
        """合并多个表格"""
        if not tables:
            return pd.DataFrame()
        
        if len(tables) == 1:
            return tables[0]
        
        # 找到最完整的列结构
        max_cols_table = max(tables, key=lambda t: len(t.columns))
        target_columns = max_cols_table.columns
        
        # 对齐所有表格的列
        aligned_tables = []
        for table in tables:
            aligned_table = table.reindex(columns=target_columns)
            aligned_tables.append(aligned_table)
        
        # 合并表格
        merged = pd.concat(aligned_tables, ignore_index=True)
        
        # 保留原始属性信息
        if hasattr(tables[0], 'attrs'):
            merged.attrs = tables[0].attrs.copy()
            merged.attrs['merged_from'] = len(tables)
        
        return merged
    
    @staticmethod
    def validate_table_quality(df: pd.DataFrame) -> Dict[str, Any]:
        """验证表格质量"""
        if df.empty:
            return {
                'is_valid': False,
                'score': 0.0,
                'issues': ['表格为空']
            }
        
        issues = []
        score = 1.0
        
        # 检查行数
        if len(df) < 2:
            issues.append('行数过少')
            score -= 0.3
        
        # 检查列数
        if len(df.columns) < 2:
            issues.append('列数过少')
            score -= 0.2
        
        # 检查空值比例
        null_ratio = df.isnull().sum().sum() / (len(df) * len(df.columns))
        if null_ratio > 0.5:
            issues.append(f'空值比例过高 ({null_ratio:.1%})')
            score -= 0.3
        elif null_ratio > 0.3:
            score -= 0.1
        
        # 检查重复行
        duplicate_ratio = df.duplicated().sum() / len(df)
        if duplicate_ratio > 0.5:
            issues.append(f'重复行过多 ({duplicate_ratio:.1%})')
            score -= 0.2
        
        # 检查列名质量
        unnamed_cols = sum(1 for col in df.columns if str(col).startswith('Unnamed'))
        if unnamed_cols > 0:
            issues.append(f'{unnamed_cols} 个未命名列')
            score -= 0.1
        
        return {
            'is_valid': score > 0.3,
            'score': max(0.0, score),
            'issues': issues,
            'null_ratio': null_ratio,
            'duplicate_ratio': duplicate_ratio
        }


class ExcelUtils:
    """Excel处理工具类"""
    
    @staticmethod
    def generate_sheet_name(base_name: str, index: int, attrs: Optional[Dict] = None) -> str:
        """生成工作表名称"""
        sheet_name = f"{base_name}_{index}"
        
        if attrs:
            if 'page' in attrs:
                sheet_name = f"Page_{attrs['page']}_{base_name}_{index}"
            if 'method' in attrs:
                method_short = attrs['method'].replace('_', '').replace('-', '')[:8]
                sheet_name += f"_{method_short}"
        
        # 确保名称不超过Excel限制
        if len(sheet_name) > Config.MAX_SHEET_NAME_LENGTH:
            sheet_name = sheet_name[:Config.MAX_SHEET_NAME_LENGTH]
        
        # 移除不安全字符
        sheet_name = re.sub(r'[\[\]:*?/\\]', '_', sheet_name)
        
        return sheet_name
    
    @staticmethod
    def optimize_column_widths(worksheet, df: pd.DataFrame):
        """优化列宽"""
        try:
            for idx, col in enumerate(df.columns, 1):
                # 计算列的最大宽度
                max_length = max(
                    len(str(col)),  # 列名长度
                    df[col].astype(str).str.len().max() if not df.empty else 0  # 数据最大长度
                )
                
                # 设置合理的列宽（最小8，最大50）
                adjusted_width = min(max(max_length + 2, 8), 50)
                
                # 获取列字母
                col_letter = worksheet.cell(row=1, column=idx).column_letter
                worksheet.column_dimensions[col_letter].width = adjusted_width
                
        except Exception as e:
            logger.warning(f"优化列宽失败: {e}")


class PerformanceUtils:
    """性能优化工具类"""
    
    @staticmethod
    def chunk_dataframe(df: pd.DataFrame, chunk_size: int = 1000) -> List[pd.DataFrame]:
        """分块处理大型DataFrame"""
        if len(df) <= chunk_size:
            return [df]
        
        chunks = []
        for i in range(0, len(df), chunk_size):
            chunk = df.iloc[i:i + chunk_size].copy()
            chunks.append(chunk)
        
        return chunks
    
    @staticmethod
    def estimate_memory_usage(df: pd.DataFrame) -> Dict[str, float]:
        """估算DataFrame内存使用量"""
        memory_usage = df.memory_usage(deep=True)
        total_mb = memory_usage.sum() / 1024 / 1024
        
        return {
            'total_mb': total_mb,
            'per_column_mb': {col: usage / 1024 / 1024 
                            for col, usage in memory_usage.items()},
            'is_large': total_mb > 100  # 超过100MB认为是大型数据
        }
    
    @staticmethod
    def optimize_dataframe_memory(df: pd.DataFrame) -> pd.DataFrame:
        """优化DataFrame内存使用"""
        if df.empty:
            return df
        
        df_optimized = df.copy()
        
        for col in df_optimized.columns:
            col_type = df_optimized[col].dtype
            
            if col_type == 'object':
                # 尝试转换为category类型以节省内存
                unique_ratio = len(df_optimized[col].unique()) / len(df_optimized)
                if unique_ratio < 0.5:  # 如果唯一值比例小于50%
                    try:
                        df_optimized[col] = df_optimized[col].astype('category')
                    except Exception:
                        pass
            
            elif col_type in ['int64', 'float64']:
                # 尝试降低数值类型精度
                try:
                    if col_type == 'int64':
                        if df_optimized[col].min() >= -128 and df_optimized[col].max() <= 127:
                            df_optimized[col] = df_optimized[col].astype('int8')
                        elif df_optimized[col].min() >= -32768 and df_optimized[col].max() <= 32767:
                            df_optimized[col] = df_optimized[col].astype('int16')
                        elif df_optimized[col].min() >= -2147483648 and df_optimized[col].max() <= 2147483647:
                            df_optimized[col] = df_optimized[col].astype('int32')
                    
                    elif col_type == 'float64':
                        df_optimized[col] = pd.to_numeric(df_optimized[col], downcast='float')
                        
                except Exception:
                    pass
        
        return df_optimized