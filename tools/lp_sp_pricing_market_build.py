"""Build the dependency-free exact CPU market worker inside a CPU reservation."""
from pathlib import Path
import subprocess
from lp_sp_pricing_budget import ROOT


if __name__ == "__main__":
    directory = ROOT/"research/lp-sp-pricing/target/cpu"
    directory.mkdir(parents=True, exist_ok=True)
    subprocess.run(["g++", "-std=c++17", "-O3", "-fPIC", "-shared", "-Wall", "-Wextra", "-Werror",
        str(ROOT/"research/lp-sp-pricing/native/market.cpp"), "-o", str(directory/"libsp_market.so")], check=True)
