#!/usr/bin/env python3

import argparse
import os
import shutil
import subprocess
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment


def abspath(path: str) -> Path:
    return Path(path).expanduser().resolve()


def run(cmd: str, env: dict = None, action: str = "RUN"):
    print(f"[{action}] {' '.join(map(str, cmd))}")
    subprocess.run(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)


CONFIGS = {
    "Original": ("default", "false"),
    "Pre-RA": ("ropsched", "false"),
    "Post-RA": ("default", "true"),
    "Both": ("ropsched", "true"),
}

BENCHMARK_TARGETS =  {
    "mimalloc": "libmimalloc.so.3.0",
    "chocolate-doom": "src/chocolate-doom",
    "zlib": "libz.so.1.3.1"
}

CLANG = abspath("llvm-ropsched/build/bin/clang")
GSA = abspath("GadgetSetAnalyzer")
BENCHMARKS = abspath("samples")
BINARIES_DESTINATION = BENCHMARKS.parent / "binaries"
RESULTS = abspath("results")


def build_benchmark(repository: Path, flags: str) -> list[Path]:
    resulting_binaries = []

    for config, misched_flags in CONFIGS.items():
        build_directory = repository / f"build/{config}"
        build_directory.mkdir(parents=True, exist_ok=True)
        config_flags = flags + f"-mllvm -misched={misched_flags[0]} -mllvm -misched-postra={misched_flags[1]}"

        # Set up the flags.
        env = os.environ.copy()
        env["CC"] = str(CLANG)
        env["CXX"] = str(CLANG)
        env["CFLAGS"] = config_flags
        env["CXXFLAGS"] = config_flags

        # Generate CMake file and build the benchmark.
        run(["cmake", "-S", str(repository), "-B", str(build_directory)], env=env, action=" CMAKE ")
        run(["cmake", "--build", str(build_directory)], env=env, action=" BUILD ")

        # Copy the resulting binary to a separate folder for uniformity.
        binary_path = build_directory / BENCHMARK_TARGETS[repository.name]
        destination_path = BINARIES_DESTINATION / f"{repository.name}.{config}"
        run(["cp", str(binary_path), str(destination_path)], action=" COPY  ")

        resulting_binaries.append(destination_path)

    return resulting_binaries



def compare_benchmark(name: str, binaries: list[Path]) -> Path:
    original = str(binaries[0])
    variants = [f"{variant.suffix[1:]}={variant}" for variant in binaries[1:]]
    old_results = str(RESULTS / name)

    if os.path.isdir(old_results):
        shutil.rmtree(old_results)

    run(["python3", GSA / "src/GSA.py", original, "--variants", *variants, "--output_metrics", "--result_folder_name", name], action="COMPARE")

    return abspath("results") / f"{name}/Gadget Quality.csv"


def concatenate_results(results: list[Path]):
    dataframes = []

    for csv in results:
        df = pd.read_csv(csv)
        df.insert(0, "Benchmark", csv.parent.name)
        dataframes.append(df)

    data = pd.concat(dataframes, ignore_index=True)

    output = abspath("results.xlsx")
    data.to_excel(output, index=False)
    wb = load_workbook(output)
    ws = wb.active

    start_row = 2
    current_benchmark = ws.cell(row=2, column=1).value

    for row in range(2, ws.max_row + 2):
        benchmark = ws.cell(row=row, column=1).value

        if benchmark != current_benchmark:
            ws.merge_cells(start_row=start_row, start_column=1, end_row=row - 1, end_column=1)
            ws.cell(row=start_row, column=1).alignment = Alignment(vertical="center", horizontal="center")

            current_benchmark = benchmark
            start_row = row

    wb.save(output)


def main():
    parser = argparse.ArgumentParser(description="Benchmark LLVM scheduler configurations with GadgetSetAnalyzer.")
    parser.add_argument("--benchmarks", default="all", help="Benchmarks to run (comma-separated list)")
    parser.add_argument("--flags", default="-O2 -mllvm -enable-misched=true", help="Clang flags to use when compiling benchmarks")
    args = parser.parse_args()

    benchmarks = [repository for repository in BENCHMARKS.iterdir()]

    if args.benchmarks != "all":
        benchmarks = filter(lambda benchmark: benchmark.name in args.benchmarks.split(","), benchmarks)

    results = []

    for benchmark in benchmarks:
        print(f"\nBenchmark: {benchmark.name}")
        binaries = build_benchmark(benchmark, args.flags)
        output = compare_benchmark(benchmark.name, binaries)
        results.append(output)

    concatenate_results(results)


if __name__ == "__main__":
    main()
