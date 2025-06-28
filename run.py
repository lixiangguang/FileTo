#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速启动脚本
提供便捷的工具启动方式
"""

import sys
import os
import subprocess
from pathlib import Path
import argparse
from loguru import logger


def check_dependencies():
    """检查依赖是否安装"""
    print("🔍 检查依赖...")
    
    required_packages = [
        'pandas', 'pdfplumber', 'tabula', 'camelot', 
        'fitz', 'streamlit', 'click', 'loguru'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} (未安装)")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  缺少依赖: {', '.join(missing_packages)}")
        print("请运行: pip install -r requirements.txt")
        return False
    
    print("✅ 所有依赖已安装")
    return True


def install_dependencies():
    """安装依赖"""
    print("📦 安装依赖...")
    
    requirements_file = Path(__file__).parent / 'requirements.txt'
    
    if not requirements_file.exists():
        print("❌ requirements.txt 文件不存在")
        return False
    
    try:
        subprocess.run([
            sys.executable, '-m', 'pip', 'install', '-r', str(requirements_file)
        ], check=True)
        print("✅ 依赖安装完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖安装失败: {e}")
        return False


def run_web_app():
    """启动Web应用"""
    print("🌐 启动Web应用...")
    
    web_app_file = Path(__file__).parent / 'web_app.py'
    
    if not web_app_file.exists():
        print("❌ web_app.py 文件不存在")
        return False
    
    try:
        subprocess.run([
            sys.executable, '-m', 'streamlit', 'run', str(web_app_file)
        ])
        return True
    except KeyboardInterrupt:
        print("\n⏹️  Web应用已停止")
        return True
    except Exception as e:
        print(f"❌ Web应用启动失败: {e}")
        return False


def run_cli(*args):
    """运行命令行工具"""
    print("💻 启动命令行工具...")
    
    cli_file = Path(__file__).parent / 'cli.py'
    
    if not cli_file.exists():
        print("❌ cli.py 文件不存在")
        return False
    
    try:
        subprocess.run([sys.executable, str(cli_file)] + list(args))
        return True
    except Exception as e:
        print(f"❌ 命令行工具运行失败: {e}")
        return False


def run_tests():
    """运行测试"""
    print("🧪 运行测试...")
    
    test_file = Path(__file__).parent / 'test_converter.py'
    
    if not test_file.exists():
        print("❌ test_converter.py 文件不存在")
        return False
    
    try:
        subprocess.run([sys.executable, str(test_file)])
        return True
    except Exception as e:
        print(f"❌ 测试运行失败: {e}")
        return False


def run_example():
    """运行示例"""
    print("📝 运行示例...")
    
    example_file = Path(__file__).parent / 'example.py'
    
    if not example_file.exists():
        print("❌ example.py 文件不存在")
        return False
    
    try:
        subprocess.run([sys.executable, str(example_file)])
        return True
    except Exception as e:
        print(f"❌ 示例运行失败: {e}")
        return False


def show_info():
    """显示工具信息"""
    print("📄 PDF转电子表格工具")
    print("=" * 30)
    print("\n🎯 功能特点:")
    print("• 支持多种PDF表格提取方法")
    print("• 自动选择最佳提取算法")
    print("• 输出标准Excel格式")
    print("• 高性能和稳定性")
    
    print("\n🔧 支持的提取方法:")
    print("• auto: 自动选择最佳方法")
    print("• pdfplumber: 适合结构化表格")
    print("• tabula: 适合复杂布局")
    print("• camelot: 适合高质量PDF")
    print("• pymupdf: 适合文本密集型PDF")
    
    print("\n📝 使用方式:")
    print("# 启动Web界面")
    print("python run.py web")
    print("")
    print("# 命令行转换")
    print("python run.py cli convert-pdf document.pdf")
    print("")
    print("# 运行测试")
    print("python run.py test")
    print("")
    print("# 查看示例")
    print("python run.py example")
    
    print("\n📦 项目文件:")
    project_files = [
        'pdf_converter.py',
        'web_app.py', 
        'cli.py',
        'utils.py',
        'config.py',
        'test_converter.py',
        'example.py',
        'requirements.txt',
        'README.md'
    ]
    
    for file in project_files:
        file_path = Path(__file__).parent / file
        status = "✅" if file_path.exists() else "❌"
        print(f"  {status} {file}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="PDF转电子表格工具启动器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python run.py web                    # 启动Web界面
  python run.py cli info               # 查看CLI帮助
  python run.py cli convert-pdf file.pdf  # 转换PDF文件
  python run.py test                   # 运行测试
  python run.py example                # 运行示例
  python run.py install                # 安装依赖
  python run.py check                  # 检查依赖
        """
    )
    
    parser.add_argument(
        'command',
        choices=['web', 'cli', 'test', 'example', 'install', 'check', 'info'],
        help='要执行的命令'
    )
    
    parser.add_argument(
        'args',
        nargs='*',
        help='传递给命令的参数'
    )
    
    parser.add_argument(
        '--force-install',
        action='store_true',
        help='强制重新安装依赖'
    )
    
    args = parser.parse_args()
    
    print("🚀 PDF转电子表格工具启动器")
    print("=" * 40)
    
    # 根据命令执行相应操作
    if args.command == 'info':
        show_info()
        
    elif args.command == 'check':
        check_dependencies()
        
    elif args.command == 'install':
        if args.force_install or not check_dependencies():
            install_dependencies()
        else:
            print("✅ 依赖已安装，使用 --force-install 强制重新安装")
            
    elif args.command == 'web':
        if check_dependencies():
            run_web_app()
        else:
            print("\n💡 请先安装依赖: python run.py install")
            
    elif args.command == 'cli':
        if check_dependencies():
            run_cli(*args.args)
        else:
            print("\n💡 请先安装依赖: python run.py install")
            
    elif args.command == 'test':
        if check_dependencies():
            run_tests()
        else:
            print("\n💡 请先安装依赖: python run.py install")
            
    elif args.command == 'example':
        if check_dependencies():
            run_example()
        else:
            print("\n💡 请先安装依赖: python run.py install")
    
    print("\n🎉 操作完成!")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️  用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        sys.exit(1)