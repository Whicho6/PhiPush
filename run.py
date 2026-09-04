from __future__ import annotations

import argparse
import os
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

from app.services.local_bootstrap import BootstrapError, ensure_real_environment


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Run PhiPush")
    parser.add_argument("--mock", action="store_true", help="use the bundled demo player")
    parser.add_argument("--host", default=os.getenv("PHIPUSH_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PHIPUSH_PORT", "8000")))
    args = parser.parse_args()
    if not args.mock and os.getenv("PHIPUSH_SKIP_BOOTSTRAP") != "1":
        try:
            wrote_env, chart_count = ensure_real_environment(Path(__file__).resolve().parent)
            if wrote_env:
                print("已在本机生成被 Git 忽略的 .env。")
            if chart_count is not None:
                print(f"已在本机生成被 Git 忽略的完整曲库：{chart_count} 张谱面。")
            if wrote_env:
                load_dotenv(override=False)
        except BootstrapError as exc:
            print(f"真实模式自动初始化失败：{exc}")
            print("程序将以 degraded 状态启动；可检查网络后重试。")
    os.environ["PHIPUSH_MOCK"] = "1" if args.mock else "0"
    print(f"PhiPush\nMode: {'MOCK' if args.mock else 'REAL'}\nURL: http://{args.host}:{args.port}")
    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
