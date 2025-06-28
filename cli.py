#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命令行接口模块
提供PDF表格提取和转换的命令行工具
"""

import os
import sys
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

import click
from loguru import logger

from config import Config
from pdf_converter import PDFTableExtractor, PDFToExcelConverter


# 配置日志
logger.remove()
logger.add(sys.stderr, level=Config.LOG_LEVEL, format=Config.LOG_FORMAT)


@click.group()
@click.version_option(version='1.0.0')
def cli():
    """FileTo - PDF表格提取和转换工具
    
    从PDF文件中提取表格并转换为Excel格式。
    支持多种提取方法，并能智能选择最佳方法。
    """
    pass


@cli.command('convert-pdf')
@click.argument('pdf_path', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='输出Excel文件路径')
@click.option('--pages', '-p', help='页码范围，例如："1,3,5-7"')
@click.option('--method', '-m', 
              type=click.Choice(['auto', 'pdfplumber', 'tabula', 'camelot', 'pymupdf']),
              default='auto', help='表格提取方法')
@click.option('--verbose', '-v', is_flag=True, help='显示详细输出')
@click.option('--include-metadata', is_flag=True, help='包含PDF元数据')
@click.option('--merge-similar', is_flag=True, help='合并相似表格')
def convert_pdf(pdf_path: str, output: Optional[str], pages: Optional[str],
               method: str, verbose: bool, include_metadata: bool, merge_similar: bool):
    """将PDF文件转换为Excel"""
    start_time = time.time()
    
    # 设置日志级别
    if verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG", format=Config.LOG_FORMAT)
    
    try:
        # 创建转换器
        converter = PDFToExcelConverter(method=method)
        
        # 转换PDF
        click.echo(f"正在从 {pdf_path} 提取表格...")
        output_path = converter.convert(
            pdf_path=pdf_path,
            output_path=output,
            pages=pages,
            include_metadata=include_metadata,
            merge_similar_tables=merge_similar
        )
        
        elapsed = time.time() - start_time
        click.echo(f"转换完成！输出文件: {output_path} (用时: {elapsed:.2f}秒)")
        
    except Exception as e:
        click.echo(f"错误: {str(e)}", err=True)
        sys.exit(1)


@cli.command('analyze')
@click.argument('pdf_path', type=click.Path(exists=True))
@click.option('--pages', '-p', help='页码范围，例如："1,3,5-7"')
@click.option('--verbose', '-v', is_flag=True, help='显示详细输出')
def analyze_pdf(pdf_path: str, pages: Optional[str], verbose: bool):
    """分析PDF文件中的表格"""
    # 设置日志级别
    if verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG", format=Config.LOG_FORMAT)
    
    try:
        # 创建提取器
        extractor = PDFTableExtractor()
        
        # 分析PDF
        click.echo(f"正在分析 {pdf_path}...")
        results = extractor.analyze_pdf(pdf_path, pages)
        
        if 'error' in results:
            click.echo(f"分析错误: {results['error']}", err=True)
            sys.exit(1)
        
        # 显示结果
        click.echo(f"\nPDF文件: {pdf_path}")
        click.echo(f"总页数: {results['total_pages']}")
        
        click.echo("\n提取方法分析:")
        for method, info in results['methods'].items():
            if 'error' in info:
                click.echo(f"  {method}: 错误 - {info['error']}")
                continue
                
            click.echo(f"  {method}:")
            click.echo(f"    表格数量: {info['table_count']}")
            click.echo(f"    处理时间: {info['processing_time']:.2f}秒")
            click.echo(f"    质量评分: {info['score']:.2f}")
            
            if verbose and info['tables']:
                click.echo("    表格详情:")
                for i, table in enumerate(info['tables']):
                    click.echo(f"      表格 {i+1}: 页码={table['page']}, "
                             f"行数={table['rows']}, 列数={table['columns']}, "
                             f"质量={table['quality']:.2f}")
        
        click.echo(f"\n推荐方法: {results['recommended_method']}")
        click.echo(f"推荐理由: {results['recommendation_reason']}")
        
    except Exception as e:
        click.echo(f"错误: {str(e)}", err=True)
        sys.exit(1)


@cli.command('info')
@click.option('--verbose', '-v', is_flag=True, help='显示详细信息')
def show_info(verbose: bool):
    """显示工具信息"""
    click.echo("FileTo - PDF表格提取和转换工具")
    click.echo("版本: 1.0.0\n")
    
    click.echo("功能特点:")
    click.echo("  - 支持多种表格提取方法，并能智能选择最佳方法")
    click.echo("  - 处理复杂表格结构，包括合并单元格和嵌套表格")
    click.echo("  - 自动清理和优化提取的数据")
    click.echo("  - 支持批量处理多个PDF文件")
    click.echo("  - 提供命令行、Web界面和Python API")
    
    click.echo("\n支持的提取方法:")
    click.echo("  - pdfplumber: 适用于简单表格和文本表格")
    click.echo("  - tabula-py: 适用于大多数标准表格")
    click.echo("  - camelot-py: 适用于复杂表格和有线表格")
    click.echo("  - PyMuPDF: 适用于现代PDF和图形表格")
    
    click.echo("\n使用示例:")
    click.echo("  fileto convert-pdf document.pdf -o output.xlsx")
    click.echo("  fileto convert-pdf document.pdf -m camelot -p \"1,3,5-7\"")
    click.echo("  fileto analyze document.pdf")
    
    if verbose:
        click.echo("\n依赖库:")
        try:
            import pkg_resources
            for pkg in ['pdfplumber', 'pandas', 'tabula-py', 'camelot-py', 'PyMuPDF', 'openpyxl']:
                try:
                    version = pkg_resources.get_distribution(pkg).version
                    click.echo(f"  - {pkg}: {version}")
                except pkg_resources.DistributionNotFound:
                    click.echo(f"  - {pkg}: 未安装")
        except ImportError:
            click.echo("  无法获取依赖库信息")


if __name__ == '__main__':
    cli()