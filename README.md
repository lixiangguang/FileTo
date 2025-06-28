# FileTo - PDF文件转换工具

一个功能强大的PDF文件内容提取工具，支持文本和表格数据的提取，特别针对中文CID编码问题进行了优化。

## 功能特点

- 📄 支持多种PDF提取方法（PyMuPDF、pdfplumber）
- 🔧 自动修复CID编码导致的中文乱码问题
- 📊 智能表格识别和数据提取
- 🌐 提供Web界面和命令行界面
- 🛠️ 支持多种输出格式（CSV、Excel、JSON）

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### Web界面

```bash
streamlit run web_app.py --server.port 8504
```

### 命令行

```bash
python cli.py input.pdf --output output.csv
```

## 技术亮点

- **CID编码修复**：自动识别和清理PDF中的CID编码字符
- **智能列名处理**：避免重复列名导致的数据处理错误
- **多层次清理**：文本、表格、DataFrame多级数据清理
- **容错机制**：确保在各种PDF格式下的稳定运行

## 项目结构

```
FileTo/
├── pdf_converter.py    # 核心转换逻辑
├── web_app.py          # Streamlit Web应用
├── cli.py              # 命令行接口
├── utils.py            # 工具函数
├── config.py           # 配置文件
└── requirements.txt    # 依赖包列表
```
