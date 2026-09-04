from __future__ import annotations

import argparse
import os

import uvicorn
from dotenv import load_dotenv


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Run PhiPush")
    parser.add_argument("--mock", action="store_true", help="use the bundled demo player")
    parser.add_argument("--host", default=os.getenv("PHIPUSH_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PHIPUSH_PORT", "8000")))
    args = parser.parse_args()
    os.environ["PHIPUSH_MOCK"] = "1" if args.mock else "0"
    print(f"PhiPush\nMode: {'MOCK' if args.mock else 'REAL'}\nURL: http://{args.host}:{args.port}")
    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
