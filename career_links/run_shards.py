"""Run find_career_links.py as N parallel shard processes and wait.

    python career_links\\run_shards.py --shards 4 --workers 30 -- --no-render --no-search

Each shard writes career_links_shard<i>.csv (+ .log, console in .out).
Re-running resumes every shard.  Arguments after "--" go to every shard.
"""
import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    argv = sys.argv[1:]
    extra = []
    if "--" in argv:
        i = argv.index("--")
        argv, extra = argv[:i], argv[i + 1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--shards", type=int, default=4)
    ap.add_argument("--workers", type=int, default=30)
    ap.add_argument("--prefix", default=os.path.join(HERE, "career_links_shard"))
    args = ap.parse_args(argv)

    procs = []
    for i in range(args.shards):
        out = "%s%d.csv" % (args.prefix, i)
        cmd = [sys.executable, "-u", os.path.join(HERE, "find_career_links.py"),
               "--output", out, "--workers", str(args.workers),
               "--shard-index", str(i), "--shard-count", str(args.shards)] + extra
        console = open("%s%d.out" % (args.prefix, i), "a", encoding="utf-8")
        procs.append((subprocess.Popen(cmd, stdout=console, stderr=subprocess.STDOUT), console))
        print("started shard", i, "->", out, flush=True)
    try:
        while any(p.poll() is None for p, _ in procs):
            time.sleep(10)
    except KeyboardInterrupt:
        for p, _ in procs:
            p.terminate()
    for p, c in procs:
        c.close()
    print("exit codes:", [p.returncode for p, _ in procs])


if __name__ == "__main__":
    main()
