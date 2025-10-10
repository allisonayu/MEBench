# Multilingual Ethics Benchmark
insert links to paper + huggingface dataset

## Overview
sldkfsdkf

## Usage
### Virtual Environment Set-Up
Many LLM packages require modern versions of its dependencies, such as httpx. Specifically, it requires a version of httpx that is too new for the googletrans library. The googletrans package is an unmaintained library that relies on old versions of httpx and httpcore. Because these two packages have conflicting version requirements for the same underlying dependencies, they cannot be installed in the same Python environment without one of them breaking.

To solve this, we need to create two separate, isolated virtual environments:

**main_env**: contains all the modern packages the evaluation script needs
**trans_env**: dedicated to googletrans library and its old dependencies

The evaluation script, running in main_env, uses the subprocess module to call the translate_worker.py script. This worker script is run using the Python interpreter from the trans_env, which had googletrans installed. This isolation method bypasses the dependency conflict, which allows both sets of packages to be used. (**CHANGE LATER**)

### Steps:
Main environment terminal commands:
1. Create main environment (main_env): py -3.9 -m venv main_env
2. Activate the environment:
   Windows: main_env\Scripts\activate
   macOS/Linux: source main_env/bin/activate
5. Install necessary packages:
   pip install anthropic pandas requests (**CHANGE ALL THIS LATER**)
   pip install openai (for gpt)

Translation environment terminal commands:
1. Create translation environment (trans_env): py -3.9 -m venv trans_env
2. Activate the environment:
   Windows: trans_env\Scripts\activate
   macOS/Linux: source trans_env/bin/activate
5. Install necessary packages: pip install googletrans==4.0.0-rc1

To run:
1. Make sure you are on the main_env (if not, deactivate any currently running environments and activate main_env)
2. Run the main script: python claudeEvals.py (or whatever we name the main file **ALSO CHANGE THIS LATER**)

## Citation
asldkfjskf
