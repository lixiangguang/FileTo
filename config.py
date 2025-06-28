#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置模块
定义应用程序的配置参数和环境变量处理
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Union


class Config:
    """应用程序配置"""
    
    # 文件处理配置
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    SUPPORTED_FORMATS = ['.pdf']
    CHUNK_SIZE = 4096  # 文件读取块大小
    
    # 表格提取配置
    DEFAULT_EXTRACTION_METHOD = 'auto'
    METHOD_PRIORITY = ['camelot', 'tabula', 'pymupdf', 'pdfplumber']
    
    # 输出配置
    DEFAULT_OUTPUT_FORMAT = 'xlsx'
    MAX_SHEET_NAME_LENGTH = 31  # Excel工作表名称最大长度
    
    # 性能配置
    MAX_TABLES_PER_FILE = 100  # 每个文件最大表格数
    MAX_ROWS_PER_TABLE = 1000000  # 每个表格最大行数
    CHUNK_SIZE_ROWS = 10000  # 分块处理行数
    
    # 日志配置
    LOG_LEVEL = 'INFO'
    LOG_FORMAT = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    
    # Web应用配置
    WEB_APP_TITLE = "FileTo - PDF表格提取工具"
    WEB_APP_ICON = "📊"
    PREVIEW_ROWS = 10  # 预览行数
    
    # 临时文件配置
    TEMP_DIR = None  # 临时目录，None表示使用系统默认
    CLEANUP_TEMP_FILES = True  # 是否清理临时文件
    
    # 错误消息
    ERROR_MESSAGES = {
        'file_not_found': "文件不存在",
        'file_too_large': f"文件大小超过限制 ({MAX_FILE_SIZE/1024/1024:.1f}MB)",
        'invalid_format': f"不支持的文件格式，仅支持: {', '.join(SUPPORTED_FORMATS)}",
        'extraction_failed': "表格提取失败",
        'no_tables_found': "未找到表格",
        'invalid_page_range': "无效的页码范围"
    }
    
    @staticmethod
    def get_temp_dir() -> str:
        """获取临时目录"""
        if Config.TEMP_DIR:
            temp_dir = Path(Config.TEMP_DIR)
            temp_dir.mkdir(parents=True, exist_ok=True)
            return str(temp_dir)
        else:
            return tempfile.gettempdir()


class EnvConfig:
    """环境变量配置"""
    
    @staticmethod
    def load_from_env():
        """从环境变量加载配置"""
        # 日志级别
        log_level = os.environ.get('FILETO_LOG_LEVEL')
        if log_level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            Config.LOG_LEVEL = log_level
        
        # 最大文件大小
        max_file_size = os.environ.get('FILETO_MAX_FILE_SIZE')
        if max_file_size and max_file_size.isdigit():
            Config.MAX_FILE_SIZE = int(max_file_size) * 1024 * 1024  # MB转字节
        
        # 临时目录
        temp_dir = os.environ.get('FILETO_TEMP_DIR')
        if temp_dir and os.path.isdir(temp_dir):
            Config.TEMP_DIR = temp_dir
        
        # 清理临时文件
        cleanup_temp = os.environ.get('FILETO_CLEANUP_TEMP')
        if cleanup_temp is not None:
            Config.CLEANUP_TEMP_FILES = cleanup_temp.lower() in ['true', '1', 'yes']
        
        # 默认提取方法
        extraction_method = os.environ.get('FILETO_EXTRACTION_METHOD')
        if extraction_method in ['auto', 'pdfplumber', 'tabula', 'camelot', 'pymupdf']:
            Config.DEFAULT_EXTRACTION_METHOD = extraction_method


# 加载环境变量配置
EnvConfig.load_from_env()