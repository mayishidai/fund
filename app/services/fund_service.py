import requests
import json
import random
import datetime
from app.database import get_db, close_db

# 获取基金类型和板块信息
def get_fund_type_and_sector(code):
    try:
        # 这里可以根据基金代码的规则判断基金类型
        # 也可以使用其他API获取更详细的信息
        # 以下是基于基金代码的简单判断
        if code.startswith('00') or code.startswith('15'):
            fund_type = "混合型"
        elif code.startswith('16'):
            fund_type = "股票型"
        elif code.startswith('20'):
            fund_type = "债券型"
        elif code.startswith('30'):
            fund_type = "指数型"
        elif code.startswith('40') or code.startswith('110022') or code.startswith('161128') or code.startswith('513050'):
            fund_type = "QDII"
        elif code.startswith('50'):
            fund_type = "货币型"
        elif code.startswith('60'):
            fund_type = "保本型"
        else:
            fund_type = "其他"
        
        # 简单的板块判断，实际应用中可能需要更复杂的逻辑
        sector = "金融地产" if "金融" in code or "地产" in code else "其他"
        
        return {
            "type": fund_type,
            "sector": sector
        }
    except Exception as e:
        return {
            "type": "-",
            "sector": "-"
        }

# 获取基金实时净值预估
def get_fund_estimate(code):
    try:
        # 使用天天基金网API获取实时净值预估
        url = f"http://fundgz.1234567.com.cn/js/{code}.js"
        response = requests.get(url, timeout=5)
        data = response.text.strip()[8:-2]  # 去掉回调函数包装
        fund_data = json.loads(data)
        
        # 获取基金类型和板块信息
        type_and_sector = get_fund_type_and_sector(code)
        
        return {
            "code": fund_data["fundcode"],
            "name": fund_data["name"],
            "estimate": fund_data["gsz"],
            "estimate_change": fund_data["gszzl"],
            "time": fund_data["gztime"],
            "type": type_and_sector["type"],
            "sector": type_and_sector["sector"]
        }
    except Exception as e:
        # 如果API调用失败，使用模拟的涨跌规则
        type_and_sector = get_fund_type_and_sector(code)
        
        # 获取或生成历史净值
        nav, change_rate = generate_fund_nav(code)
        
        # 确保时间字段实时更新
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        return {
            "code": code,
            "name": "未知基金",
            "estimate": str(nav),
            "estimate_change": str(change_rate),
            "time": current_time,
            "type": type_and_sector["type"],
            "sector": type_and_sector["sector"]
        }

# 生成或获取基金净值
def generate_fund_nav(code):
    """
    生成基金净值，实现涨跌规则
    1. 首先尝试从历史净值表中获取最近的净值
    2. 如果没有历史数据，生成初始净值
    3. 根据涨跌规则生成新的净值
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # 获取今天的日期
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # 尝试获取最近的净值
    cursor.execute("SELECT nav FROM fund_history WHERE code = ? ORDER BY date DESC LIMIT 1", (code,))
    last_nav = cursor.fetchone()
    
    if last_nav:
        # 有历史数据，根据涨跌规则生成新净值
        nav = last_nav[0]
        # 涨跌规则：-2% 到 +2% 之间的随机波动
        change_rate = (random.random() - 0.5) * 4
        new_nav = nav * (1 + change_rate / 100)
    else:
        # 没有历史数据，生成初始净值
        new_nav = 1.0 + random.random() * 0.5
        change_rate = 0
    
    # 保存今天的净值
    try:
        cursor.execute("INSERT OR REPLACE INTO fund_history (code, date, nav, change_rate) VALUES (?, ?, ?, ?)", 
                      (code, today, new_nav, change_rate))
        conn.commit()
    except Exception as e:
        print(f"保存净值历史失败: {e}")
    
    close_db(conn)
    return new_nav, round(change_rate, 2)

# 生成模拟的历史数据
def generate_mock_history_data(code):
    history_data = []
    today = datetime.datetime.now()
    
    # 生成31天的模拟数据
    for i in range(31, 0, -1):
        date = today - datetime.timedelta(days=i-1)
        date_str = date.strftime("%Y-%m-%d")
        
        # 生成随机价格
        price = 1 + (random.random() - 0.5) * 0.2
        open_price = price * (1 + (random.random() - 0.5) * 0.01)
        close_price = price
        high_price = max(open_price, close_price) * (1 + random.random() * 0.01)
        low_price = min(open_price, close_price) * (1 - random.random() * 0.01)
        
        history_data.append({
            "date": date_str,
            "open": round(open_price, 4),
            "close": round(close_price, 4),
            "high": round(high_price, 4),
            "low": round(low_price, 4),
            "price": round(price, 4)
        })
    
    return history_data