from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List, Dict, Tuple
import asyncio
from main import TokenBalanceTracker
from web3.middleware import async_geth_poa_middleware

# Определение FastAPI приложения
app = FastAPI()

# Конфигурация
RPC_URL = 'https://polygon-mainnet.infura.io/v3/edcb17ba2f524017b1192f0cad991fe5'
CONTRACT_ADDRESS = '0x1a9b54A3075119f1546C52cA0940551A6ce5d2D0'
ABI_PATH = 'abis/erc20.json'

# Инициализация TokenBalanceTracker
tracker = TokenBalanceTracker(RPC_URL, CONTRACT_ADDRESS, ABI_PATH)
tracker.web3.middleware_onion.inject(async_geth_poa_middleware, layer=0)

# Модели для запросов и ответов
class BalanceRequest(BaseModel):
    addresses: List[str]


@app.get("/get_balance")
async def get_balance(address: str):
    try:
        balance = await tracker.get_balance(address)
        return {"balance": balance}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_token_info")
async def get_token_info(address: str):
    try:
        info = await tracker.get_token_info(address)
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get_balance_batch")
async def get_balance_batch(request: BalanceRequest):
    try:
        balances = await tracker.get_balances_batch(request.addresses)
        return {"balances": balances}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_top_balances")
async def get_top_balances(top_n: int = 10):
    try:
        top_balances = await tracker.get_top_balances(top_n)
        return {"top_balances": top_balances}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_top_balances_with_dates")
async def get_top_balances_with_dates(top_n: int = 10):
    try:
        top_balances_with_dates = await tracker.get_top_balances_with_dates(top_n)
        return {"top_balances_with_dates": top_balances_with_dates}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Запуск сервера
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)