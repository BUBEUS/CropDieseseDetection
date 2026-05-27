from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
app = FastAPI()


app.mount("/photos", StaticFiles(directory="/app/photos"), name="photos")
@app.get("/")
def read_root():
    return FileResponse("index.html")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
