import requests
import re
import random
import datetime

# 获取上海金实时数据
def get_gold_price():
    try:
        # 从工商银行获取积存金实时数据（上海黄金交易所数据）
        # 数据源：中国工商银行（提供上海黄金交易所实时数据）
        # 上海黄金交易所官方网站：https://www.sge.com.cn/
        
        # 工商银行积存金行情查询页面
        url = "https://mybank.icbc.com.cn/icbc/newperbank/perbank3/gold/goldaccrual_query_out.jsp"
        response = requests.get(url, timeout=5)
        response.encoding = 'utf-8'
        html = response.text
        
        # 使用正则表达式提取积存金价格数据
        # 匹配积存金实时价格
        price_match = re.search(r'积存金\s+([\d.]+)', html)
        # 匹配更新时间
        time_match = re.search(r'更新时间:(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', html)
        
        if price_match and time_match:
            price = float(price_match.group(1))
            update_time = time_match.group(1)
            
            # 计算涨跌幅（基于前一天的价格，这里简化处理）
            # 实际应用中应该从历史数据中获取前一天的价格
            change = 0.0  # 暂时设置为0，实际应用中需要计算
            
            return {
                "price": round(price, 2),
                "change": round(change, 2),
                "time": update_time,
                "name": "上海金（积存金）",
                "code": "AU9999",
                "source": "中国工商银行（上海黄金交易所数据）"
            }
        else:
            # 如果工商银行数据获取失败，尝试从东方财富网获取黄金9999数据
            url = "https://quote.eastmoney.com/q/118.AU9999.html"
            response = requests.get(url, timeout=5)
            response.encoding = 'utf-8'
            html = response.text
            
            # 使用正则表达式提取黄金9999价格数据
            gold_match = re.search(r'黄金9999.*?最新价.*?([\d.]+)', html, re.DOTALL)
            change_match = re.search(r'黄金9999.*?涨跌幅.*?([\d.-]+)%', html, re.DOTALL)
            
            if gold_match and change_match:
                price = float(gold_match.group(1))
                change = float(change_match.group(1))
                
                return {
                    "price": round(price, 2),
                    "change": round(change, 2),
                    "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "name": "上海金（黄金9999）",
                    "code": "AU9999",
                    "source": "东方财富网（上海黄金交易所数据）"
                }
            else:
                # 如果无法获取实时数据，使用模拟数据
                base_price = 1125.0  # 基础价格，符合实际上海金价格水平
                price = base_price + (random.random() - 0.5) * 20  # 随机波动
                change = (price - base_price) / base_price * 100  # 涨跌幅
                
                return {
                    "price": round(price, 2),
                    "change": round(change, 2),
                    "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "name": "上海金",
                    "code": "AU9999",
                    "source": "模拟数据（基于上海黄金交易所价格水平）"
                }
    except Exception as e:
        print(f"获取上海金数据失败: {e}")
        # 返回默认数据
        return {
            "price": 1125.0,
            "change": 0.0,
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "name": "上海金",
            "code": "AU9999",
            "source": "默认数据（基于上海黄金交易所价格水平）"
        }

# 获取上海金历史数据
def get_gold_history():
    try:
        print("获取实时黄金历史数据...")
        history_data = []
        
        # 尝试从东方财富网获取黄金9999的历史数据
        url = "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=118.AU9999&fields1=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13&fields2=f51,f52,f53,f54,f55,f56,f57,f58&klt=101&fqt=0&end=20500101&lmt=31"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
            "Referer": "https://quote.eastmoney.com/q/118.AU9999.html"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        if data and data.get("data") and data["data"].get("klines"):
            klines = data["data"]["klines"]
            
            for kline in klines:
                parts = kline.split(",")
                if len(parts) >= 5:
                    # 解析日期和价格数据
                    date_str = parts[0]
                    open_price = float(parts[1])
                    high_price = float(parts[2])
                    low_price = float(parts[3])
                    close_price = float(parts[4])
                    
                    history_data.append({
                        "date": date_str,
                        "open": round(open_price, 2),
                        "close": round(close_price, 2),
                        "high": round(high_price, 2),
                        "low": round(low_price, 2),
                        "price": round(close_price, 2)
                    })
            
            if history_data:
                print(f"成功获取{len(history_data)}天的黄金历史数据")
                return history_data
        
        # 如果东方财富网数据获取失败，尝试从Investing.com获取黄金历史数据
        url = "https://api.investing.com/api/financialdata/8830/historical/chart/?period=86400&start=1640995200&end=1643673600"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        if data and data.get("data"):
            for item in data["data"]:
                if len(item) >= 6:
                    timestamp = item[0]
                    open_price = item[1]
                    high_price = item[2]
                    low_price = item[3]
                    close_price = item[4]
                    
                    # 转换时间戳为日期字符串
                    date_obj = datetime.datetime.fromtimestamp(timestamp)
                    date_str = date_obj.strftime("%Y-%m-%d")
                    
                    history_data.append({
                        "date": date_str,
                        "open": round(open_price, 2),
                        "close": round(close_price, 2),
                        "high": round(high_price, 2),
                        "low": round(low_price, 2),
                        "price": round(close_price, 2)
                    })
            
            if history_data:
                print(f"成功获取{len(history_data)}天的黄金历史数据")
                return history_data
        
        # 如果所有数据源都失败，返回空数据表示获取失败
        print("无法获取实时黄金历史数据")
        return []
        
    except Exception as e:
        print(f"获取上海金历史数据失败: {e}")
        # 返回空数据表示获取失败
        return []

# 获取上海金分时数据
def get_gold_minute_data():
    print("获取实时黄金分时数据...")
    
    try:
        # 尝试从东方财富网获取黄金9999的实时分时数据
        url = "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=118.AU9999&fields1=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13&fields2=f51,f52,f53,f54,f55,f56,f57,f58&klt=1&fqt=0&end=20500101&lmt=1000"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
            "Referer": "https://quote.eastmoney.com/q/118.AU9999.html"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        if data and data.get("data") and data["data"].get("klines"):
            klines = data["data"]["klines"]
            minute_data = []
            
            for kline in klines:
                parts = kline.split(",")
                if len(parts) >= 3:
                    # 解析时间和价格
                    time_str = parts[0]
                    close_price = float(parts[2])
                    
                    # 格式化时间为HH:MM
                    time_obj = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M")
                    time_formatted = time_obj.strftime("%H:%M")
                    
                    minute_data.append({
                        "time": time_formatted,
                        "price": round(close_price, 2)
                    })
            
            if minute_data:
                print(f"成功获取{len(minute_data)}个分时数据点")
                return minute_data
        
        # 如果东方财富网数据获取失败，尝试其他数据源
        # 尝试从Investing.com获取黄金分时数据
        url = "https://api.investing.com/api/financialdata/8830/historical/chart/?period=60&start=1640995200&end=1641081600"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        if data and data.get("data"):
            minute_data = []
            for item in data["data"]:
                if len(item) >= 2:
                    timestamp = item[0]
                    price = item[1]
                    
                    # 转换时间戳为HH:MM
                    time_obj = datetime.datetime.fromtimestamp(timestamp)
                    time_formatted = time_obj.strftime("%H:%M")
                    
                    minute_data.append({
                        "time": time_formatted,
                        "price": round(price, 2)
                    })
            
            if minute_data:
                print(f"成功获取{len(minute_data)}个分时数据点")
                return minute_data
        
        # 如果所有数据源都失败，返回空数据表示获取失败
        print("无法获取实时黄金分时数据")
        return []
        
    except Exception as e:
        print(f"获取黄金分时数据失败: {e}")
        # 返回空数据表示获取失败
        return []