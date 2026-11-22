"""Run only R226-owned jobs; cancellation never terminates shared analysis work."""
from __future__ import annotations

import threading


class RoughcutJobs:
    def __init__(self, runner, *, autostart=True):
        self.runner = runner
        self.autostart = autostart
        self.events = {}
        self.threads = {}
        self.running = set()
        self.lock = threading.RLock()
        self.closed = False

    def submit(self, job_id):
        with self.lock:
            event = self.events.setdefault(job_id, threading.Event())
            if self.closed:
                event.set()
                return
            if self.autostart:
                thread = threading.Thread(target=self.run, args=(job_id,), name='roughcut-' + job_id, daemon=True)
                self.threads[job_id] = thread
                thread.start()

    def run(self, job_id):
        with self.lock:
            if job_id in self.running:
                return
            event = self.events.setdefault(job_id, threading.Event())
            if self.closed:
                event.set()
            self.running.add(job_id)
        try:
            self.runner(job_id, event)
        finally:
            with self.lock:
                self.running.discard(job_id)

    def cancel(self, job_id):
        with self.lock:
            self.events.setdefault(job_id, threading.Event()).set()

    def close(self):
        with self.lock:
            self.closed = True
            for event in self.events.values():
                event.set()
            threads = list(self.threads.values())
        for thread in threads:
            if thread is not threading.current_thread():
                thread.join(timeout=2)
