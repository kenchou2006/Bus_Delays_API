import requests
import time
from datetime import datetime, timedelta
import sched
import sqlite3
import signal

#conn = sqlite3.connect(r'PyCode\bus_delay.db')
conn = sqlite3.connect(r'bus_delay.db')
cursor = conn.cursor()

# 創建新的表格來存儲每日統計數據
cursor.execute("""
CREATE TABLE IF NOT EXISTS daily_stats (
    date TEXT,
    route_name TEXT,
    delayed_count INTEGER,
    on_time_count INTEGER,
    PRIMARY KEY (date, route_name)
)
""")
conn.commit()

client_id = "jack306-946ef12f-2953-48a8"
client_secret = "ebbecc91-624c-416b-8d75-8b8b99630422"

class TDX:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = self.get_token()

    def get_token(self):
        url = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        return response.json().get('access_token')

    def get_response(self, url):
        headers = {'Authorization': f'Bearer {self.token}'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

url = "https://tdx.transportdata.tw/api/basic/v2/Bus/EstimatedTimeOfArrival/City/Taipei?&%24format=JSON"

bus_stops = {}  # 儲存每個公車站的資訊
check_interval = 60  # 每分鐘檢查一次
tolerance = 240  # 容許誤差（秒）

def calculate_delay(expected_time, actual_time):
    delay = max(0, int((actual_time - expected_time).total_seconds()))
    return delay

def format_time(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def update_daily_stats(route_name, is_delayed):
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 首先檢查是否已存在記錄
    cursor.execute("""
        SELECT delayed_count, on_time_count FROM daily_stats
        WHERE date = ? AND route_name = ?
    """, (today, route_name))
    result = cursor.fetchone()
    
    if result:
        delayed_count, on_time_count = result
        if is_delayed:
            delayed_count += 1
        else:
            on_time_count += 1
        
        cursor.execute("""
            UPDATE daily_stats
            SET delayed_count = ?, on_time_count = ?
            WHERE date = ? AND route_name = ?
        """, (delayed_count, on_time_count, today, route_name))
    else:
        # 如果不存在記錄，則插入新記錄
        cursor.execute("""
            INSERT INTO daily_stats (date, route_name, delayed_count, on_time_count)
            VALUES (?, ?, ?, ?)
        """, (today, route_name, 1 if is_delayed else 0, 0 if is_delayed else 1))
    
    conn.commit()

    # 打印更新的數據
    cursor.execute("""
        SELECT * FROM daily_stats
        WHERE date = ? AND route_name = ?
    """, (today, route_name))
    result = cursor.fetchone()
    print(f"已更新數據庫: 日期={result[0]}, 路線={result[1]}, 誤點次數={result[2]}, 準時次數={result[3]}, 總共次數={result[2]+result[3]}")

def check_delays():
    try:
        tdx = TDX(client_id, client_secret)
        current_data = tdx.get_response(url)
        current_time = datetime.now().replace(microsecond=0)

        for item in current_data:
            route_name = item['RouteName']['Zh_tw']
            stop_name = item['StopName']['Zh_tw']
            estimate_time = item.get('EstimateTime')
            stop_status = item.get('StopStatus')

            key = (route_name, stop_name)

            if key not in bus_stops:
                bus_stops[key] = {
                    'estimate_time': estimate_time,
                    'expected_arrival': (current_time + timedelta(seconds=estimate_time)).replace(microsecond=0) if estimate_time else None,
                    'status': stop_status,
                    'last_update': current_time
                }
            else:
                if stop_status == 1 and bus_stops[key]['status'] == 0:
                    # 公車已到站
                    actual_arrival = current_time
                    expected_arrival = bus_stops[key]['expected_arrival']
                    
                    if expected_arrival:
                        delay = calculate_delay(expected_arrival, actual_arrival)
                        is_delayed = delay > tolerance
                        update_daily_stats(route_name, is_delayed)
                        print(f"路線 {route_name} 在站點 {stop_name} {'誤點' if is_delayed else '準時'}到達")
                        print(f"預計到達時間: {format_time(expected_arrival)}, 實際到達時間: {format_time(actual_arrival)}, 延遲: {delay} 秒")

                    # 重置站點資訊
                    bus_stops[key] = {
                        'estimate_time': estimate_time,
                        'expected_arrival': (current_time + timedelta(seconds=estimate_time)).replace(microsecond=0) if estimate_time else None,
                        'status': stop_status,
                        'last_update': current_time
                    }
                elif stop_status == 0:
                    # 如果公車還沒到站，更新預估時間
                    bus_stops[key]['estimate_time'] = estimate_time
                    bus_stops[key]['expected_arrival'] = (current_time + timedelta(seconds=estimate_time)).replace(microsecond=0) if estimate_time else None
                    bus_stops[key]['last_update'] = current_time
                
                bus_stops[key]['status'] = stop_status

        # 檢查應該已經到達但尚未到達的公車
        for key, stop_info in list(bus_stops.items()):
            if stop_info['expected_arrival'] and current_time > stop_info['expected_arrival'] + timedelta(seconds=tolerance):
                route_name, stop_name = key
                update_daily_stats(route_name, True)
                print(f"路線 {route_name} 在站點 {stop_name} 誤點（未到站）")
                print(f"預計到達時間: {format_time(stop_info['expected_arrival'])}, 當前時間: {format_time(current_time)}")
                
                # 從追蹤列表中移除此站點
                del bus_stops[key]

    except Exception as e:
        print(f"發生錯誤: {e}")

    # 安排下一次檢查
    scheduler.enter(check_interval, 1, check_delays)

def signal_handler(sig, frame):
    print("捕捉到Ctrl+C，正在儲存數據並關閉...")
    conn.commit()
    conn.close()
    print("數據已儲存，程式已退出。")
    exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    scheduler = sched.scheduler(time.time, time.sleep)
    scheduler.enter(0, 1, check_delays)
    scheduler.run()
