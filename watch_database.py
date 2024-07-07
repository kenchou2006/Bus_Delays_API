import sqlite3
from datetime import datetime

# 连接到数据库
#conn = sqlite3.connect(r'PyCode\bus_delay.db')
conn = sqlite3.connect(r'bus_delay.db')
cursor = conn.cursor()

# 计算所有路线的总体误点和准时比例
cursor.execute("""
    SELECT
        SUM(delayed_count) AS total_delayed,
        SUM(on_time_count) AS total_on_time,
        SUM(delayed_count) * 1.0 / (SUM(delayed_count) + SUM(on_time_count)) AS delay_ratio,
        SUM(on_time_count) * 1.0 / (SUM(delayed_count) + SUM(on_time_count)) AS on_time_ratio
    FROM daily_stats
""")
total_delayed, total_on_time, overall_delay_ratio, overall_on_time_ratio = cursor.fetchone()

print("所有路線的總誤點和準時比例:")
print(f"總誤點次數: {total_delayed}, 總準時次數: {total_on_time}, 誤點比例: {overall_delay_ratio:.2%}, 準時比例: {overall_on_time_ratio:.2%}")

# 计算每条路线的迟到比例前 7 名
cursor.execute("""
    SELECT route_name,
           SUM(delayed_count) * 1.0 / (SUM(delayed_count) + SUM(on_time_count)) AS delay_ratio
    FROM daily_stats
    GROUP BY route_name
    ORDER BY delay_ratio DESC
    LIMIT 7
""")
top_7_delay_ratios = cursor.fetchall()

print("\n每條路線的遲到比例前 7 名:")
for route_name, delay_ratio in top_7_delay_ratios:
    print(f"路線: {route_name}, 遲到比例: {delay_ratio:.2%}")

# 计算各个月份的误点统计
cursor.execute("""
    SELECT strftime('%Y-%m', date) AS month,
           SUM(delayed_count) AS total_delayed
    FROM daily_stats
    GROUP BY month
    ORDER BY month
""")
monthly_delays = cursor.fetchall()

print("\n各个月份的誤點統計:")
for month, total_delayed in monthly_delays:
    print(f"月份: {month}, 總誤點次數: {total_delayed}")

# 关闭数据库连接
conn.close()
