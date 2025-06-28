#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试PDF转Excel列保留功能
"""

import pandas as pd
from pdf_converter import PDFTableExtractor, PDFToExcelConverter
import tempfile
import os

def test_column_preservation():
    """测试列保留功能"""
    print("开始测试列保留功能...")
    
    # 检查是否有测试PDF文件
    test_pdf = "111.pdf"
    if not os.path.exists(test_pdf):
        print(f"❌ 测试文件 {test_pdf} 不存在")
        return
    
    try:
        # 创建提取器
        extractor = PDFTableExtractor(test_pdf)
        
        # 提取表格
        print("正在提取表格...")
        tables_dict = extractor.extract_all_methods()
        
        if not tables_dict:
            print("❌ 未提取到任何表格")
            return
        
        # 展平所有表格
        all_tables = []
        for method, method_tables in tables_dict.items():
            all_tables.extend(method_tables)
        
        print(f"✅ 成功提取到 {len(all_tables)} 个表格")
        
        # 检查每个表格的列数
        for i, table in enumerate(all_tables):
            method = table.attrs.get('method', 'unknown')
            print(f"表格 {i+1} ({method}): {table.shape[0]}行 x {table.shape[1]}列")
            
            # 显示列名
            print(f"  列名: {list(table.columns)}")
            
            # 显示前几行数据
            if not table.empty:
                print(f"  前3行数据:")
                for idx, row in table.head(3).iterrows():
                    print(f"    行{idx}: {row.tolist()}")
            print()
        
        # 选择最佳表格
        best_tables = extractor.get_best_tables()
        print(f"✅ 选择了 {len(best_tables)} 个最佳表格")
        
        # 分析问题：检查是否所有表格都只有1列
        single_column_count = sum(1 for table in all_tables if table.shape[1] == 1)
        print(f"\n⚠️  问题分析: {single_column_count}/{len(all_tables)} 个表格只有1列")
        
        if single_column_count == len(all_tables):
            print("❌ 所有表格都只有1列，这表明PDF表格提取存在问题")
            print("可能的原因:")
            print("  1. PDF中的表格格式复杂，提取算法无法正确识别列边界")
            print("  2. 表格数据被错误地合并到单列中")
            print("  3. PDF表格使用了特殊的布局或格式")
        
        # 转换为Excel
        converter = PDFToExcelConverter()
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            output_path = tmp_file.name
        
        print("正在转换为Excel...")
        result_path = converter.convert(test_pdf, output_path)
        
        if result_path and os.path.exists(result_path):
            print(f"✅ 转换成功: {result_path}")
            
            # 读取生成的Excel文件验证
            excel_data = pd.read_excel(result_path, sheet_name=None)
            
            print("\n生成的Excel文件内容:")
            for sheet_name, df in excel_data.items():
                print(f"  工作表 '{sheet_name}': {df.shape[0]}行 x {df.shape[1]}列")
                print(f"    列名: {list(df.columns)}")
                if not df.empty:
                    print(f"    前3行数据:")
                    for idx, row in df.head(3).iterrows():
                        print(f"      行{idx}: {row.tolist()}")
                print()
        else:
            print(f"❌ 转换失败或文件不存在")
        
        # 清理临时文件
        try:
            os.unlink(output_path)
        except:
            pass
            
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_column_preservation()