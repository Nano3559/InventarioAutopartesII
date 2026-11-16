"""CLI V2-08. Por defecto solo prepara. No existe flag para autorizar fit."""
import argparse
import json
from pathlib import Path
import sys

if __package__ in (None,""):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v2.experiments import prepare_run,execute_experiments


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id",required=True)
    parser.add_argument("--action",choices=["prepare","execute"],default="prepare")
    args=parser.parse_args()
    try:
        path,result=(prepare_run if args.action=="prepare" else execute_experiments)(args.run_id)
        print(json.dumps({"path":str(path),"status":result.get("status",result.get("selection",{}).get("status")),
                          "test_loaded":False},ensure_ascii=True))
    except PermissionError as exc:
        print(json.dumps({"status":"TRAINING_DISABLED","reason":str(exc)},ensure_ascii=True))
        sys.exit(2)
