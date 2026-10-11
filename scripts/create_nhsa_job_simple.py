"""
使用SQL直接创建NHSA注册证号采集任务
"""
import pyodbc
import json
from datetime import datetime

# 数据库连接字符串（从.env读取或直接配置）
connection_string = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost;"
    "DATABASE=bap;"
    "UID=sa;"
    "PWD=YourPassword;"
    "Encrypt=no;"
)

try:
    # 连接数据库
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()

    # 插入任务
    query_params = json.dumps({"registration_no": "滇械注准20192140008"})

    cursor.execute("""
        INSERT INTO job_queue (config_id, query_params, status, retry_count, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (44, query_params, 'pending', 0, datetime.now()))

    conn.commit()

    # 获取插入的任务ID
    cursor.execute("SELECT @@IDENTITY")
    job_id = cursor.fetchone()[0]

    print(f"任务创建成功！")
    print(f"  任务ID: {int(job_id)}")
    print(f"  配置ID: 44")
    print(f"  状态: pending")
    print(f"  查询参数: {query_params}")
    print(f"\n执行命令：")
    print(f"  curl -X POST 'http://127.0.0.1:8000/task/run?config_id=44&limit=1'")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"错误: {e}")
