from fastapi import APIRouter, HTTPException, Depends, Query, File, UploadFile
from fastapi.responses import Response
from typing import List
import csv
import io
from app.models import Fund, FundAmountUpdate
from app.database import get_db, close_db
from app.services.fund_service import get_fund_estimate, generate_mock_history_data
from app.api.auth import get_current_user, UserInDB

router = APIRouter(tags=["funds"])

# API端点：获取所有基金
@router.get("/funds")
async def get_funds(current_user: UserInDB = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT code, name, amount, shares FROM funds WHERE user_id = ?", (current_user.id,))
    funds = cursor.fetchall()
    conn.close()
    
    # 获取每个基金的实时净值预估
    result = []
    for fund in funds:
        estimate_data = get_fund_estimate(fund[0])
        # 计算当前市值
        nav = float(estimate_data["estimate"]) if estimate_data["estimate"] != "-" else 1.0
        # 正确的计算应该是使用份额乘以当前净值
        shares = fund[3] if len(fund) > 3 else 0
        current_value = shares * nav if shares > 0 else 0
        result.append({
            "code": fund[0],
            "name": fund[1],
            "amount": fund[2],
            "shares": fund[3] if len(fund) > 3 else 0,
            "estimate": estimate_data["estimate"],
            "estimate_change": estimate_data["estimate_change"],
            "time": estimate_data["time"],
            "type": estimate_data["type"],
            "sector": estimate_data["sector"],
            "current_value": current_value
        })
    return result

# API端点：添加基金
@router.post("/funds")
async def add_fund(fund: Fund, current_user: UserInDB = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    
    # 检查基金是否已存在
    cursor.execute("SELECT id FROM funds WHERE user_id = ? AND code = ?", (current_user.id, fund.code))
    existing_fund = cursor.fetchone()
    if existing_fund:
        conn.close()
        raise HTTPException(status_code=400, detail="基金已存在")
    
    # 获取当前净值
    estimate_data = get_fund_estimate(fund.code)
    nav = float(estimate_data["estimate"]) if estimate_data["estimate"] != "-" else 1.0
    
    # 计算份额
    shares = fund.amount / nav if nav > 0 else 0
    
    # 添加新基金
    cursor.execute("INSERT INTO funds (user_id, code, name, amount, shares) VALUES (?, ?, ?, ?, ?)", 
                  (current_user.id, fund.code, fund.name, fund.amount, shares))
    conn.commit()
    conn.close()
    
    return {"message": "基金添加成功", "fund": fund, "shares": shares}

# API端点：删除基金
@router.delete("/funds/{code}")
async def delete_fund(code: str, current_user: UserInDB = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    
    # 查找并删除基金
    cursor.execute("DELETE FROM funds WHERE user_id = ? AND code = ?", (current_user.id, code))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="基金不存在")
    
    conn.commit()
    conn.close()
    
    return {"message": "基金删除成功", "code": code}

# API端点：为基金追加金额或卖出
@router.put("/funds/{code}/amount")
async def update_fund_amount(code: str, amount_data: FundAmountUpdate, current_user: UserInDB = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    
    # 检查基金是否存在并获取当前金额和份额
    cursor.execute("SELECT amount, shares FROM funds WHERE user_id = ? AND code = ?", (current_user.id, code))
    fund = cursor.fetchone()
    if not fund:
        conn.close()
        raise HTTPException(status_code=404, detail="基金不存在")
    
    # 获取操作类型和金额
    is_sell = amount_data.sell
    amount = amount_data.amount
    current_amount = fund[0] or 0
    current_shares = fund[1] or 0
    
    # 获取当前净值
    estimate_data = get_fund_estimate(code)
    nav = float(estimate_data["estimate"]) if estimate_data["estimate"] != "-" else 1.0
    
    if is_sell:
        # 卖出操作：计算卖出的份额
        if amount < 0:
            conn.close()
            raise HTTPException(status_code=400, detail="卖出后金额不能为负")
        # 计算卖出的份额
        sell_shares = amount / nav if nav > 0 else 0
        new_shares = current_shares - sell_shares
        new_amount = amount
        message = "基金卖出成功"
    else:
        # 买入操作：计算新增的份额
        if amount <= 0:
            conn.close()
            raise HTTPException(status_code=400, detail="追加金额必须大于0")
        buy_shares = amount / nav if nav > 0 else 0
        new_shares = current_shares + buy_shares
        new_amount = current_amount + amount
        message = "金额追加成功"
    
    # 更新基金金额和份额
    cursor.execute("UPDATE funds SET amount = ?, shares = ? WHERE user_id = ? AND code = ?", 
                  (new_amount, new_shares, current_user.id, code))
    conn.commit()
    conn.close()
    
    return {"message": message, "code": code, "new_amount": new_amount, "new_shares": new_shares}

# API端点：获取基金历史净值数据
@router.get("/funds/{code}/history")
async def get_fund_history(code: str):
    try:
        # 尝试从天天基金网获取真实的历史净值数据
        import requests
        history_data = []
        fund_info = get_fund_estimate(code)
        
        # 构造天天基金网历史数据API URL
        # 注意：天天基金网的API可能会有变化，这里使用一个常见的接口格式
        url = f"http://api.fund.eastmoney.com/f10/lsjz?fundCode={code}&pageIndex=1&pageSize=31&startDate=&endDate=&_=1633048567890"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
            "Referer": f"http://fund.eastmoney.com/{code}.html"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        # 检查响应数据是否有效
        if data and "Data" in data and "LSJZList" in data["Data"]:
            lsjz_list = data["Data"]["LSJZList"]
            
            # 处理历史数据
            for item in lsjz_list:
                date = item.get("FSRQ", "")  # 日期
                nav = item.get("DWJZ", "0")  # 单位净值
                
                # 确保日期和净值有效
                if date and nav:
                    try:
                        nav_value = float(nav)
                        
                        # 生成开盘价、收盘价、最高价、最低价（基于单位净值）
                        import random
                        open_price = nav_value * (1 + (random.random() - 0.5) * 0.01)
                        close_price = nav_value
                        high_price = max(open_price, close_price) * (1 + random.random() * 0.01)
                        low_price = min(open_price, close_price) * (1 - random.random() * 0.01)
                        
                        history_data.append({
                            "date": date,
                            "open": round(open_price, 4),
                            "close": round(close_price, 4),
                            "high": round(high_price, 4),
                            "low": round(low_price, 4),
                            "price": round(nav_value, 4)
                        })
                    except ValueError:
                        pass
            
            # 如果获取到了真实数据，返回真实数据
            if history_data:
                return {
                    "code": code,
                    "name": fund_info["name"],
                    "history": history_data
                }
        
        # 如果没有获取到真实数据，使用模拟数据
        # 生成模拟的历史净值数据
        import datetime
        today = datetime.datetime.now()
        current_estimate = float(fund_info["estimate"]) if fund_info["estimate"] != "-" else 1.0
        
        # 生成30天的历史数据
        for i in range(30, 0, -1):
            date = today - datetime.timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            
            # 生成基于当前净值的随机历史数据
            # 添加一些随机波动，但保持整体趋势合理
            import random
            random_factor = 1 + (random.random() - 0.5) * 0.02
            historical_value = current_estimate * random_factor
            
            # 确保值为正数
            historical_value = max(0.01, historical_value)
            
            # 生成开盘价、收盘价、最高价、最低价
            open_price = historical_value * (1 + (random.random() - 0.5) * 0.01)
            close_price = historical_value
            high_price = max(open_price, close_price) * (1 + random.random() * 0.01)
            low_price = min(open_price, close_price) * (1 - random.random() * 0.01)
            
            history_data.append({
                "date": date_str,
                "open": round(open_price, 4),
                "close": round(close_price, 4),
                "high": round(high_price, 4),
                "low": round(low_price, 4),
                "price": round(historical_value, 4)
            })
        
        # 添加今天的数据
        today_str = today.strftime("%Y-%m-%d")
        history_data.append({
            "date": today_str,
            "open": round(current_estimate * (1 + (random.random() - 0.5) * 0.01), 4),
            "close": current_estimate,
            "high": round(current_estimate * (1 + random.random() * 0.01), 4),
            "low": round(current_estimate * (1 - random.random() * 0.01), 4),
            "price": current_estimate
        })
        
        return {
            "code": code,
            "name": fund_info["name"],
            "history": history_data
        }
    except Exception as e:
        print(f"获取历史数据失败: {e}")
        # 如果出错，返回模拟数据
        return {
            "code": code,
            "name": "未知基金",
            "history": generate_mock_history_data(code)
        }

# API端点：搜索基金
@router.get("/funds/search")
async def search_funds(keyword: str = Query(..., description="搜索关键词"), current_user: UserInDB = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT code, name, amount FROM funds WHERE user_id = ? AND (code LIKE ? OR name LIKE ?)", 
                  (current_user.id, f"%{keyword}%", f"%{keyword}%"))
    existing_funds = cursor.fetchall()
    conn.close()
    
    # 获取每个基金的实时净值预估
    result = []
    existing_codes = set()
    
    # 处理已存在的基金
    for fund in existing_funds:
        estimate_data = get_fund_estimate(fund[0])
        result.append({
            "code": fund[0],
            "name": fund[1],
            "amount": fund[2],
            "estimate": estimate_data["estimate"],
            "estimate_change": estimate_data["estimate_change"],
            "time": estimate_data["time"],
            "type": estimate_data["type"],
            "sector": estimate_data["sector"],
            "exists": True
        })
        existing_codes.add(fund[0])
    
    # 尝试搜索非存在的基金（如果关键词看起来像基金代码）
    if keyword.isdigit() and len(keyword) >= 4:
        # 检查该代码是否已在结果中
        if keyword not in existing_codes:
            estimate_data = get_fund_estimate(keyword)
            # 即使是未知基金也返回，让前端处理
            result.append({
                "code": estimate_data["code"],
                "name": estimate_data["name"],
                "amount": 0,
                "estimate": estimate_data["estimate"],
                "estimate_change": estimate_data["estimate_change"],
                "time": estimate_data["time"],
                "type": estimate_data["type"],
                "sector": estimate_data["sector"],
                "exists": False
            })
    
    return result

# API端点：根据基金代码获取基金信息
@router.get("/funds/info/{code}")
async def get_fund_info(code: str):
    # 获取基金信息
    estimate_data = get_fund_estimate(code)
    return {
        "code": estimate_data["code"],
        "name": estimate_data["name"],
        "estimate": estimate_data["estimate"],
        "estimate_change": estimate_data["estimate_change"],
        "time": estimate_data["time"],
        "type": estimate_data["type"],
        "sector": estimate_data["sector"]
    }

# API端点：导出基金数据
@router.get("/funds/export")
async def export_funds(current_user: UserInDB = Depends(get_current_user)):
    try:
        print(f"导出基金：用户ID={current_user.id}, 用户名={current_user.username}")
        
        # 连接数据库
        conn = get_db()
        cursor = conn.cursor()
        
        # 查询基金数据
        cursor.execute("SELECT code, name FROM funds WHERE user_id = ?", (current_user.id,))
        funds = cursor.fetchall()
        conn.close()
        
        print(f"找到基金数量：{len(funds)}")
        
        # 构建CSV格式数据
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["基金代码", "基金名称"])
        for fund in funds:
            writer.writerow(fund)
        
        csv_content = output.getvalue()
        print(f"CSV内容长度：{len(csv_content)}")
        
        # 返回CSV文件
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=funds_{current_user.username}.csv"
            }
        )
    except Exception as e:
        print(f"导出失败：{str(e)}")
        raise HTTPException(status_code=500, detail=f"导出失败：{str(e)}")

# API端点：获取单个基金详情
@router.get("/fund")
async def get_fund(code: str = Query(..., description="基金代码"), current_user: UserInDB = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT code, name, amount, shares FROM funds WHERE user_id = ? AND code = ?", (current_user.id, code))
    fund = cursor.fetchone()
    conn.close()
    
    if not fund:
        raise HTTPException(status_code=404, detail="基金不存在")
    
    # 获取实时净值预估
    estimate_data = get_fund_estimate(code)
    # 计算当前市值
    nav = float(estimate_data["estimate"]) if estimate_data["estimate"] != "-" else 1.0
    # 正确的计算应该是使用份额乘以当前净值
    shares = fund[3] if len(fund) > 3 else 0
    current_value = shares * nav if shares > 0 else 0
    return {
        "code": fund[0],
        "name": fund[1],
        "amount": fund[2],
        "shares": fund[3] if len(fund) > 3 else 0,
        "estimate": estimate_data["estimate"],
        "estimate_change": estimate_data["estimate_change"],
        "time": estimate_data["time"],
        "type": estimate_data["type"],
        "sector": estimate_data["sector"],
        "current_value": current_value
    }

# API端点：获取全部基金信息
@router.get("/funds/all")
async def get_all_funds():
    # 热门基金列表，包含更多基金
    hot_funds = [
        # 华夏基金
        {"code": "000001", "name": "华夏成长混合"},
        {"code": "000002", "name": "华夏大盘精选混合"},
        {"code": "000003", "name": "华夏现金增利货币"},
        {"code": "000004", "name": "华夏回报混合A"},
        {"code": "000005", "name": "华夏上证50ETF"},
        {"code": "000006", "name": "华夏海外收益债券A"},
        {"code": "000007", "name": "华夏全球股票(QDII)"},
        {"code": "000008", "name": "华夏稳增混合"},
        {"code": "000009", "name": "华夏兴华混合"},
        {"code": "000010", "name": "华夏策略混合"},
        
        # 易方达基金
        {"code": "110001", "name": "易方达平稳增长混合"},
        {"code": "110002", "name": "易方达策略成长混合"},
        {"code": "110003", "name": "易方达50指数"},
        {"code": "110005", "name": "易方达积极成长混合"},
        {"code": "110006", "name": "易方达货币A"},
        {"code": "110007", "name": "易方达稳健收益债券A"},
        {"code": "110008", "name": "易方达稳健收益债券B"},
        {"code": "110009", "name": "易方达价值精选混合"},
        {"code": "110010", "name": "易方达价值成长混合"},
        {"code": "110011", "name": "易方达优质精选混合(QDII)"},
        
        # 嘉实基金
        {"code": "070001", "name": "嘉实成长收益混合A"},
        {"code": "070002", "name": "嘉实理财增长混合"},
        {"code": "070003", "name": "嘉实理财稳健混合"},
        {"code": "070005", "name": "嘉实理财债券"},
        {"code": "070006", "name": "嘉实服务增值行业混合"},
        {"code": "070008", "name": "嘉实货币A"},
        {"code": "070009", "name": "嘉实超短债债券"},
        {"code": "070010", "name": "嘉实主题精选混合"},
        {"code": "070011", "name": "嘉实策略增长混合"},
        {"code": "070012", "name": "嘉实海外中国股票混合(QDII)"},
        
        # 南方基金
        {"code": "160201", "name": "南方稳健成长混合A"},
        {"code": "160202", "name": "南方稳健成长贰号混合"},
        {"code": "160204", "name": "南方稳健成长混合C"},
        {"code": "160205", "name": "南方成份精选混合A"},
        {"code": "160206", "name": "南方避险增值混合"},
        {"code": "160207", "name": "南方隆元产业主题混合"},
        {"code": "160208", "name": "南方全球精选配置(QDII-FOF)"},
        {"code": "160209", "name": "南方盛元红利混合"},
        {"code": "160210", "name": "南方优选价值混合A"},
        {"code": "160211", "name": "南方优选价值混合C"},
        
        # 广发基金
        {"code": "270001", "name": "广发聚富混合A"},
        {"code": "270002", "name": "广发稳健增长混合A"},
        {"code": "270004", "name": "广发货币A"},
        {"code": "270005", "name": "广发聚丰混合A"},
        {"code": "270006", "name": "广发策略优选混合"},
        {"code": "270007", "name": "广发大盘成长混合A"},
        {"code": "270008", "name": "广发核心精选混合A"},
        {"code": "270009", "name": "广发增强债券A"},
        {"code": "270010", "name": "广发沪深300ETF联接A"},
        {"code": "270011", "name": "广发中证500ETF联接A"},
        
        # 汇添富基金
        {"code": "519008", "name": "汇添富优势精选混合A"},
        {"code": "519018", "name": "汇添富均衡增长混合A"},
        {"code": "519068", "name": "汇添富成长焦点混合A"},
        {"code": "519069", "name": "汇添富价值精选混合A"},
        {"code": "519078", "name": "汇添富增强收益债券A"},
        {"code": "519088", "name": "汇添富策略回报混合A"},
        {"code": "519098", "name": "汇添富民营活力混合A"},
        {"code": "519118", "name": "汇添富医疗服务混合A"},
        {"code": "519128", "name": "汇添富消费行业混合A"},
        {"code": "519168", "name": "汇添富环保行业股票A"},
        
        # 富国基金
        {"code": "100016", "name": "富国天源平衡混合A"},
        {"code": "100018", "name": "富国天利增长债券A"},
        {"code": "100020", "name": "富国天益价值混合A"},
        {"code": "100022", "name": "富国天瑞强势混合A"},
        {"code": "100026", "name": "富国天合稳健混合A"},
        {"code": "100028", "name": "富国天成红利混合A"},
        {"code": "100032", "name": "富国天鼎中证红利指数增强A"},
        {"code": "100038", "name": "富国沪深300ETF联接A"},
        {"code": "100056", "name": "富国低碳环保混合A"},
        {"code": "100060", "name": "富国高新技术产业混合A"},
        
        # 博时基金
        {"code": "050001", "name": "博时价值增长混合A"},
        {"code": "050002", "name": "博时裕富沪深300指数A"},
        {"code": "050003", "name": "博时现金收益货币A"},
        {"code": "050004", "name": "博时精选混合A"},
        {"code": "050006", "name": "博时稳定价值债券A"},
        {"code": "050007", "name": "博时平衡配置混合A"},
        {"code": "050008", "name": "博时第三产业混合A"},
        {"code": "050009", "name": "博时新兴成长混合A"},
        {"code": "050010", "name": "博时特许价值混合A"},
        {"code": "050011", "name": "博时信用债券A"},
        
        # 工银瑞信基金
        {"code": "481001", "name": "工银瑞信核心价值混合A"},
        {"code": "481004", "name": "工银瑞信稳健成长混合A"},
        {"code": "481006", "name": "工银瑞信红利混合A"},
        {"code": "481008", "name": "工银瑞信大盘蓝筹混合A"},
        {"code": "481009", "name": "工银瑞信沪深300ETF联接A"},
        {"code": "481010", "name": "工银瑞信中小盘成长混合A"},
        {"code": "481012", "name": "工银瑞信消费服务混合A"},
        {"code": "481015", "name": "工银瑞信主题策略混合A"},
        {"code": "481017", "name": "工银瑞信基本面量化策略混合A"},
        {"code": "481018", "name": "工银瑞信添颐债券A"},
        
        # 鹏华基金
        {"code": "160607", "name": "鹏华价值优势混合(L0F)"},
        {"code": "160608", "name": "鹏华普天债券A"},
        {"code": "160609", "name": "鹏华普天收益混合"},
        {"code": "160610", "name": "鹏华动力增长混合(L0F)"},
        {"code": "160611", "name": "鹏华优质治理混合(L0F)"},
        {"code": "160612", "name": "鹏华丰收债券"},
        {"code": "160613", "name": "鹏华盛世创新混合(L0F)"},
        {"code": "160615", "name": "鹏华沪深300ETF联接A"},
        {"code": "160616", "name": "鹏华中证500指数(L0F)"},
        {"code": "160617", "name": "鹏华丰润债券(L0F)"}
    ]
    
    # 获取每个基金的实时净值预估
    result = []
    for fund in hot_funds:
        try:
            estimate_data = get_fund_estimate(fund["code"])
            result.append({
                "code": fund["code"],
                "name": fund["name"],
                "estimate": estimate_data["estimate"],
                "estimate_change": estimate_data["estimate_change"],
                "time": estimate_data["time"],
                "type": estimate_data["type"],
                "sector": estimate_data["sector"]
            })
        except Exception as e:
            print(f"获取基金{fund['code']}数据失败:", e)
            # 如果获取失败，添加一个默认数据
            result.append({
                "code": fund["code"],
                "name": fund["name"],
                "estimate": "0.00",
                "estimate_change": "0.00",
                "time": "",
                "type": "混合型",
                "sector": "未分类"
            })
    
    return result

# API端点：导入基金数据
@router.post("/funds/import")
async def import_funds(file: UploadFile = File(...), current_user: UserInDB = Depends(get_current_user)):
    import csv
    import io
    
    try:
        content = await file.read()
        content = content.decode("utf-8")
        reader = csv.reader(io.StringIO(content))
        next(reader)  # 跳过表头
        
        conn = get_db()
        cursor = conn.cursor()
        added_count = 0
        
        for row in reader:
            if len(row) >= 2:
                code = row[0].strip()
                name = row[1].strip()
                
                if code and name:
                    # 检查基金是否已存在
                    cursor.execute("SELECT id FROM funds WHERE user_id = ? AND code = ?", (current_user.id, code))
                    existing_fund = cursor.fetchone()
                    if not existing_fund:
                        cursor.execute("INSERT INTO funds (user_id, code, name) VALUES (?, ?, ?)", (current_user.id, code, name))
                        added_count += 1
        
        conn.commit()
        conn.close()
        
        return {"message": f"导入成功，新增 {added_count} 个基金"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"导入失败：{str(e)}")
