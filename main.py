from fastapi.responses import HTMLResponse
from app import app
from app.database import init_db

# 初始化数据库
init_db()

# 根路径返回前端页面
@app.get("/", response_class=HTMLResponse)
async def read_root():
    # 读取并返回index.html内容
    try:
        with open("static/index.html", "r", encoding="utf-8") as f:
            return f.read()
    except:
        # 如果index.html不存在，返回一个简单的提示
        return "<h1>基金实时净值预估系统</h1><p>请确保前端文件已部署到static目录</p>"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
