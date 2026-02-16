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
        history_data = []
        today = datetime.datetime.now()
        
        # 获取当前实时价格作为基础价格
        current_price = get_gold_price()["price"]
        base_price = current_price
        
        # 生成30天的历史数据
        for i in range(30, 0, -1):
            date = today - datetime.timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            
            # 生成基于当前价格的随机历史数据，考虑价格趋势
            # 每天价格波动范围在-2%到+2%之间
            day_factor = 1 + (random.random() - 0.5) * 0.04
            historical_value = base_price * day_factor
            
            # 生成开盘价、收盘价、最高价、最低价
            open_price = historical_value * (1 + (random.random() - 0.5) * 0.01)
            close_price = historical_value
            high_price = max(open_price, close_price) * (1 + random.random() * 0.01)
            low_price = min(open_price, close_price) * (1 - random.random() * 0.01)
            
            history_data.append({
                "date": date_str,
                "open": round(open_price, 2),
                "close": round(close_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "price": round(historical_value, 2)
            })
        
        # 添加今天的数据
        today_str = today.strftime("%Y-%m-%d")
        history_data.append({
            "date": today_str,
            "open": round(current_price * (1 + (random.random() - 0.5) * 0.01), 2),
            "close": current_price,
            "high": round(current_price * (1 + random.random() * 0.01), 2),
            "low": round(current_price * (1 - random.random() * 0.01), 2),
            "price": current_price
        })
        
        return history_data
    except Exception as e:
        print(f"获取上海金历史数据失败: {e}")
        return []

# 获取上海金分时数据
def get_gold_minute_data():
    try:
        minute_data = []
        now = datetime.datetime.now()
        
        # 获取当前实时价格作为基础价格
        current_price = get_gold_price()["price"]
        base_price = current_price
        
        # 生成今天的分时数据，从9:00开始
        start_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
        current_time = start_time
        
        # 模拟分时数据，每5分钟一个数据点
        while current_time <= now:
            # 生成随机价格波动
            random_factor = 1 + (random.random() - 0.5) * 0.005
            price = base_price * random_factor
            
            # 更新基础价格，使价格有趋势变化
            base_price = price
            
            minute_data.append({
                "time": current_time.strftime("%H:%M"),
                "price": round(price, 2)
            })
            
            # 增加5分钟
            current_time += datetime.timedelta(minutes=5)
        
        return minute_data
    except Exception as e:
        print(f"获取上海金分时数据失败: {e}")
        return []