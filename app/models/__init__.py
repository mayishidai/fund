from pydantic import BaseModel
from typing import Optional

# 用户模型
class User(BaseModel):
    username: str
    password: str

class UserInDB(User):
    id: int

# 令牌模型
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# 基金模型
class Fund(BaseModel):
    code: str
    name: str
    amount: float = 0

class FundInDB(Fund):
    id: int
    user_id: int
    shares: float = 0

# 基金金额更新模型
class FundAmountUpdate(BaseModel):
    amount: float
    sell: bool = False

# 上海金模型
class GoldPrice(BaseModel):
    price: float
    change: float
    time: str
    name: str
    code: str
    source: str

# 黄金历史数据模型
class GoldHistoryItem(BaseModel):
    date: str
    open: float
    close: float
    high: float
    low: float
    price: float

# 黄金分时数据模型
class GoldMinuteItem(BaseModel):
    time: str
    price: float