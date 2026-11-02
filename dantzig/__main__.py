import argparse
import uvicorn

parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, default=5241)
args = parser.parse_args()
uvicorn.run("dantzig.app:app", host="127.0.0.1", port=args.port)
