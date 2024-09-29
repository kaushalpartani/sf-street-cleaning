from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import json
import subprocess
import os
import sys
import urllib.request

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
def get_neighborhoods():
    try:
        with urllib.request.urlopen("https://raw.githubusercontent.com/kaushalpartani/sf-street-cleaning/refs/heads/main/data/neighborhoods.geojson") as response:
            if response.status != 200:
                raise HTTPException(status_code=response.status, detail="Error fetching neighborhoods data")
            data = json.loads(response.read().decode())
        return JSONResponse(content=data)
    except urllib.error.HTTPError as e:
        raise HTTPException(status_code=e.code, detail="Error fetching neighborhoods data")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.get("/neighborhoods/{neighborhood}")
def get_neighborhood_data(neighborhood: str):
    url = f"https://raw.githubusercontent.com/kaushalpartani/sf-street-cleaning/refs/heads/main/data/neighborhoods/{neighborhood}.geojson"
    try:
        with urllib.request.urlopen(url) as response:
            if response.status != 200:
                raise HTTPException(status_code=response.status, detail=f"Error fetching data for {neighborhood}")
            data = json.loads(response.read().decode())
        return JSONResponse(content=data)
    except urllib.error.HTTPError as e:
        raise HTTPException(status_code=e.code, detail=f"Data for {neighborhood} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


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

    print("Starting the server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)