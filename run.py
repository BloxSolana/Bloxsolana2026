# run.py
from Automatic import app, start_scheduler

if __name__ == "__main__":
    start_scheduler()
    app.run(host="127.0.0.1", port=5000, threaded=True, use_reloader=False)
  
