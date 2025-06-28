# FileTo - PDF表格提取工具

![版本](https://img.shields.io/badge/版本-1.0.0-blue)
![Python](https://img.shields.io/badge/Python-3.7%2B-brightgreen)
![许可证](https://img.shields.io/badge/许可证-MIT-green)

FileTo是一个高性能、稳定的PDF表格提取和转换工具。它能够从PDF文件中提取表格数据，并将其转换为Excel格式，支持多种提取算法，并能智能选择最佳方法。

## 功能特点

- **多种提取方法**：支持pdfplumber、tabula-py、camelot-py、PyMuPDF等多种表格提取方法
- **智能选择**：自动分析PDF并选择最佳提取方法
- **多种界面**：支持命令行、Web界面和Python API
- **批量处理**：支持批量处理多个PDF文件
- **数据清理**：自动清理和优化提取的数据
- **表格合并**：智能合并相似的表格结构
- **内存优化**：优化大型表格的内存使用
- **标准输出**：生成格式规范的Excel文件

## 安装

### 依赖

- Python 3.7+
- 核心依赖：
  - pdfplumber
  - pandas
  - openpyxl
  - tabula-py (需要Java运行环境)
  - camelot-py
  - PyMuPDF

### 安装步骤

1. 克隆仓库：

```bash
git clone https://github.com/lixiangguang/FileTo.git
cd FileTo
```

2. 安装依赖：

```bash
pip install -r requirements.txt
```

3. 安装Java（如果使用tabula-py）：

```bash
# Ubuntu/Debian
sudo apt-get install default-jre

# macOS
brew install openjdk

# Windows
# 从 https://www.oracle.com/java/technologies/javase-jre8-downloads.html 下载并安装
```

## 基本使用

### 命令行界面

```bash
# 将PDF转换为Excel
python cli.py convert-pdf document.pdf -o output.xlsx

# 指定提取方法和页码
python cli.py convert-pdf document.pdf -m camelot -p "1,3,5-7"

# 分析PDF文件
python cli.py analyze document.pdf

# 显示工具信息
python cli.py info
```

### Web界面

```bash
# 启动Web应用
python web_app.py
```

然后在浏览器中访问 http://localhost:8501

### Python API

```python
from pdf_converter import PDFTableExtractor, PDFToExcelConverter

# 提取表格
extractor = PDFTableExtractor(method='auto')
tables = extractor.extract_tables('document.pdf', pages='1-5')

# 转换为Excel
converter = PDFToExcelConverter()
output_path = converter.convert('document.pdf', 'output.xlsx', include_metadata=True)
```

## 高级配置

### 配置文件

可以通过修改 `config.py` 文件来自定义配置：

```python
# 修改最大文件大小
Config.MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

# 修改提取方法优先级
Config.METHOD_PRIORITY = ['pymupdf', 'camelot', 'tabula', 'pdfplumber']

# 修改日志级别
Config.LOG_LEVEL = 'DEBUG'
```

### 环境变量

也可以通过环境变量来配置：

```bash
# 设置日志级别
export FILETO_LOG_LEVEL=DEBUG

# 设置最大文件大小（MB）
export FILETO_MAX_FILE_SIZE=100

# 设置临时目录
export FILETO_TEMP_DIR=/path/to/temp

# 设置默认提取方法
export FILETO_EXTRACTION_METHOD=camelot
```

## API文档

### PDFTableExtractor

```python
extractor = PDFTableExtractor(method='auto')
```

- `method`：表格提取方法，可选值：'auto', 'pdfplumber', 'tabula', 'camelot', 'pymupdf'

#### 方法

- `extract_tables(pdf_path, pages=None, **kwargs)`：提取表格
  - `pdf_path`：PDF文件路径
  - `pages`：页码列表或范围字符串，如 "1,3,5-7"，None表示所有页面
  - `**kwargs`：传递给具体提取方法的参数
  - 返回：表格列表，每个表格为字典，包含DataFrame和元数据

- `analyze_pdf(pdf_path, pages=None)`：分析PDF文件中的表格
  - `pdf_path`：PDF文件路径
  - `pages`：页码列表或范围字符串
  - 返回：分析结果字典

### PDFToExcelConverter

```python
converter = PDFToExcelConverter(method='auto')
```

- `method`：表格提取方法，可选值：'auto', 'pdfplumber', 'tabula', 'camelot', 'pymupdf'

#### 方法

- `convert(pdf_path, output_path=None, pages=None, clean_data=True, include_metadata=False, **kwargs)`：将PDF转换为Excel
  - `pdf_path`：PDF文件路径
  - `output_path`：输出Excel文件路径，如果为None则自动生成
  - `pages`：页码列表或范围字符串
  - `clean_data`：是否清理数据
  - `include_metadata`：是否包含元数据
  - `**kwargs`：传递给提取方法的参数
  - 返回：输出Excel文件路径

## 工具函数

### FileUtils

文件处理工具类，提供文件验证、哈希计算、临时文件管理等功能。

```python
from utils import FileUtils

# 验证PDF文件
is_valid, error_msg = FileUtils.validate_pdf_file('document.pdf')

# 获取文件哈希值
file_hash = FileUtils.get_file_hash('document.pdf')

# 创建临时文件
temp_path = FileUtils.create_temp_file(suffix='.pdf')
```

### DataUtils

数据处理工具类，提供DataFrame清洗、类型转换、表格合并与质量验证等功能。

```python
from utils import DataUtils

# 清理DataFrame
df_clean = DataUtils.clean_dataframe(df)

# 合并相似表格
merged_tables = DataUtils.merge_similar_tables(tables_list)

# 验证表格质量
quality_info = DataUtils.validate_table_quality(df)
```

### ExcelUtils

Excel处理工具类，提供工作表名称生成和列宽优化等功能。

```python
from utils import ExcelUtils

# 生成工作表名称
sheet_name = ExcelUtils.generate_sheet_name('Table', 1, {'page': 5})

# 优化列宽
ExcelUtils.optimize_column_widths(worksheet, df)
```

## 测试

运行测试：

```bash
python -m unittest discover tests
```

## 性能优化

### 大文件处理

对于大型PDF文件，可以使用分页处理：

```python
# 分批处理页面
for page_batch in range(1, total_pages, 5):
    pages = f"{page_batch}-{min(page_batch+4, total_pages)}"
    tables = extractor.extract_tables('large_document.pdf', pages=pages)
    # 处理表格...
```

### 内存优化

对于大型表格，可以使用内存优化工具：

```python
from utils import PerformanceUtils

# 分块处理大型DataFrame
chunks = PerformanceUtils.chunk_dataframe(large_df, chunk_size=10000)
for chunk in chunks:
    # 处理数据块...

# 优化DataFrame内存使用
df_optimized = PerformanceUtils.optimize_dataframe_memory(large_df)

# 估算内存使用量
memory_info = PerformanceUtils.estimate_memory_usage(df)
print(f"内存使用: {memory_info['total_mb']} MB")
```

## 故障排除

### 常见问题

1. **表格提取不完整或错误**
   - 尝试不同的提取方法：`-m camelot` 或 `-m pymupdf`
   - 对于复杂表格，camelot通常效果最好
   - 对于简单表格，pdfplumber可能更快

2. **Java相关错误**
   - 确保已安装Java并设置了JAVA_HOME环境变量
   - tabula-py依赖Java运行环境

3. **内存错误**
   - 使用页码范围限制处理范围：`-p "1-5"`
   - 增加系统虚拟内存
   - 使用PerformanceUtils中的内存优化工具

## 贡献

欢迎贡献代码、报告问题或提出改进建议！请遵循以下步骤：

1. Fork仓库
2. 创建功能分支：`git checkout -b feature/amazing-feature`
3. 提交更改：`git commit -m 'Add amazing feature'`
4. 推送到分支：`git push origin feature/amazing-feature`
5. 提交Pull Request

## 许可证

本项目采用MIT许可证 - 详情请参阅 [LICENSE](LICENSE) 文件

## 联系方式

- 项目维护者：[lixiangguang](https://github.com/lixiangguang)
- 项目链接：[https://github.com/lixiangguang/FileTo](https://github.com/lixiangguang/FileTo)

---

**FileTo** - 让PDF表格提取变得简单高效！