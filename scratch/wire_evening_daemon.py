import sys

content = open('Actress_Modules/actress_scheduler.py', 'r', encoding='utf-8', errors='replace').read()

old = '    # Start the peak-time publisher in parallel\n    start_publish_scheduler()\n'
new = '''    # Start the peak-time publisher in parallel
    start_publish_scheduler()

    # Start dedicated 6 PM evening pipeline in its own daemon thread
    def _run_evening_safe():
        try:
            run_evening_pipeline()
        except Exception as _ep_err:
            logger.error("[EVENING] Pipeline crashed (non-fatal): %s", _ep_err)

    def _evening_daemon():
        import schedule as _sched
        _sched.every().day.at("12:30").do(_run_evening_safe)  # 6:00 PM IST
        while True:
            _sched.run_pending()
            time.sleep(30)

    _ev_thread = threading.Thread(target=_evening_daemon, daemon=True, name="EveningPipeline")
    _ev_thread.start()
    logger.info("[EVENING] Evening Pipeline daemon started -- fires at 6 PM IST daily")

'''

if old not in content:
    print("ERROR: old block not found")
    sys.exit(1)

new_content = content.replace(old, new, 1)
with open('Actress_Modules/actress_scheduler.py', 'w', encoding='utf-8') as f:
    f.write(new_content)
print("OK: wired evening daemon into start_scheduler")
