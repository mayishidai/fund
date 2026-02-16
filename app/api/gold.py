from fastapi import APIRouter
from app.services.gold_service import get_gold_price, get_gold_history, get_gold_minute_data

router = APIRouter()

# API端点：获取上海金实时数据
@router.get("/gold")
async def get_gold():
    return get_gold_price()

# API端点：获取上海金历史数据
@router.get("/gold/history")
async def get_gold_history_data():
    return {
        "code": "AU9999",
        "name": "上海金",
        "history": get_gold_history()
    }

# API端点：获取上海金分时数据
@router.get("/gold/minute")
async def get_gold_minute_data():
    return {
        "code": "AU9999",
        "name": "上海金",
        "minute_data": get_gold_minute_data()
    }
