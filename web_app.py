#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web应用模块
提供基于Streamlit的Web界面
"""

import os
import sys
import time
import tempfile
from pathlib import Path
from typing import List, Dict, Optional, Any, Union

import pandas as pd
import streamlit as st
from loguru import logger

from config import Config
from pdf_converter import PDFTableExtractor, PDFToExcelConverter
from utils import FileUtils


# 配置日志
logger.remove()
logger.add(sys.stderr, level=Config.LOG_LEVEL, format=Config.LOG_FORMAT)


# 页面配置
st.set_page_config(
    page_title=Config.WEB_APP_TITLE,
    page_icon=Config.WEB_APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)


# 自定义CSS
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #e6f0ff;
        border-bottom: 2px solid #4c8bf5;
    }
    .stProgress > div > div > div > div {
        background-color: #4c8bf5;
    }
    .stDownloadButton button {
        background-color: #4c8bf5;
        color: white;
    }
    .stDataFrame {
        max-height: 400px;
        overflow-y: auto;
    }
</style>
""", unsafe_allow_html=True)


# 初始化会话状态
def init_session_state():
    """初始化会话状态"""
    if 'history' not in st.session_state:
        st.session_state.history = []
    if 'current_tables' not in st.session_state:
        st.session_state.current_tables = []
    if 'excel_path' not in st.session_state:
        st.session_state.excel_path = None


# 显示页面头部
def show_header():
    """显示页面头部"""
    st.title(f"{Config.WEB_APP_ICON} FileTo - PDF表格提取工具")
    st.markdown("""
    <div style="margin-bottom: 20px;">
        <p>从PDF文件中提取表格并转换为Excel格式。支持多种提取方法，并能智能选择最佳方法。</p>
        <ul style="list-style-type: none; padding-left: 0;">
            <li>✅ 支持多种表格提取方法</li>
            <li>✅ 处理复杂表格结构</li>
            <li>✅ 自动清理和优化数据</li>
            <li>✅ 提供表格预览</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)


# 侧边栏设置
def show_sidebar():
    """显示侧边栏设置"""
    st.sidebar.header("设置")
    
    # 提取方法
    method = st.sidebar.selectbox(
        "表格提取方法",
        options=["auto", "pdfplumber", "tabula", "camelot", "pymupdf"],
        index=0,
        help="选择表格提取方法，或使用自动模式选择最佳方法"
    )
    
    # 显示预览
    show_preview = st.sidebar.checkbox(
        "显示表格预览", 
        value=True,
        help="显示提取的表格预览"
    )
    
    # 预览行数
    preview_rows = st.sidebar.slider(
        "预览行数", 
        min_value=5, 
        max_value=50, 
        value=Config.PREVIEW_ROWS,
        help="设置表格预览显示的行数"
    )
    
    # 包含元数据
    include_metadata = st.sidebar.checkbox(
        "包含元数据", 
        value=True,
        help="在Excel文件中包含PDF元数据"
    )
    
    # 合并相似表格
    merge_similar = st.sidebar.checkbox(
        "合并相似表格", 
        value=False,
        help="尝试合并结构相似的表格"
    )
    
    # 关于信息
    st.sidebar.markdown("---")
    st.sidebar.info(
        "**关于FileTo**\n\n"
        "FileTo是一个高性能、稳定的PDF表格提取和转换工具。\n\n"
        "版本: 1.0.0\n\n"
        "[GitHub仓库](https://github.com/lixiangguang/FileTo)"
    )
    
    return {
        "method": method,
        "show_preview": show_preview,
        "preview_rows": preview_rows,
        "include_metadata": include_metadata,
        "merge_similar": merge_similar
    }


# 处理上传的PDF文件
def process_uploaded_file(uploaded_file, settings):
    """处理上传的PDF文件"""
    if uploaded_file is None:
        return
    
    # 创建临时文件
    temp_dir = Config.get_temp_dir()
    temp_pdf_path = os.path.join(temp_dir, uploaded_file.name)
    
    # 保存上传的文件
    with open(temp_pdf_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # 显示进度条
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # 创建提取器
        status_text.text("正在初始化提取器...")
        extractor = PDFTableExtractor(method=settings["method"])
        progress_bar.progress(10)
        
        # 提取表格
        status_text.text("正在提取表格...")
        start_time = time.time()
        tables = extractor.extract_tables(temp_pdf_path)
        elapsed = time.time() - start_time
        progress_bar.progress(70)
        
        if not tables:
            st.warning("未从PDF中提取到表格。请尝试其他提取方法或检查PDF文件。")
            progress_bar.progress(100)
            status_text.text("处理完成，未找到表格")
            return
        
        # 清理表格数据
        status_text.text("正在清理和优化数据...")
        for table in tables:
            table["dataframe"] = table["dataframe"].copy()
        progress_bar.progress(80)
        
        # 创建Excel文件
        status_text.text("正在创建Excel文件...")
        temp_excel_path = os.path.join(temp_dir, f"{Path(uploaded_file.name).stem}.xlsx")
        
        converter = PDFToExcelConverter(method=settings["method"])
        excel_path = converter.convert(
            pdf_path=temp_pdf_path,
            output_path=temp_excel_path,
            clean_data=True,
            include_metadata=settings["include_metadata"],
            merge_similar_tables=settings["merge_similar"]
        )
        progress_bar.progress(100)
        
        # 更新会话状态
        st.session_state.current_tables = tables
        st.session_state.excel_path = excel_path
        
        # 添加到历史记录
        st.session_state.history.append({
            "filename": uploaded_file.name,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "table_count": len(tables),
            "method": settings["method"],
            "excel_path": excel_path,
            "processing_time": elapsed
        })
        
        status_text.text(f"处理完成！提取了 {len(tables)} 个表格，用时 {elapsed:.2f} 秒")
        
    except Exception as e:
        st.error(f"处理文件时出错: {str(e)}")
        logger.error(f"处理文件时出错: {str(e)}")
        progress_bar.progress(100)
        status_text.text("处理失败")
    
    # 清理临时PDF文件
    if Config.CLEANUP_TEMP_FILES and os.path.exists(temp_pdf_path):
        os.unlink(temp_pdf_path)


# 显示表格预览
def show_table_preview(tables, preview_rows):
    """显示表格预览"""
    if not tables:
        st.info("没有可预览的表格")
        return
    
    # 显示统计信息
    st.subheader("表格统计")
    col1, col2, col3 = st.columns(3)
    col1.metric("表格数量", len(tables))
    
    total_rows = sum(len(table["dataframe"]) for table in tables)
    col2.metric("总行数", total_rows)
    
    total_cols = sum(len(table["dataframe"].columns) for table in tables)
    col3.metric("总列数", total_cols)
    
    # 显示每个表格的预览
    st.subheader("表格预览")
    
    for i, table in enumerate(tables):
        df = table["dataframe"]
        method = table.get("method", "未知")
        page = table.get("page", "未知")
        
        with st.expander(f"表格 {i+1} (页码: {page}, 方法: {method}, 行数: {len(df)}, 列数: {len(df.columns)})"):
            # 显示表格预览
            st.dataframe(df.head(preview_rows))
            
            # 显示表格质量信息
            quality_info = pd.DataFrame({
                "指标": ["行数", "列数", "空值比例", "数据类型"],
                "值": [
                    len(df),
                    len(df.columns),
                    f"{df.isna().sum().sum() / (len(df) * len(df.columns)):.1%}",
                    ", ".join(df.dtypes.astype(str).value_counts().index.tolist()[:3])
                ]
            })
            st.dataframe(quality_info, hide_index=True)


# 创建Excel下载链接
def create_download_link(excel_path):
    """创建Excel下载链接"""
    if not excel_path or not os.path.exists(excel_path):
        st.warning("Excel文件不可用")
        return
    
    # 读取Excel文件
    with open(excel_path, "rb") as f:
        excel_data = f.read()
    
    # 创建下载按钮
    filename = os.path.basename(excel_path)
    st.download_button(
        label=f"下载Excel文件 ({filename})",
        data=excel_data,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    # 显示文件信息
    file_size = os.path.getsize(excel_path) / 1024  # KB
    st.info(f"文件大小: {file_size:.1f} KB")


# 显示历史记录
def show_history():
    """显示历史记录"""
    if not st.session_state.history:
        st.info("没有处理历史")
        return
    
    # 创建历史记录表格
    history_data = []
    for item in st.session_state.history:
        history_data.append({
            "文件名": item["filename"],
            "处理时间": item["timestamp"],
            "表格数量": item["table_count"],
            "提取方法": item["method"],
            "处理用时(秒)": f"{item['processing_time']:.2f}"
        })
    
    history_df = pd.DataFrame(history_data)
    st.dataframe(history_df, hide_index=True)
    
    # 清除历史按钮
    if st.button("清除历史记录"):
        st.session_state.history = []
        st.experimental_rerun()


# 主函数
def main():
    """主函数"""
    # 初始化会话状态
    init_session_state()
    
    # 显示页面头部
    show_header()
    
    # 侧边栏设置
    settings = show_sidebar()
    
    # 创建选项卡
    tab1, tab2, tab3 = st.tabs(["📤 文件上传", "📚 批量处理", "📋 历史记录"])
    
    # 文件上传选项卡
    with tab1:
        st.subheader("上传PDF文件")
        uploaded_file = st.file_uploader(
            "选择PDF文件", 
            type=["pdf"],
            help="上传PDF文件以提取表格"
        )
        
        if uploaded_file is not None:
            # 处理上传的文件
            process_uploaded_file(uploaded_file, settings)
            
            # 显示表格预览
            if settings["show_preview"] and st.session_state.current_tables:
                show_table_preview(st.session_state.current_tables, settings["preview_rows"])
            
            # 创建下载链接
            if st.session_state.excel_path:
                st.subheader("下载Excel文件")
                create_download_link(st.session_state.excel_path)
    
    # 批量处理选项卡
    with tab2:
        st.subheader("批量处理PDF文件")
        st.info("批量处理功能即将推出，敬请期待！")
    
    # 历史记录选项卡
    with tab3:
        st.subheader("处理历史")
        show_history()


if __name__ == "__main__":
    main()