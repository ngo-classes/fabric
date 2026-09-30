#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import csv
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List, Dict

def human_rate(bps: float) -> str:
    n = bps
    for u in ["B/s", "KB/s", "MB/s", "GB/s", "TB/s"]:
        if n < 1024 or u == "TB/s":
            return f"{n:.2f} {u}"
        n /= 1024

def ensure_path_writable(path: Path) -> str:
    """
    Ensure 'path' exists and is writable; return detected fstype (best-effort).
    """
    path.mkdir(parents=True, exist_ok=True)
    fstype = "<unknown>"
    try:
        import psutil  # optional
        parts = {p.mountpoint: p.fstype for p in psutil.disk_partitions(all=True)}
        # find the deepest mountpoint that is a prefix of 'path'
        spath = str(path.resolve())
        candidates = [mp for mp in parts.keys() if spath.startswith(str(mp))]
        if candidates:
            fstype = parts[max(candidates, key=len)]
    except Exception:
        pass
    # quick write test
    test_file = path / ".cephfs_write_test.tmp"
    test_file.write_bytes(b"ok")
    assert test_file.read_bytes() == b"ok"
    test_file.unlink(missing_ok=True)
    return fstype

def ensure_mount_ok(mount: Path) -> str:
    if not mount.exists():
        raise FileNotFoundError(f"Mount path not found: {mount}")
    return ensure_path_writable(mount)

def create_source_file(src_file: Path, size_bytes: int) -> None:
    if src_file.exists() and src_file.stat().st_size == size_bytes:
        print(f"[prep] Source exists ({src_file.stat().st_size} bytes); reusing.")
        return

    src_file.parent.mkdir(parents=True, exist_ok=True)

    # Prefer fallocate (fast), then truncate (sparse), then dd, then Python
    if shutil.which("fallocate"):
        print("[prep] Creating source with fallocate ...")
        subprocess.run(["fallocate", "-l", str(size_bytes), str(src_file)], check=True)
    elif shutil.which("truncate"):
        print("[prep] Creating source with truncate (sparse) ...")
        subprocess.run(["truncate", "-s", str(size_bytes), str(src_file)], check=True)
    elif shutil.which("dd"):
        print("[prep] Creating source with dd (zeroes) ...")
        blk = 4 * 1024 * 1024
        count = size_bytes // blk
        rem = size_bytes % blk
        t0 = time.perf_counter()
        subprocess.run(["dd", "if=/dev/zero", f"of={src_file}", f"bs={blk}", f"count={count}", "status=none"], check=True)
        if rem:
            # append the remainder
            subprocess.run([
                "dd", "if=/dev/zero", f"of={src_file}",
                "bs=1", f"count={rem}", "oflag=append,seek_bytes", "status=none"
            ], check=True)
        t1 = time.perf_counter()
        print(f"[prep] dd completed in {t1-t0:.2f}s")
    else:
        print("[prep] Creating source with Python (zero fill) ...")
        chunk = b"\x00" * (4 * 1024 * 1024)
        written = 0
        with open(src_file, "wb") as f:
            while written < size_bytes:
                to_write = min(len(chunk), size_bytes - written)
                f.write(chunk[:to_write])
                written += to_write

    # Ensure exact size
    with open(src_file, "ab") as f:
        cur = src_file.stat().st_size
        if cur < size_bytes:
            f.truncate(size_bytes)

    print(f"[prep] Source ready: {src_file.stat().st_size} bytes")

def bench_python_copy(src: Path, dst: Path) -> Tuple[float, float]:
    buf = 8 * 1024 * 1024  # 8 MiB
    t0 = time.perf_counter()
    total = 0
    with open(src, "rb", buffering=0) as fsrc, open(dst, "wb", buffering=0) as fdst:
        while True:
            chunk = fsrc.read(buf)
            if not chunk:
                break
            fdst.write(chunk)
            total += len(chunk)
    t1 = time.perf_counter()
    elapsed = t1 - t0
    rate = total / elapsed if elapsed > 0 else float("nan")
    print(f"[python] {total} bytes in {elapsed:.2f}s -> {human_rate(rate)}")
    return rate, elapsed

def bench_rsync(src: Path, dst: Path) -> Optional[Tuple[float, float]]:
    if not shutil.which("rsync"):
        print("[rsync] not available; skipping")
        return None
    t0 = time.perf_counter()
    subprocess.run(["rsync", "--inplace", str(src), str(dst)], check=True)
    t1 = time.perf_counter()
    elapsed = t1 - t0
    rate = src.stat().st_size / elapsed if elapsed > 0 else float("nan")
    print(f"[rsync] {src.stat().st_size} bytes in {elapsed:.2f}s -> {human_rate(rate)}")
    return rate, elapsed

def bench_dd(src: Path, dst: Path) -> Optional[Tuple[float, float]]:
    if not shutil.which("dd"):
        print("[dd] not available; skipping")
        return None
    blk = 4 * 1024 * 1024
    size = src.stat().st_size
    count = size // blk
    rem = size % blk
    t0 = time.perf_counter()
    subprocess.run(["dd", f"if={src}", f"of={dst}", f"bs={blk}", f"count={count}", "iflag=fullblock", "oflag=direct", "status=none"], check=True)
    if rem:
        subprocess.run(["dd", f"if={src}", f"of={dst}", "bs=1", f"count={rem}", "oflag=append,seek_bytes,direct", "status=none"], check=True)
    t1 = time.perf_counter()
    elapsed = t1 - t0
    rate = size / elapsed if elapsed > 0 else float("nan")
    print(f"[dd] {size} bytes in {elapsed:.2f}s -> {human_rate(rate)}")
    return rate, elapsed

def bench_pv(src: Path, dst: Path) -> Optional[Tuple[float, float]]:
    if not shutil.which("pv"):
        print("[pv] not available; skipping")
        return None
    t0 = time.perf_counter()
    cmd = f"pv -f {src} | dd of={dst} bs=4M oflag=direct status=none"
    subprocess.run(cmd, shell=True, check=True)
    t1 = time.perf_counter()
    elapsed = t1 - t0
    rate = src.stat().st_size / elapsed if elapsed > 0 else float("nan")
    print(f"[pv|dd] {src.stat().st_size} bytes in {elapsed:.2f}s -> {human_rate(rate)}")
    return rate, elapsed

def main() -> int:
    ap = argparse.ArgumentParser(description="CephFS vs Local copy throughput benchmark")
    ap.add_argument("--mount", required=True, help="CephFS mount point")
    ap.add_argument("--size-gb", type=float, default=2.0, help="Test file size in GiB (default: 2)")
    ap.add_argument("--label", default="", help="Optional site/host label to include in CSV")
    ap.add_argument("--methods", default="python,rsync,dd,pv", help="Comma list of methods to run")
    ap.add_argument("--dest-subdir", default="benchmarks", help="Subdir under CephFS mount to write test files+CSV")
    ap.add_argument("--src-dir", default="/tmp/cephfs-bench-src", help="Local dir to place the source file")
    ap.add_argument("--keep-files", action="store_true", help="Keep destination test files (default: remove)")
    ap.add_argument("--csv-basename", default="", help="Override CSV basename (default: hostname_timestamp)")
    ap.add_argument("--compare-local", action="store_true", help="Also write to a local filesystem for comparison")
    ap.add_argument("--local-dest-dir", default="/tmp/cephfs-bench-local/benchmarks", help="Local destination dir for comparison writes")
    args = ap.parse_args()

    mount = Path(args.mount).resolve()
    ceph_fstype = ensure_mount_ok(mount)
    size_bytes = int(args.size_gb * (1024**3))

    # CephFS destination dirs
    ceph_dest_dir = mount / args.dest_subdir
    ceph_dest_dir.mkdir(parents=True, exist_ok=True)
    (ceph_dest_dir / "results").mkdir(parents=True, exist_ok=True)

    # Local destination dir (optional)
    local_dest_dir = Path(args.local_dest_dir).resolve()
    local_fstype = None
    if args.compare_local:
        local_fstype = ensure_path_writable(local_dest_dir)
        (local_dest_dir / "results").mkdir(parents=True, exist_ok=True)

    # Source area
    src_dir = Path(args.src_dir)
    src_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    host = socket.gethostname()
    csv_base = args.csv_basename or f"{host}_{stamp}"

    # Results CSV lives on CephFS (and on local if compare_local enabled)
    ceph_csv_path = ceph_dest_dir / "results" / f"{csv_base}.csv"
    local_csv_path = (local_dest_dir / "results" / f"{csv_base}.csv") if args.compare_local else None

    src_file = src_dir / f"bench_src_{stamp}.bin"
    create_source_file(src_file, size_bytes)

    uname = platform.uname()
    methods = [m.strip().lower() for m in args.methods.split(",") if m.strip()]

    rows: List[Dict[str, object]] = []

    def record(target: str, fstype: str, method: str, rate_bps: float, elapsed: float, size_b: int) -> None:
        rows.append({
            "timestamp": stamp,
            "hostname": host,
            "label": args.label,
            "target": target,             # "cephfs" or "local"
            "mount": str(mount) if target == "cephfs" else str(local_dest_dir),
            "fstype": fstype,
            "method": method,
            "size_bytes": size_b,
            "elapsed_s": elapsed,
            "bytes_per_sec": rate_bps,
            "MB_per_s": rate_bps / (1024**2),
            "GiB_per_s": rate_bps / (1024**3),
            "kernel": uname.release,
            "os": f"{uname.system} {uname.version}",
        })

    def _run_and_cleanup(dst: Path, bench_fn, target, fstype, method_name):
        """Run a single benchmark, record the result, and immediately remove the dst file."""
        out = bench_fn(src_file, dst)
        if out is not None:
            rate, el = out if isinstance(out, tuple) else (out, None)
            record(target, fstype, method_name, rate, el, size_bytes)
        if not args.keep_files:
            try:
                dst.unlink(missing_ok=True)
            except Exception:
                pass

    def run_suite(target: str, base_dir: Path, fstype: str) -> None:
        """
        Run all selected methods writing into 'base_dir'.
        Each destination file is removed immediately after its benchmark
        so that only one test file exists at a time on the volume.
        """
        dst_base = base_dir / f"bench_dst_{stamp}"

        if "python" in methods:
            _run_and_cleanup(dst_base.with_suffix(".py"), bench_python_copy, target, fstype, "python")

        if "rsync" in methods:
            _run_and_cleanup(dst_base.with_suffix(".rsync"), bench_rsync, target, fstype, "rsync")

        if "dd" in methods:
            _run_and_cleanup(dst_base.with_suffix(".dd"), bench_dd, target, fstype, "dd")

        if "pv" in methods:
            _run_and_cleanup(dst_base.with_suffix(".pv"), bench_pv, target, fstype, "pv|dd")

    # Run on CephFS
    run_suite("cephfs", ceph_dest_dir, ceph_fstype)

    # Run on local filesystem if requested
    if args.compare_local:
        run_suite("local", local_dest_dir, local_fstype or "<unknown>")

    # Write CSV(s)
    def write_rows(csv_path: Path) -> None:
        if not rows:
            return
        write_header = not csv_path.exists()
        with open(csv_path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            if write_header:
                writer.writeheader()
            writer.writerows(rows)
        print(f"[done] Wrote results: {csv_path}")

    if rows:
        write_rows(ceph_csv_path)
        if args.compare_local and local_csv_path:
            write_rows(local_csv_path)
    else:
        print("[done] No benchmarks ran; no CSV written.")

    return 0

if __name__ == "__main__":
    sys.exit(main())
