import os, subprocess, sys
os.environ.setdefault("PYTHONPATH", ".")
subprocess.run([sys.executable, "-m", "app.database.seed"], check=True)
subprocess.run([sys.executable, "-m", "app.rag.ingestion"], check=True)
subprocess.run([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"])
