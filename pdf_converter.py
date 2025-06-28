#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF转电子表格转换器
支持多种PDF表格提取方法，确保高性能和稳定性
"""

import os
import sys
import pandas as pd
import pdfplumber
import tabula
import camelot
import fitz  # PyMuPDF
from typing import List, Dict, Optional, Tuple, Union
from pathlib import Path
from loguru import logger
from tqdm import tqdm
import numpy as np
from PIL import Image
import cv2


class PDFTableExtractor:
    """PDF表格提取器 - 支持多种提取方法"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
        
        logger.info(f"初始化PDF表格提取器: {self.pdf_path}")
    
    def _clean_cid_text(self, text: str) -> str:
        """清理CID编码和特殊字符"""
        import re
        
        if not text:
            return ""
        
        # 移除CID编码格式的字符 (cid:xxxx)
        text = re.sub(r'\(cid:\d+\)', '', text)
        
        # 移除其他常见的PDF编码问题字符
        text = re.sub(r'[\uf000-\uf8ff]', '', text)  # 私有使用区字符
        text = re.sub(r'[\u0000-\u001f]', '', text)  # 控制字符
        text = re.sub(r'[\ufeff\ufffe]', '', text)  # BOM字符
        
        # 清理多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """清理DataFrame中的CID编码和重复列名"""
        if df.empty:
            return df
        
        # 清理列名中的CID编码
        new_columns = []
        for col in df.columns:
            cleaned_col = self._clean_cid_text(str(col))
            # 如果清理后为空或只有空白字符，使用默认名称
            if not cleaned_col or cleaned_col.isspace():
                cleaned_col = ''
            new_columns.append(cleaned_col)
        
        # 处理空列名和重复列名
        final_columns = []
        col_counts = {}
        
        for i, col in enumerate(new_columns):
            if not col:  # 空列名
                col = f'Column_{i+1}'
            
            # 处理重复列名
            original_col = col
            counter = 1
            while col in col_counts:
                col = f"{original_col}_{counter}"
                counter += 1
            
            col_counts[col] = True
            final_columns.append(col)
        
        # 设置新列名
        df.columns = final_columns
        
        # 清理数据中的CID编码
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).apply(self._clean_cid_text)
        
        # 最终验证：如果仍有重复列名，强制使用索引重命名
        if len(set(df.columns)) != len(df.columns):
            df.columns = [f'Column_{i+1}' for i in range(len(df.columns))]
        
        return df
    
    def extract_with_pdfplumber(self, pages: Optional[List[int]] = None) -> List[pd.DataFrame]:
        """使用pdfplumber提取表格 - 适合结构化表格"""
        tables = []
        
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                target_pages = pages or range(len(pdf.pages))
                
                for page_num in tqdm(target_pages, desc="pdfplumber提取中"):
                    if page_num >= len(pdf.pages):
                        continue
                        
                    page = pdf.pages[page_num]
                    
                    # 尝试多种表格设置以改善列检测
                    table_settings_list = [
                        {
                            "vertical_strategy": "lines_strict",
                            "horizontal_strategy": "lines_strict",
                            "snap_tolerance": 3,
                            "join_tolerance": 3,
                            "edge_min_length": 3,
                            "min_words_vertical": 3,
                            "min_words_horizontal": 1
                        },
                        {
                            "vertical_strategy": "text",
                            "horizontal_strategy": "text",
                            "snap_tolerance": 5,
                            "join_tolerance": 5
                        },
                        {
                            "vertical_strategy": "explicit",
                            "horizontal_strategy": "explicit",
                            "explicit_vertical_lines": self._detect_vertical_lines(page),
                            "explicit_horizontal_lines": self._detect_horizontal_lines(page)
                        }
                    ]
                    
                    best_tables = []
                    max_columns = 0
                    
                    for settings in table_settings_list:
                        try:
                            page_tables = page.extract_tables(table_settings=settings)
                            
                            for table in page_tables:
                                if table and len(table) > 1:
                                    # 检查列数
                                    col_count = len(table[0]) if table[0] else 0
                                    if col_count > max_columns:
                                        max_columns = col_count
                                        best_tables = [table]
                                    elif col_count == max_columns and col_count > 1:
                                        best_tables.append(table)
                                        
                        except Exception as e:
                            logger.debug(f"表格设置失败: {e}")
                            continue
                    
                    # 如果没有找到多列表格，尝试文本分割
                    if max_columns <= 1:
                        best_tables = self._extract_tables_by_text_analysis(page)
                    
                    # 处理最佳表格
                    for table in best_tables:
                        if table and len(table) > 1:
                            # 清理表格中的CID编码
                            cleaned_table = []
                            for row in table:
                                cleaned_row = [self._clean_cid_text(str(cell)) if cell else '' for cell in row]
                                cleaned_table.append(cleaned_row)
                            
                            # 处理表头
                            headers = cleaned_table[0] if cleaned_table[0] else [f'Column_{i+1}' for i in range(len(cleaned_table[0]) if cleaned_table[0] else 0)]
                            
                            # 创建DataFrame
                            df = pd.DataFrame(cleaned_table[1:], columns=headers)
                            
                            # 清理DataFrame
                            df = self._clean_dataframe(df)
                            
                            # 只移除完全空白的行，保留所有列
                            df = df.dropna(how='all')
                            
                            if not df.empty and len(df.columns) > 0:
                                df.attrs['page'] = page_num + 1
                                df.attrs['method'] = 'pdfplumber'
                                logger.debug(f"pdfplumber提取到表格: {df.shape[0]}行 x {df.shape[1]}列")
                                tables.append(df)
                                
        except Exception as e:
            logger.error(f"pdfplumber提取失败: {e}")
            
        return tables
