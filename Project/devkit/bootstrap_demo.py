"""Make a bare checkout runnable outside the capstone environment.

Only fills in what is missing, so it never overwrites the capstone's pre-loaded
config.py, data, documents, .env or Streamlit theme.

    python devkit/bootstrap_demo.py           # add whatever is missing
    python devkit/bootstrap_demo.py --all     # ... then run steps 1 to 4
    python devkit/bootstrap_demo.py --small   # quarter-size demo data (faster)
"""
import argparse
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)


def copy_if_missing(source, target, label):
    if os.path.exists(target):
        print(f"kept      {label} (already present)")
        return
    os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
    shutil.copyfile(source, target)
    print(f"added     {label}")


def run(command):
    print(f"\n$ {' '.join(command)}")
    subprocess.run(command, cwd=PROJECT, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="also run steps 1 to 4")
    parser.add_argument("--small", action="store_true", help="quarter-size demo data")
    arguments = parser.parse_args()
    os.chdir(PROJECT)
    copy_if_missing(os.path.join(HERE, "reference_config.py"), os.path.join("config", "config.py"), "config/config.py")
    if not os.path.exists(os.path.join("config", "__init__.py")):
        open(os.path.join("config", "__init__.py"), "w").close()
    copy_if_missing(os.path.join(HERE, "streamlit_config.toml"), os.path.join(".streamlit", "config.toml"),
                    ".streamlit/config.toml")
    copy_if_missing(".env.example", ".env", ".env (fill in GEMINI_API_KEY, or set FAIRPAY_OFFLINE_LLM=1)")
    run([sys.executable, os.path.join("devkit", "make_demo_docs.py")])
    run([sys.executable, os.path.join("devkit", "make_demo_data.py")] + (["--small"] if arguments.small else []))
    if arguments.all:
        for step in ["run_database_setup.py", "run_data_pipeline.py", "run_model_training.py", "run_knowledge_indexing.py"]:
            run([sys.executable, step])
        print("\nReady. Start the service with  python run_api_service.py  and the dashboard with  "
              "streamlit run run_dashboard.py")


if __name__ == "__main__":
    main()
