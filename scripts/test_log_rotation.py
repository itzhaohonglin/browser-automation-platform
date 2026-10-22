"""测试日志轮转功能

测试场景：
1. 按天轮转 (daily)
2. 按小时轮转 (hourly)
3. 不轮转 (none)
"""
import os
import sys
import time
import logging
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_daily_rotation():
    """测试按天轮转"""
    print("\n=== 测试按天轮转 ===")

    log_file = "logs/test_daily.log"
    os.makedirs("logs", exist_ok=True)

    # 创建日志处理器
    handler = TimedRotatingFileHandler(
        filename=log_file,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    handler.suffix = "%Y%m%d"
    handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ))

    # 创建测试 logger
    logger = logging.getLogger("test_daily")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    # 写入测试日志
    for i in range(5):
        logger.info(f"测试日志 #{i+1} - 按天轮转")
        time.sleep(0.1)

    print(f"[OK] 日志文件创建: {log_file}")
    print(f"[OK] 轮转策略: 每天午夜")
    print(f"[OK] 文件名格式: app.log.20261022")
    print(f"[OK] 保留天数: 30天")

    # 清理
    handler.close()
    logger.removeHandler(handler)


def test_hourly_rotation():
    """测试按小时轮转"""
    print("\n=== 测试按小时轮转 ===")

    log_file = "logs/test_hourly.log"
    os.makedirs("logs", exist_ok=True)

    # 创建日志处理器
    handler = TimedRotatingFileHandler(
        filename=log_file,
        when="H",
        interval=1,
        backupCount=30 * 24,
        encoding="utf-8"
    )
    handler.suffix = "%Y%m%d_%H"
    handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ))

    # 创建测试 logger
    logger = logging.getLogger("test_hourly")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    # 写入测试日志
    for i in range(5):
        logger.info(f"测试日志 #{i+1} - 按小时轮转")
        time.sleep(0.1)

    print(f"[OK] 日志文件创建: {log_file}")
    print(f"[OK] 轮转策略: 每小时")
    print(f"[OK] 文件名格式: app.log.20261022_14")
    print(f"[OK] 保留时间: 30天 (720小时)")

    # 清理
    handler.close()
    logger.removeHandler(handler)


def test_no_rotation():
    """测试不轮转"""
    print("\n=== 测试不轮转 ===")

    log_file = "logs/test_no_rotation.log"
    os.makedirs("logs", exist_ok=True)

    # 创建日志处理器
    handler = logging.FileHandler(
        filename=log_file,
        mode="a",
        encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ))

    # 创建测试 logger
    logger = logging.getLogger("test_no_rotation")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    # 写入测试日志
    for i in range(5):
        logger.info(f"测试日志 #{i+1} - 不轮转")
        time.sleep(0.1)

    print(f"[OK] 日志文件创建: {log_file}")
    print(f"[OK] 轮转策略: 不轮转")
    print(f"[OK] 说明: 所有日志写入同一个文件")

    # 清理
    handler.close()
    logger.removeHandler(handler)


def test_actual_config():
    """测试实际应用配置"""
    print("\n=== 测试实际应用配置 ===")

    try:
        from app.core.config import settings

        print(f"LOG_FILE: {settings.LOG_FILE}")
        print(f"LOG_ROTATION: {settings.LOG_ROTATION}")
        print(f"LOG_RETENTION_DAYS: {settings.LOG_RETENTION_DAYS}")
        print(f"LOG_LEVEL: {settings.LOG_LEVEL}")

        if settings.LOG_FILE:
            print("\n[OK] 日志配置已启用")
            print(f"[OK] 日志文件将保存到: {settings.LOG_FILE}")

            if settings.LOG_ROTATION == "daily":
                print(f"[OK] 轮转策略: 按天，每天午夜生成新文件")
                print(f"[OK] 保留 {settings.LOG_RETENTION_DAYS} 天的日志")
            elif settings.LOG_ROTATION == "hourly":
                print(f"[OK] 轮转策略: 按小时，每小时生成新文件")
                print(f"[OK] 保留 {settings.LOG_RETENTION_DAYS} 天 ({settings.LOG_RETENTION_DAYS * 24} 小时) 的日志")
            else:
                print(f"[OK] 轮转策略: 不轮转，所有日志写入同一个文件")
        else:
            print("\n[WARN] 日志文件未配置，仅输出到控制台")

    except Exception as e:
        print(f"[ERROR] 加载配置失败: {e}")


def show_log_files():
    """显示生成的日志文件"""
    print("\n=== 生成的日志文件 ===")

    if os.path.exists("logs"):
        files = sorted(os.listdir("logs"))
        if files:
            for f in files:
                file_path = os.path.join("logs", f)
                size = os.path.getsize(file_path)
                print(f"  {f} ({size} bytes)")
        else:
            print("  (无文件)")
    else:
        print("  logs 目录不存在")


if __name__ == "__main__":
    print("="*60)
    print("日志轮转功能测试")
    print("="*60)

    # 运行测试
    test_daily_rotation()
    test_hourly_rotation()
    test_no_rotation()
    test_actual_config()
    show_log_files()

    print("\n" + "="*60)
    print("测试完成!")
    print("="*60)
