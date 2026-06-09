import uvicorn
import os

if __name__ == "__main__":
    # Port defaults to 8080 for development
    port = int(os.getenv("PORT", 8080))
    print(f"Starting Malt Radar backend on port {port}...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
