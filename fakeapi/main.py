from fastapi import FastAPI, HTTPException
from random import randint
import asyncio

app = FastAPI()


@app.get("/")
async def root():
    number = randint(0, 2)
    match number:
        case 0:
            print("one")
            return {"message": "tuenione"}
        case 1:
            print("ello")
            await asyncio.sleep(36000000000)
            print("gobye")
            return {"message": "This will never be returned"}
        case 2:
            print("tree")
            return HTTPException(status_code=418, detail="I'm a teapot")
