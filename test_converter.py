#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试模块
确保PDF转换功能的稳定性和准确性
"""

import unittest
import tempfile
import os
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 导入要测试的模块
from pdf_converter import PDFTableExtractor, PDFToExcelConverter
from utils import FileUtils, DataUtils, ExcelUtils, PerformanceUtils
from config import Config


class TestFileUtils(unittest.TestCase):
    """文件工具测试"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_pdf = Path(self.temp_dir) / 'test.pdf'
        self.test_txt = Path(self.temp_dir) / 'test.txt'
        
        # 创建测试文件
        self.test_pdf.write_bytes(b'%PDF-1.4 fake pdf content')
        self.test_txt.write_text('test content')
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_validate_pdf_file_success(self):
        """测试有效PDF文件验证"""
        is_valid, error = FileUtils.validate_pdf_file(self.test_pdf)
        self.assertTrue(is_valid)
        self.assertEqual(error, "")
    
    def test_validate_pdf_file_not_exists(self):
        """测试不存在文件验证"""
        non_existent = Path(self.temp_dir) / 'non_existent.pdf'
        is_valid, error = FileUtils.validate_pdf_file(non_existent)
        self.assertFalse(is_valid)
        self.assertEqual(error, Config.ERROR_MESSAGES['file_not_found'])
    
    def test_validate_pdf_file_wrong_format(self):
        """测试错误格式文件验证"""
        is_valid, error = FileUtils.validate_pdf_file(self.test_txt)
        self.assertFalse(is_valid)
        self.assertEqual(error, Config.ERROR_MESSAGES['invalid_format'])
    
    def test_get_file_hash(self):
        """测试文件哈希计算"""
        hash1 = FileUtils.get_file_hash(self.test_pdf)
        hash2 = FileUtils.get_file_hash(self.test_pdf)
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 32)  # MD5哈希长度
    
    def test_get_safe_filename(self):
        """测试安全文件名生成"""
        unsafe_name = 'test<>:"/\\|?*.pdf'
        safe_name = FileUtils.get_safe_filename(unsafe_name)
        self.assertNotIn('<', safe_name)
        self.assertNotIn('>', safe_name)
        self.assertNotIn(':', safe_name)
        self.assertTrue(safe_name.endswith('.pdf'))


class TestDataUtils(unittest.TestCase):
    """数据工具测试"""
    
    def setUp(self):
        # 创建测试数据
        self.test_df = pd.DataFrame({
            'Name': ['Alice', 'Bob', 'Charlie', None],
            'Age': ['25', '30', 'nan', '35'],
            'Salary': ['$50,000', '$60,000', '', '$70,000'],
            'Date': ['2023-01-01', '2023-02-01', '2023-03-01', '2023-04-01']
        })
        
        self.empty_df = pd.DataFrame()
        
        self.dirty_df = pd.DataFrame({
            'Col1': ['  value1  ', 'value2', 'nan', None],
            'Col2': [1, 2, None, 4],
            'Col3': ['', '   ', 'NULL', 'value']
        })
    
    def test_clean_dataframe_basic(self):
        """测试基本数据清理"""
        cleaned = DataUtils.clean_dataframe(self.dirty_df)
        
        # 检查字符串清理
        self.assertEqual(cleaned.iloc[0, 0], 'value1')  # 去除空格
        self.assertEqual(cleaned.iloc[2, 0], '')  # nan转换为空字符串
    
    def test_clean_dataframe_empty(self):
        """测试空DataFrame清理"""
        cleaned = DataUtils.clean_dataframe(self.empty_df)
        self.assertTrue(cleaned.empty)
    
    def test_auto_convert_types(self):
        """测试自动类型转换"""
        df = pd.DataFrame({
            'Numbers': ['1', '2', '3', '4'],
            'Prices': ['$100', '$200', '$300', '$400'],
            'Dates': ['2023-01-01', '2023-02-01', '2023-03-01', '2023-04-01'],
            'Text': ['a', 'b', 'c', 'd']
        })
        
        cleaned = DataUtils.clean_dataframe(df)
        
        # 数字列应该被转换为数值类型
        self.assertTrue(pd.api.types.is_numeric_dtype(cleaned['Numbers']))
        
        # 文本列应该保持为object类型
        self.assertEqual(cleaned['Text'].dtype, 'object')
    
    def test_validate_table_quality_good(self):
        """测试高质量表格验证"""
        good_df = pd.DataFrame({
            'A': [1, 2, 3, 4, 5],
            'B': ['a', 'b', 'c', 'd', 'e'],
            'C': [10.1, 20.2, 30.3, 40.4, 50.5]
        })
        
        quality = DataUtils.validate_table_quality(good_df)
        self.assertTrue(quality['is_valid'])
        self.assertGreater(quality['score'], 0.7)
    
    def test_validate_table_quality_poor(self):
        """测试低质量表格验证"""
        poor_df = pd.DataFrame({
            'A': [None, None, None],
            'B': [None, None, None]
        })
        
        quality = DataUtils.validate_table_quality(poor_df)
        self.assertFalse(quality['is_valid'])
        self.assertLess(quality['score'], 0.5)
    
    def test_merge_similar_tables(self):
        """测试相似表格合并"""
        table1 = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
        table2 = pd.DataFrame({'A': [5, 6], 'B': [7, 8]})
        table3 = pd.DataFrame({'X': [9, 10], 'Y': [11, 12]})
        
        tables = [table1, table2, table3]
        merged = DataUtils.merge_similar_tables(tables, similarity_threshold=0.8)
        
        # table1和table2应该被合并，table3保持独立
        self.assertEqual(len(merged), 2)
        self.assertEqual(len(merged[0]), 4)  # 合并后的表格有4行


class TestExcelUtils(unittest.TestCase):
    """Excel工具测试"""
    
    def test_generate_sheet_name_basic(self):
        """测试基本工作表名称生成"""
        name = ExcelUtils.generate_sheet_name('Table', 1)
        self.assertEqual(name, 'Table_1')
    
    def test_generate_sheet_name_with_attrs(self):
        """测试带属性的工作表名称生成"""
        attrs = {'page': 2, 'method': 'pdfplumber'}
        name = ExcelUtils.generate_sheet_name('Table', 1, attrs)
        self.assertIn('Page_2', name)
        self.assertIn('pdfplumb', name)  # 方法名被截断
    
    def test_generate_sheet_name_length_limit(self):
        """测试工作表名称长度限制"""
        long_name = 'Very_Long_Table_Name_That_Exceeds_Excel_Limits'
        name = ExcelUtils.generate_sheet_name(long_name, 1)
        self.assertLessEqual(len(name), Config.MAX_SHEET_NAME_LENGTH)


class TestPerformanceUtils(unittest.TestCase):
    """性能工具测试"""
    
    def test_chunk_dataframe_small(self):
        """测试小型DataFrame分块"""
        df = pd.DataFrame({'A': range(10)})
        chunks = PerformanceUtils.chunk_dataframe(df, chunk_size=1000)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(len(chunks[0]), 10)
    
    def test_chunk_dataframe_large(self):
        """测试大型DataFrame分块"""
        df = pd.DataFrame({'A': range(2500)})
        chunks = PerformanceUtils.chunk_dataframe(df, chunk_size=1000)
        self.assertEqual(len(chunks), 3)
        self.assertEqual(len(chunks[0]), 1000)
        self.assertEqual(len(chunks[1]), 1000)
        self.assertEqual(len(chunks[2]), 500)
    
    def test_estimate_memory_usage(self):
        """测试内存使用估算"""
        df = pd.DataFrame({
            'A': range(1000),
            'B': ['text'] * 1000,
            'C': [1.5] * 1000
        })
        
        usage = PerformanceUtils.estimate_memory_usage(df)
        self.assertIn('total_mb', usage)
        self.assertIn('per_column_mb', usage)
        self.assertIn('is_large', usage)
        self.assertIsInstance(usage['total_mb'], float)
    
    def test_optimize_dataframe_memory(self):
        """测试DataFrame内存优化"""
        df = pd.DataFrame({
            'Category': ['A', 'B', 'A', 'B'] * 250,  # 重复值，适合category
            'Value': range(1000),
            'Float': [1.0] * 1000
        })
        
        original_memory = df.memory_usage(deep=True).sum()
        optimized_df = PerformanceUtils.optimize_dataframe_memory(df)
        optimized_memory = optimized_df.memory_usage(deep=True).sum()
        
        # 优化后内存使用应该减少
        self.assertLess(optimized_memory, original_memory)


class TestPDFToExcelConverter(unittest.TestCase):
    """PDF转Excel转换器测试"""
    
    def setUp(self):
        self.converter = PDFToExcelConverter()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('pdf_converter.PDFTableExtractor')
    def test_convert_with_mock_extractor(self, mock_extractor_class):
        """测试使用模拟提取器的转换"""
        # 创建模拟数据
        mock_table = pd.DataFrame({
            'Name': ['Alice', 'Bob'],
            'Age': [25, 30]
        })
        
        # 配置模拟对象
        mock_extractor = Mock()
        mock_extractor.get_best_tables.return_value = [mock_table]
        mock_extractor_class.return_value = mock_extractor
        
        # 创建临时PDF文件
        pdf_path = Path(self.temp_dir) / 'test.pdf'
        pdf_path.write_bytes(b'%PDF-1.4 fake pdf')
        
        output_path = Path(self.temp_dir) / 'output.xlsx'
        
        # 执行转换
        result = self.converter.convert(str(pdf_path), str(output_path), method='auto')
        
        # 验证结果
        self.assertEqual(result, str(output_path))
        self.assertTrue(output_path.exists())
        
        # 验证Excel文件内容
        df_result = pd.read_excel(output_path)
        self.assertEqual(len(df_result), 2)
        self.assertIn('Name', df_result.columns)
        self.assertIn('Age', df_result.columns)


class TestConfig(unittest.TestCase):
    """配置测试"""
    
    def test_config_values(self):
        """测试配置值"""
        self.assertIsInstance(Config.MAX_FILE_SIZE, int)
        self.assertGreater(Config.MAX_FILE_SIZE, 0)
        self.assertIsInstance(Config.SUPPORTED_FORMATS, list)
        self.assertIn('.pdf', Config.SUPPORTED_FORMATS)
    
    def test_get_method_info(self):
        """测试获取方法信息"""
        info = Config.get_method_info('auto')
        self.assertIn('name', info)
        self.assertIn('description', info)
        
        # 测试不存在的方法
        info = Config.get_method_info('nonexistent')
        self.assertEqual(info, {})
    
    def test_validate_file(self):
        """测试文件验证"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(b'test content')
            tmp_path = Path(tmp.name)
        
        try:
            result = Config.validate_file(tmp_path)
            self.assertTrue(result)
        finally:
            tmp_path.unlink()


def create_test_suite():
    """创建测试套件"""
    suite = unittest.TestSuite()
    
    # 添加所有测试类
    test_classes = [
        TestFileUtils,
        TestDataUtils,
        TestExcelUtils,
        TestPerformanceUtils,
        TestPDFToExcelConverter,
        TestConfig
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    return suite


def run_tests():
    """运行所有测试"""
    print("🧪 开始运行测试...")
    print("=" * 50)
    
    suite = create_test_suite()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 50)
    if result.wasSuccessful():
        print("✅ 所有测试通过!")
    else:
        print(f"❌ 测试失败: {len(result.failures)} 个失败, {len(result.errors)} 个错误")
        
        if result.failures:
            print("\n失败的测试:")
            for test, traceback in result.failures:
                print(f"- {test}: {traceback.split('AssertionError:')[-1].strip()}")
        
        if result.errors:
            print("\n错误的测试:")
            for test, traceback in result.errors:
                print(f"- {test}: {traceback.split('Exception:')[-1].strip()}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    exit(0 if success else 1)