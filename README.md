[ROP]: https://en.wikipedia.org/wiki/Return-oriented_programming
[JOP]: https://developer.arm.com/documentation/102433/0200/Jump-oriented-programming
[COP]: https://www.scribd.com/document/937825119/Pure-Call-Oriented-Programming-PCOP


# RopSched

**RopSched** is an instruction-scheduling approach to limit the number of code reuse gadgets in programs compiled with LLVM. 

This work was completed as part of a research project for the graduate program in computer science at **California State University, Sacramento** under the guidance of **Dr. Ghassan Shobaki** and **Dr. Syed Badruddoja**.

## Background
Binary exploitation is traditionally achieved by overflowing some portion of memory (usually on the stack) and overwriting a return address. By doing so, an attacker can redirect program execution to a payload (usually in the same buffer) to achieve arbitrary code execution. To help prevent simple exploits like this, platform vendors developed defense mechanisms such as **Data Execution Prevention (DEP)** on Windows and **No eXecute (NX)** on Linux.

DEP and NX remove the executable permissions from the sections of memory that store data, which effectively disarms payloads injected in this way. However, clever researchers figured out how utilize existing program instructions to craft a payload anyway. By controlling the return address (through a buffer overflow), an attacker can jump to a short sequence of instructions that *already exists* elsewhere in the binary. If this sequence ends in another `return` instruction, the attacker can redirect control flow to a different sequence of instructions. By repeating this process, an attacker can start to chain together short sequences of assembly instructions to build out their payload by piece by piece. Since they aren't injecting any *new* instructions into the program and just reusing what is already available from the existing program logic, this bypasses the aforementioned defenses. These short instruction sequences are called **gadgets** and the process of chaining them together to achieve code execution is known as [return-oriented programming (ROP)][ROP].

Similar techniques also exist for instruction sequences that end in `jump` and `call` instructions as well because they also change the control flow of a program and can be chained together. Unsurprisingly, these techniques are called [jump-oriented programming (JOP)][JOP] and [call-oriented programming (COP)][COP] respectively. 

This research project explores an instruction-scheduling approach to reduce the attack surface of these techniques by reducing the number of usable gadgets an attacker has access to and by making the remaining gadgets more difficult to leverage. We chose to implement this in LLVM due to its widespread usage and the Rust compiler to benchmark the results because Rust has a standardized toolchain unlike C++ or C.

## Setup
1. To run RopSched, first clone the repository and the required submodules.

```bash
git clone --recurse-submodules https://github.com/PeanutButterRat/ropsched.git
```

2. Next, run the `setup` script. This will compile LLVM and the Rust compiler.

```bash
cd ropsched && ./setup
```

3. Finally, set up a virtual environment (venv) and install the required Python packages.

```bash
python -m venv .venv             # Create the virtual environment.
source .venv/bin/activate        # Activate the virtual environment.
pip install -r requirements.txt  # Install the required packages.
```

> If you don't have the `venv` package already installed, you can do so with `sudo apt install python3-venv`.

You should now be ready to run the tests!

## Usage
To run any benchmarks, use the `benchmark` script.
```
(.venv) ebrown@ERIC-DESKTOP-UBUNTU:~/RopSched$ ./benchmark -h
usage: benchmark [-h] [-b BENCHMARKS] [-c CONFIGS] [-f FLAGS] [-d] [-t TIMEOUT] [--show-times] [--skip-compilation] [-s SHEET_NAME] [-o OUTPUT] [-a ARCHITECTURE] [--benchmark-directory BENCHMARK_DIRECTORY]

Benchmark LLVM scheduler configurations with GadgetSetAnalyzer.

options:
  -h, --help            show this help message and exit
  -b BENCHMARKS, --benchmarks BENCHMARKS
                        Benchmarks to run (comma-separated list)
  -c CONFIGS, --configs CONFIGS
                        Scheduling configs to run (comma-separated list: [pre-ra, post-ra, both])
  -f FLAGS, --flags FLAGS
                        Extra LLVM flags to use when compiling benchmarks
  -d, --debug           Show command output
  -t TIMEOUT, --timeout TIMEOUT
                        Timeout in seconds for a single command invocation
  --show-times          Display the time it takes for each benchmark to complete
  --skip-compilation    Skip the compilation and analysis steps, just combine the CSV files from a previous run
  -s SHEET_NAME, --sheet-name SHEET_NAME
                        The name of the sheet
  -o OUTPUT, --output OUTPUT
                        The name of the workbook to output
  -a ARCHITECTURE, --architecture ARCHITECTURE
                        The architecture to compile for (x86-64 or aarch64)
  --benchmark-directory BENCHMARK_DIRECTORY
                        Directory where the benchmark repositories are
```

As shown above, there are various options to change the way the benchmarks are run. Most of them are to help with generating results files or to weed out good projects to benchmark. The most useful flags would be the following:

- `--benchmarks`: Select which benchmarks are run. These should be folder names found within the `--benchmark-directory`.

```bash
./benchmark -b "project1,project2,project3"
```

- `--configs`: Select which configs are run. These are combinations of the pre-RA machine scheduler and post-RA machine scheduler. `both` means to run the pre-RA scheduler and post-RA scheduler in the same run whereas `pre-ra` and `post-ra` will run each the RopSched scheduler for either the pre-RA scheduling stage or the post-RA scheduling stage respectively. When not running RopSched, the `default` LLVM scheduling strategy will be used for that givent stage.

```bash
./benchmark -c "post-ra,both"
```

- `--flags`: Send specific flags to the LLVM pipeline. This can be used to enable debugging output when LLVM runs. This will ultimately be passed to the Rust compiler through `-C llvm-args={flag}` for each space-separated flag you specify.

```bash
./benchmark -f="-debug-only=ropsched"  # Use the option=value form so Python doesn't think these are flags to be passed to the benchmark script itself.
```

