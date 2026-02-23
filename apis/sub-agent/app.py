from fastapi import FastAPI, status

app = FastAPI()

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {"status": "ok"}

@app.get("/")
def read_root():
    return "I'm a sub agent please connect me to the main agent"