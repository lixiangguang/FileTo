#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用示例
演示PDF转电子表格工具的各种用法
"""

import os
import sys
from pathlib import Path
from pdf_converter import PDFToExcelConverter, PDFTableExtractor
from utils import DataUtils, FileUtils
from config import Config


def example_basic_conversion():
    """示例1: 基本转换"""
    print("📄 示例1: 基本PDF转Excel转换")
    print("=" * 40)
    
    # 注意：这里需要一个实际的PDF文件
    pdf_file = "sample.pdf"  # 请替换为实际的PDF文件路径
    
    if not os.path.exists(pdf_file):
        print(f"⚠️  请先准备一个PDF文件: {pdf_file}")
        print("   您可以下载任何包含表格的PDF文件进行测试")
        return
    
    try:
        # 创建转换器
        converter = PDFToExcelConverter()
        
        # 执行转换
        print(f"🚀 开始转换: {pdf_file}")
        result_path = converter.convert(
            pdf_path=pdf_file,
            output_path="output_basic.xlsx",
            method="auto"
        )
        
        print(f"✅ 转换完成: {result_path}")
        
        # 显示文件信息
        if os.path.exists(result_path):
            file_size = os.path.getsize(result_path)
            print(f"📊 输出文件大小: {file_size / 1024:.2f} KB")
        
    except Exception as e:
        print(f"❌ 转换失败: {e}")


def example_method_comparison():
    """示例2: 比较不同提取方法"""
    print("\n🔍 示例2: 比较不同提取方法")
    print("=" * 40)
    
    pdf_file = "sample.pdf"
    
    if not os.path.exists(pdf_file):
        print(f"⚠️  请先准备一个PDF文件: {pdf_file}")
        return
    
    try:
        # 创建提取器
        extractor = PDFTableExtractor(pdf_file)
        
        # 获取所有方法的结果
        print("🔄 使用所有方法提取表格...")
        all_results = extractor.extract_all_methods()
        
        # 比较结果
        print("\n📊 提取结果比较:")
        for method, tables in all_results.items():
            table_count = len(tables)
            if table_count > 0:
                total_rows = sum(len(df) for df in tables)
                total_cols = sum(len(df.columns) for df in tables)
                print(f"  {method:12}: {table_count:2d} 个表格, {total_rows:4d} 行, {total_cols:3d} 列")
            else:
                print(f"  {method:12}: 未找到表格")
        
        # 保存最佳结果
        best_tables = extractor.get_best_tables()
        if best_tables:
            converter = PDFToExcelConverter()
            converter._save_to_excel(best_tables, "output_best.xlsx")
            print(f"\n💾 最佳结果已保存到: output_best.xlsx")
        
    except Exception as e:
        print(f"❌ 比较失败: {e}")


def example_data_quality_analysis():
    """示例3: 数据质量分析"""
    print("\n🧪 示例3: 数据质量分析")
    print("=" * 40)
    
    pdf_file = "sample.pdf"
    
    if not os.path.exists(pdf_file):
        print(f"⚠️  请先准备一个PDF文件: {pdf_file}")
        return
    
    try:
        extractor = PDFTableExtractor(pdf_file)
        tables = extractor.get_best_tables()
        
        if not tables:
            print("❌ 未找到任何表格")
            return
        
        print(f"📋 分析 {len(tables)} 个表格的数据质量...")
        
        for i, table in enumerate(tables, 1):
            print(f"\n表格 {i}:")
            print(f"  尺寸: {table.shape[0]} 行 x {table.shape[1]} 列")
            
            # 数据质量分析
            quality = DataUtils.validate_table_quality(table)
            print(f"  质量评分: {quality['score']:.2f}")
            print(f"  是否有效: {'✅' if quality['is_valid'] else '❌'}")
            
            if quality['issues']:
                print(f"  问题: {', '.join(quality['issues'])}")
            
            # 显示前几行数据
            print("  预览:")
            preview = table.head(3)
            for col in preview.columns:
                print(f"    {col}: {list(preview[col])}")
            
            # 清理数据
            cleaned_table = DataUtils.clean_dataframe(table)
            if not cleaned_table.equals(table):
                print(f"  清理后尺寸: {cleaned_table.shape[0]} 行 x {cleaned_table.shape[1]} 列")
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")


def example_batch_processing():
    """示例4: 批量处理"""
    print("\n📦 示例4: 批量处理PDF文件")
    print("=" * 40)
    
    # 创建示例目录结构
    input_dir = Path("pdf_input")
    output_dir = Path("excel_output")
    
    print(f"📁 输入目录: {input_dir}")
    print(f"📁 输出目录: {output_dir}")
    
    if not input_dir.exists():
        print(f"⚠️  请创建输入目录并放入PDF文件: {input_dir}")
        print("   mkdir pdf_input")
        print("   # 然后将PDF文件复制到 pdf_input 目录")
        return
    
    # 查找PDF文件
    pdf_files = list(input_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"⚠️  在 {input_dir} 目录中未找到PDF文件")
        return
    
    print(f"🔍 找到 {len(pdf_files)} 个PDF文件")
    
    # 创建输出目录
    output_dir.mkdir(exist_ok=True)
    
    # 批量转换
    converter = PDFToExcelConverter()
    success_count = 0
    
    for pdf_file in pdf_files:
        try:
            print(f"\n🚀 处理: {pdf_file.name}")
            
            # 验证文件
            is_valid, error = FileUtils.validate_pdf_file(pdf_file)
            if not is_valid:
                print(f"  ❌ 文件验证失败: {error}")
                continue
            
            # 转换
            output_file = output_dir / f"{pdf_file.stem}.xlsx"
            result_path = converter.convert(
                str(pdf_file),
                str(output_file),
                method="auto"
            )
            
            print(f"  ✅ 转换成功: {output_file.name}")
            success_count += 1
            
        except Exception as e:
            print(f"  ❌ 转换失败: {e}")
    
    print(f"\n📊 批量处理完成: {success_count}/{len(pdf_files)} 个文件成功转换")


def example_custom_processing():
    """示例5: 自定义处理流程"""
    print("\n⚙️ 示例5: 自定义处理流程")
    print("=" * 40)
    
    pdf_file = "sample.pdf"
    
    if not os.path.exists(pdf_file):
        print(f"⚠️  请先准备一个PDF文件: {pdf_file}")
        return
    
    try:
        extractor = PDFTableExtractor(pdf_file)
        
        # 步骤1: 尝试所有方法
        print("🔄 步骤1: 尝试所有提取方法")
        all_results = extractor.extract_all_methods()
        
        # 步骤2: 筛选高质量表格
        print("🔍 步骤2: 筛选高质量表格")
        high_quality_tables = []
        
        for method, tables in all_results.items():
            for table in tables:
                quality = DataUtils.validate_table_quality(table)
                if quality['score'] > 0.7:  # 只保留高质量表格
                    table.attrs['quality_score'] = quality['score']
                    high_quality_tables.append(table)
                    print(f"  ✅ 保留表格 (方法: {method}, 评分: {quality['score']:.2f})")
        
        # 步骤3: 合并相似表格
        print("🔗 步骤3: 合并相似表格")
        merged_tables = DataUtils.merge_similar_tables(high_quality_tables)
        print(f"  合并前: {len(high_quality_tables)} 个表格")
        print(f"  合并后: {len(merged_tables)} 个表格")
        
        # 步骤4: 数据清理和优化
        print("🧹 步骤4: 数据清理和优化")
        final_tables = []
        
        for i, table in enumerate(merged_tables):
            # 清理数据
            cleaned = DataUtils.clean_dataframe(table)
            
            # 内存优化
            from utils import PerformanceUtils
            optimized = PerformanceUtils.optimize_dataframe_memory(cleaned)
            
            final_tables.append(optimized)
            print(f"  表格 {i+1}: {optimized.shape[0]} 行 x {optimized.shape[1]} 列")
        
        # 步骤5: 保存结果
        print("💾 步骤5: 保存最终结果")
        if final_tables:
            converter = PDFToExcelConverter()
            converter._save_to_excel(final_tables, "output_custom.xlsx")
            print(f"  ✅ 保存完成: output_custom.xlsx")
        else:
            print("  ⚠️  没有符合条件的表格")
        
    except Exception as e:
        print(f"❌ 自定义处理失败: {e}")


def main():
    """主函数"""
    print("🎯 PDF转电子表格工具 - 使用示例")
    print("=" * 50)
    
    # 显示配置信息
    print(f"📋 当前配置:")
    print(f"  最大文件大小: {Config.MAX_FILE_SIZE / 1024 / 1024:.0f} MB")
    print(f"  支持格式: {', '.join(Config.SUPPORTED_FORMATS)}")
    print(f"  默认方法: {Config.DEFAULT_METHOD}")
    
    # 运行示例
    examples = [
        example_basic_conversion,
        example_method_comparison,
        example_data_quality_analysis,
        example_batch_processing,
        example_custom_processing
    ]
    
    for example_func in examples:
        try:
            example_func()
        except KeyboardInterrupt:
            print("\n⏹️  用户中断")
            break
        except Exception as e:
            print(f"\n❌ 示例执行失败: {e}")
    
    print("\n🎉 示例演示完成!")
    print("\n💡 提示:")
    print("  - 请准备一些包含表格的PDF文件进行测试")
    print("  - 可以使用 'python cli.py info' 查看更多信息")
    print("  - 可以使用 'streamlit run web_app.py' 启动Web界面")


if __name__ == "__main__":
    main()