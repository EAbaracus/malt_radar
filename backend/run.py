import uvicorn
import os

if __name__ == "__main__":
    # Port defaults to 8080 for development
    port = int(os.getenv("PORT", 8080))
    print(f"Starting Malt Radar backend on port {port}...")
    # server_header=False: suppress the "Server: uvicorn" banner for
    # fingerprint hardening (P1 scope 2026-08-06). uvicorn injects this
    # header at the protocol layer AFTER the app returns, so it cannot be
    # stripped by application middleware -- it must be disabled here.
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        server_header=False,
    )
