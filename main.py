from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import json
import subprocess
import os
import sys

app = FastAPI(title="SF Street Cleaning API")

# Mount the 'data' directory to serve static files
app.mount("/data", StaticFiles(directory="data"), name="data")

# Read the HTML content
with open("street-cleaning-map.html", "r") as file:
    html_content = file.read()

@app.get("/", response_class=HTMLResponse)
async def root():
    return html_content

@app.get("/neighborhoods")
async def get_neighborhoods():
    try:
        with open("data/neighborhoods.geojson", "r") as file:
            data = json.load(file)
        return JSONResponse(content=data)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Neighborhoods data not found")

@app.get("/neighborhoods/{neighborhood}")
async def get_neighborhood_data(neighborhood: str):
    file_path = f"data/neighborhoods/{neighborhood}.geojson"
    try:
        with open(file_path, "r") as file:
            data = json.load(file)
        return JSONResponse(content=data)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Data for {neighborhood} not found")


def run_transformation_script():
    script_path = os.path.join("pre_release_scripts", "transformations.py")
    try:
        subprocess.run([sys.executable, script_path], check=True)
        print("Data generation completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error running transformation script: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import uvicorn

    print("Running data generation script...")
    run_transformation_script()

    print("Starting the server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)