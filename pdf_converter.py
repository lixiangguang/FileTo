#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF表格提取和转换模块
支持多种提取方法，并提供表格清理和转换功能
"""

import os
import re
import time
import warnings
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union, Any, Callable

import pandas as pd
import numpy as np
from loguru import logger

# 导入配置
from config import Config
from utils import FileUtils, DataUtils, ExcelUtils, PerformanceUtils

# 忽略警告
warnings.filterwarnings('ignore')


class PDFTableExtractor:
    """PDF表格提取器
    
    支持多种提取方法：
    - pdfplumber: 适用于简单表格和文本表格
    - tabula-py: 适用于大多数标准表格
    - camelot-py: 适用于复杂表格和有线表格
    - PyMuPDF: 适用于现代PDF和图形表格
    """
    
    def __init__(self, method: str = 'auto'):
        """初始化PDF表格提取器
        
        Args:
            method: 提取方法，可选值：'auto', 'pdfplumber', 'tabula', 'camelot', 'pymupdf'
        """
        self.method = method.lower()
        self.available_methods = []
        self._check_available_methods()
        
        if self.method not in ['auto'] + self.available_methods:
            logger.warning(f"方法 '{method}' 不可用，将使用自动模式")
            self.method = 'auto'
    
    def _check_available_methods(self):
        """检查可用的提取方法"""
        # 检查pdfplumber
        try:
            import pdfplumber
            self.available_methods.append('pdfplumber')
        except ImportError:
            logger.debug("pdfplumber 未安装")
        
        # 检查tabula
        try:
            import tabula
            self.available_methods.append('tabula')
        except ImportError:
            logger.debug("tabula-py 未安装")
        
        # 检查camelot
        try:
            import camelot
            self.available_methods.append('camelot')
        except ImportError:
            logger.debug("camelot-py 未安装")
        
        # 检查PyMuPDF
        try:
            import fitz
            self.available_methods.append('pymupdf')
        except ImportError:
            logger.debug("PyMuPDF 未安装")
        
        if not self.available_methods:
            raise ImportError("没有可用的表格提取方法，请安装至少一个支持的库")
    
    def extract_tables(self, pdf_path: Union[str, Path], 
                      pages: Optional[Union[List[int], str]] = None, 
                      **kwargs) -> List[Dict]:
        """从PDF中提取表格
        
        Args:
            pdf_path: PDF文件路径
            pages: 页码列表或范围字符串，如 "1,3,5-7"，None表示所有页面
            **kwargs: 传递给具体提取方法的参数
        
        Returns:
            表格列表，每个表格为字典，包含DataFrame和元数据
        """
        pdf_path = str(pdf_path)
        
        # 验证PDF文件
        is_valid, error_msg = FileUtils.validate_pdf_file(pdf_path)
        if not is_valid:
            logger.error(f"PDF文件无效: {error_msg}")
            return []
        
        # 解析页码
        page_list = self._parse_pages(pdf_path, pages)
        if not page_list:
            logger.warning("没有有效的页码")
            return []
        
        # 自动选择方法或使用指定方法
        if self.method == 'auto':
            return self._extract_auto(pdf_path, page_list, **kwargs)
        else:
            return self._extract_with_method(self.method, pdf_path, page_list, **kwargs)
    
    def _parse_pages(self, pdf_path: str, pages: Optional[Union[List[int], str]]) -> List[int]:
        """解析页码参数"""
        if pages is None:
            # 获取PDF总页数
            try:
                import PyPDF2
                with open(pdf_path, 'rb') as f:
                    pdf = PyPDF2.PdfReader(f)
                    total_pages = len(pdf.pages)
                return list(range(1, total_pages + 1))
            except Exception as e:
                logger.error(f"获取PDF页数失败: {e}")
                return []
        
        if isinstance(pages, list):
            return [p for p in pages if p > 0]
        
        if isinstance(pages, str):
            result = []
            parts = pages.split(',')
            for part in parts:
                if '-' in part:
                    try:
                        start, end = map(int, part.split('-'))
                        if start > 0 and end >= start:
                            result.extend(range(start, end + 1))
                    except ValueError:
                        continue
                else:
                    try:
                        page = int(part)
                        if page > 0:
                            result.append(page)
                    except ValueError:
                        continue
            return result
        
        return []
    
    def _extract_auto(self, pdf_path: str, pages: List[int], **kwargs) -> List[Dict]:
        """自动选择最佳方法提取表格"""
        logger.info(f"使用自动模式提取表格，将尝试 {len(self.available_methods)} 种方法")
        
        # 尝试每种方法并评估结果
        results_by_method = {}
        scores_by_method = {}
        
        for method in Config.METHOD_PRIORITY:
            if method not in self.available_methods:
                continue
                
            logger.info(f"尝试使用 {method} 提取表格")
            start_time = time.time()
            
            try:
                tables = self._extract_with_method(method, pdf_path, pages, **kwargs)
                elapsed = time.time() - start_time
                
                # 评估表格质量
                score = self._evaluate_tables(tables, elapsed)
                
                results_by_method[method] = tables
                scores_by_method[method] = score
                
                logger.info(f"{method} 提取了 {len(tables)} 个表格，质量评分: {score:.2f}")
                
                # 如果得分足够高，直接返回结果
                if score > 0.8:
                    logger.info(f"选择 {method} 作为最佳方法")
                    return tables
                    
            except Exception as e:
                logger.warning(f"{method} 提取失败: {e}")
        
        # 选择得分最高的方法
        if scores_by_method:
            best_method = max(scores_by_method, key=scores_by_method.get)
            logger.info(f"选择 {best_method} 作为最佳方法，评分: {scores_by_method[best_method]:.2f}")
            return results_by_method[best_method]
        
        logger.warning("所有方法都失败，返回空结果")
        return []
    
    def _evaluate_tables(self, tables: List[Dict], elapsed_time: float) -> float:
        """评估表格质量"""
        if not tables:
            return 0.0
        
        total_score = 0.0
        
        # 评估表格数量 (0.2权重)
        table_count_score = min(len(tables) / 5.0, 1.0) * 0.2
        
        # 评估表格大小和质量 (0.6权重)
        quality_scores = []
        for table in tables:
            df = table['dataframe']
            if df.empty:
                continue
                
            # 计算表格大小得分
            size_score = min((len(df.columns) * len(df)) / 100.0, 1.0) * 0.5
            
            # 计算表格质量得分
            quality_result = DataUtils.validate_table_quality(df)
            quality_score = quality_result['score'] * 0.5
            
            quality_scores.append(size_score + quality_score)
        
        avg_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        quality_score = avg_quality_score * 0.6
        
        # 评估处理时间 (0.2权重)
        time_score = (1.0 / (1.0 + elapsed_time / 10.0)) * 0.2
        
        total_score = table_count_score + quality_score + time_score
        return total_score
    
    def _extract_with_method(self, method: str, pdf_path: str, 
                            pages: List[int], **kwargs) -> List[Dict]:
        """使用指定方法提取表格"""
        if method == 'pdfplumber':
            return self._extract_with_pdfplumber(pdf_path, pages, **kwargs)
        elif method == 'tabula':
            return self._extract_with_tabula(pdf_path, pages, **kwargs)
        elif method == 'camelot':
            return self._extract_with_camelot(pdf_path, pages, **kwargs)
        elif method == 'pymupdf':
            return self._extract_with_pymupdf(pdf_path, pages, **kwargs)
        else:
            logger.error(f"未知的提取方法: {method}")
            return []
    
    def _extract_with_pdfplumber(self, pdf_path: str, pages: List[int], **kwargs) -> List[Dict]:
        """使用pdfplumber提取表格"""
        import pdfplumber
        
        tables = []
        
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            
            for page_num in pages:
                if page_num > total_pages:
                    continue
                    
                try:
                    page = pdf.pages[page_num - 1]
                    page_tables = page.extract_tables()
                    
                    for i, table_data in enumerate(page_tables):
                        if not table_data or not any(row for row in table_data if any(cell for cell in row)):
                            continue
                            
                        # 转换为DataFrame
                        df = pd.DataFrame(table_data)
                        
                        # 使用第一行作为列名
                        if not df.empty and kwargs.get('use_first_row_as_header', True):
                            df.columns = df.iloc[0]
                            df = df.iloc[1:].reset_index(drop=True)
                        
                        # 清理表格
                        df = self._clean_table(df)
                        
                        if not df.empty:
                            tables.append({
                                'dataframe': df,
                                'page': page_num,
                                'table_index': i,
                                'method': 'pdfplumber',
                                'bbox': None  # pdfplumber不直接提供边界框
                            })
                except Exception as e:
                    logger.warning(f"pdfplumber处理第{page_num}页时出错: {e}")
        
        return tables
    
    def _extract_with_tabula(self, pdf_path: str, pages: List[int], **kwargs) -> List[Dict]:
        """使用tabula-py提取表格"""
        import tabula
        
        tables = []
        pages_str = ','.join(map(str, pages))
        
        try:
            # 设置tabula参数
            tabula_options = {
                'pages': pages_str,
                'multiple_tables': True,
                'lattice': kwargs.get('lattice', True),
                'stream': kwargs.get('stream', True),
                'guess': kwargs.get('guess', True),
                'silent': True
            }
            
            # 提取表格
            dfs = tabula.read_pdf(pdf_path, **tabula_options)
            
            # 处理结果
            for i, df in enumerate(dfs):
                if df.empty:
                    continue
                    
                # 清理表格
                df = self._clean_table(df)
                
                if not df.empty:
                    # 尝试确定页码
                    page_num = pages[0] if len(pages) == 1 else None
                    if page_num is None and len(dfs) == len(pages):
                        page_num = pages[i]
                    
                    tables.append({
                        'dataframe': df,
                        'page': page_num,
                        'table_index': i,
                        'method': 'tabula',
                        'bbox': None  # tabula不直接提供边界框
                    })
        except Exception as e:
            logger.warning(f"tabula处理PDF时出错: {e}")
        
        return tables
    
    def _extract_with_camelot(self, pdf_path: str, pages: List[int], **kwargs) -> List[Dict]:
        """使用camelot-py提取表格"""
        import camelot
        
        tables = []
        pages_str = ','.join(map(str, pages))
        
        try:
            # 设置camelot参数
            flavor = kwargs.get('flavor', 'lattice')
            camelot_options = {
                'pages': pages_str,
                'copy_text': kwargs.get('copy_text', []),
                'line_scale': kwargs.get('line_scale', 15),
                'process_background': kwargs.get('process_background', False),
                'strip_text': kwargs.get('strip_text', '\n'),
                'line_tol': kwargs.get('line_tol', 2)
            }
            
            # 提取表格
            camelot_tables = camelot.read_pdf(pdf_path, flavor=flavor, **camelot_options)
            
            # 处理结果
            for i, table in enumerate(camelot_tables):
                df = table.df
                if df.empty:
                    continue
                
                # 清理表格
                df = self._clean_table(df)
                
                if not df.empty:
                    # 获取边界框
                    bbox = table.cells[0][0]._bbox if hasattr(table, 'cells') and table.cells else None
                    
                    tables.append({
                        'dataframe': df,
                        'page': table.page,
                        'table_index': i,
                        'method': 'camelot',
                        'bbox': bbox,
                        'accuracy': table.accuracy,
                        'whitespace': table.whitespace
                    })
        except Exception as e:
            logger.warning(f"camelot处理PDF时出错: {e}")
        
        return tables
    
    def _extract_with_pymupdf(self, pdf_path: str, pages: List[int], **kwargs) -> List[Dict]:
        """使用PyMuPDF提取表格"""
        import fitz
        
        tables = []
        
        try:
            with fitz.open(pdf_path) as doc:
                for page_num in pages:
                    if page_num > len(doc):
                        continue
                        
                    try:
                        page = doc[page_num - 1]
                        
                        # 提取表格
                        page_tables = page.find_tables(
                            horizontal_strategy=kwargs.get('horizontal_strategy', 'text'),
                            vertical_strategy=kwargs.get('vertical_strategy', 'text'),
                            snap_tolerance=kwargs.get('snap_tolerance', 2),
                            snap_x_tolerance=kwargs.get('snap_x_tolerance', 2),
                            snap_y_tolerance=kwargs.get('snap_y_tolerance', 2),
                            join_tolerance=kwargs.get('join_tolerance', 2),
                            join_x_tolerance=kwargs.get('join_x_tolerance', 2),
                            join_y_tolerance=kwargs.get('join_y_tolerance', 2),
                            edge_min_length=kwargs.get('edge_min_length', 3),
                            deduplicate=kwargs.get('deduplicate', True)
                        )
                        
                        for i, table in enumerate(page_tables):
                            # 转换为DataFrame
                            df = pd.DataFrame(table.extract())
                            
                            # 使用第一行作为列名
                            if not df.empty and kwargs.get('use_first_row_as_header', True):
                                df.columns = df.iloc[0]
                                df = df.iloc[1:].reset_index(drop=True)
                            
                            # 清理表格
                            df = self._clean_table(df)
                            
                            if not df.empty:
                                tables.append({
                                    'dataframe': df,
                                    'page': page_num,
                                    'table_index': i,
                                    'method': 'pymupdf',
                                    'bbox': table.rect
                                })
                    except Exception as e:
                        logger.warning(f"PyMuPDF处理第{page_num}页时出错: {e}")
        except Exception as e:
            logger.warning(f"PyMuPDF处理PDF时出错: {e}")
        
        return tables
    
    def _clean_table(self, df: pd.DataFrame) -> pd.DataFrame:
        """清理表格数据"""
        if df.empty:
            return df
        
        # 基本清理
        df = DataUtils.clean_dataframe(df)
        
        if df.empty:
            return df
        
        # 处理CID编码问题
        df = self._clean_cid_encoding(df)
        
        # 处理合并单元格问题
        df = self._handle_merged_cells(df)
        
        return df
    
    def _clean_cid_encoding(self, df: pd.DataFrame) -> pd.DataFrame:
        """清理CID编码问题"""
        if df.empty:
            return df
        
        # 创建副本避免修改原数据
        df_clean = df.copy()
        
        # 清理CID编码
        for col in df_clean.columns:
            if df_clean[col].dtype == 'object':
                # 替换CID编码
                df_clean[col] = df_clean[col].astype(str).apply(
                    lambda x: re.sub(r'\(cid:\d+\)', '', x) if isinstance(x, str) else x
                )
        
        # 清理列名中的CID编码
        df_clean.columns = [re.sub(r'\(cid:\d+\)', '', str(col)) for col in df_clean.columns]
        
        return df_clean
    
    def _handle_merged_cells(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理合并单元格问题"""
        if df.empty:
            return df
        
        # 创建副本避免修改原数据
        df_clean = df.copy()
        
        # 填充空值（可能是合并单元格）
        for col in df_clean.columns:
            # 检测是否有连续的空值
            mask = df_clean[col].isna()
            if mask.any():
                # 向下填充值
                df_clean[col] = df_clean[col].fillna(method='ffill')
        
        return df_clean
    
    def analyze_pdf(self, pdf_path: Union[str, Path], 
                   pages: Optional[Union[List[int], str]] = None) -> Dict[str, Any]:
        """分析PDF文件中的表格
        
        Args:
            pdf_path: PDF文件路径
            pages: 页码列表或范围字符串，如 "1,3,5-7"，None表示所有页面
        
        Returns:
            分析结果字典
        """
        pdf_path = str(pdf_path)
        
        # 验证PDF文件
        is_valid, error_msg = FileUtils.validate_pdf_file(pdf_path)
        if not is_valid:
            logger.error(f"PDF文件无效: {error_msg}")
            return {'error': error_msg}
        
        # 解析页码
        page_list = self._parse_pages(pdf_path, pages)
        if not page_list:
            logger.warning("没有有效的页码")
            return {'error': '没有有效的页码'}
        
        # 分析结果
        results = {}
        
        # 获取PDF基本信息
        try:
            import PyPDF2
            with open(pdf_path, 'rb') as f:
                pdf = PyPDF2.PdfReader(f)
                results['total_pages'] = len(pdf.pages)
                results['metadata'] = pdf.metadata
        except Exception as e:
            logger.error(f"获取PDF信息失败: {e}")
            results['total_pages'] = 0
            results['metadata'] = {}
        
        # 分析每种方法
        results['methods'] = {}
        
        for method in self.available_methods:
            try:
                start_time = time.time()
                tables = self._extract_with_method(method, pdf_path, page_list)
                elapsed = time.time() - start_time
                
                # 评估表格质量
                score = self._evaluate_tables(tables, elapsed)
                
                # 收集表格信息
                tables_info = []
                for table in tables:
                    df = table['dataframe']
                    tables_info.append({
                        'page': table.get('page'),
                        'rows': len(df),
                        'columns': len(df.columns),
                        'quality': DataUtils.validate_table_quality(df)['score']
                    })
                
                results['methods'][method] = {
                    'table_count': len(tables),
                    'tables': tables_info,
                    'processing_time': elapsed,
                    'score': score
                }
            except Exception as e:
                logger.warning(f"{method} 分析失败: {e}")
                results['methods'][method] = {
                    'error': str(e),
                    'table_count': 0,
                    'tables': [],
                    'processing_time': 0,
                    'score': 0
                }
        
        # 推荐最佳方法
        if results['methods']:
            best_method = max(results['methods'], 
                             key=lambda m: results['methods'][m].get('score', 0))
            results['recommended_method'] = best_method
            results['recommendation_reason'] = self._get_recommendation_reason(
                best_method, results['methods'][best_method])
        else:
            results['recommended_method'] = None
            results['recommendation_reason'] = "没有可用的提取方法"
        
        return results
    
    def _get_recommendation_reason(self, method: str, method_info: Dict) -> str:
        """获取推荐理由"""
        if method_info.get('error'):
            return f"虽然 {method} 出现错误，但它是唯一可用的方法"
        
        table_count = method_info.get('table_count', 0)
        processing_time = method_info.get('processing_time', 0)
        score = method_info.get('score', 0)
        
        reasons = []
        
        if table_count > 0:
            reasons.append(f"提取了 {table_count} 个表格")
        
        if processing_time < 5:
            reasons.append("处理速度快")
        
        if score > 0.7:
            reasons.append("表格质量高")
        
        if method == 'pdfplumber':
            reasons.append("适合简单表格和文本表格")
        elif method == 'tabula':
            reasons.append("适合大多数标准表格")
        elif method == 'camelot':
            reasons.append("适合复杂表格和有线表格")
        elif method == 'pymupdf':
            reasons.append("适合现代PDF和图形表格")
        
        if reasons:
            return f"{method} 推荐原因: " + ", ".join(reasons)
        else:
            return f"{method} 是最佳选择，但没有具体原因"


class PDFToExcelConverter:
    """PDF转Excel转换器"""
    
    def __init__(self, method: str = 'auto'):
        """初始化PDF转Excel转换器
        
        Args:
            method: 提取方法，可选值：'auto', 'pdfplumber', 'tabula', 'camelot', 'pymupdf'
        """
        self.extractor = PDFTableExtractor(method)
    
    def convert(self, pdf_path: Union[str, Path], 
               output_path: Optional[Union[str, Path]] = None,
               pages: Optional[Union[List[int], str]] = None,
               clean_data: bool = True,
               include_metadata: bool = False,
               **kwargs) -> str:
        """将PDF转换为Excel
        
        Args:
            pdf_path: PDF文件路径
            output_path: 输出Excel文件路径，如果为None则自动生成
            pages: 页码列表或范围字符串，如 "1,3,5-7"，None表示所有页面
            clean_data: 是否清理数据
            include_metadata: 是否包含元数据
            **kwargs: 传递给提取方法的参数
        
        Returns:
            输出Excel文件路径
        """
        pdf_path = Path(pdf_path)
        
        # 验证PDF文件
        is_valid, error_msg = FileUtils.validate_pdf_file(pdf_path)
        if not is_valid:
            logger.error(f"PDF文件无效: {error_msg}")
            raise ValueError(error_msg)
        
        # 生成输出路径
        if output_path is None:
            output_path = pdf_path.with_suffix('.xlsx')
        else:
            output_path = Path(output_path)
            if output_path.is_dir():
                output_path = output_path / f"{pdf_path.stem}.xlsx"
        
        # 确保输出目录存在
        FileUtils.ensure_directory(output_path.parent)
        
        # 提取表格
        tables = self.extractor.extract_tables(pdf_path, pages, **kwargs)
        
        if not tables:
            logger.warning(f"未从 {pdf_path} 中提取到表格")
            # 创建一个空的Excel文件
            pd.DataFrame().to_excel(output_path, index=False)
            return str(output_path)
        
        # 合并相似表格（如果需要）
        if kwargs.get('merge_similar_tables', False):
            dfs = [table['dataframe'] for table in tables]
            merged_dfs = DataUtils.merge_similar_tables(dfs)
            
            # 更新表格列表
            if len(merged_dfs) < len(tables):
                new_tables = []
                for i, df in enumerate(merged_dfs):
                    new_table = {
                        'dataframe': df,
                        'page': tables[0].get('page') if i < len(tables) else None,
                        'table_index': i,
                        'method': tables[0].get('method') if i < len(tables) else 'merged',
                        'merged': True
                    }
                    new_tables.append(new_table)
                tables = new_tables
        
        # 写入Excel
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # 写入表格
            for i, table in enumerate(tables):
                df = table['dataframe']
                
                # 清理数据
                if clean_data:
                    df = DataUtils.clean_dataframe(df)
                
                # 优化内存使用
                df = PerformanceUtils.optimize_dataframe_memory(df)
                
                # 生成工作表名称
                sheet_name = ExcelUtils.generate_sheet_name('Table', i+1, table)
                
                # 写入工作表
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # 优化列宽
                ExcelUtils.optimize_column_widths(writer.sheets[sheet_name], df)
            
            # 添加元数据工作表
            if include_metadata:
                self._add_metadata_sheet(writer, pdf_path, tables)
        
        logger.info(f"已将 {pdf_path} 转换为 {output_path}，共 {len(tables)} 个表格")
        return str(output_path)
    
    def _add_metadata_sheet(self, writer, pdf_path: Path, tables: List[Dict]):
        """添加元数据工作表"""
        try:
            # 收集元数据
            metadata = {
                '文件名': pdf_path.name,
                '文件大小': f"{pdf_path.stat().st_size / 1024 / 1024:.2f} MB",
                '转换时间': time.strftime('%Y-%m-%d %H:%M:%S'),
                '表格数量': len(tables),
                '提取方法': ', '.join(set(table.get('method', 'unknown') for table in tables))
            }
            
            # 尝试获取PDF元数据
            try:
                import PyPDF2
                with open(pdf_path, 'rb') as f:
                    pdf = PyPDF2.PdfReader(f)
                    pdf_info = pdf.metadata
                    if pdf_info:
                        for key, value in pdf_info.items():
                            if key.startswith('/'):
                                key = key[1:]
                            metadata[f'PDF_{key}'] = str(value)
            except Exception as e:
                logger.debug(f"获取PDF元数据失败: {e}")
            
            # 创建元数据DataFrame
            meta_df = pd.DataFrame(list(metadata.items()), columns=['属性', '值'])
            
            # 写入元数据工作表
            meta_df.to_excel(writer, sheet_name='元数据', index=False)
            
            # 优化列宽
            ExcelUtils.optimize_column_widths(writer.sheets['元数据'], meta_df)
            
        except Exception as e:
            logger.warning(f"添加元数据工作表失败: {e}")
