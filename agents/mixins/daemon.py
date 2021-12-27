import queue
from datetime import datetime, timedelta
from queue import Queue
from threading import Thread
from traceback import format_exc
from collections import defaultdict
import rx


class DaemonMixin:
    
    def setup(self, *args, **kwargs):
        self.pidgeon_hole = defaultdict(dict)

    def clean_up_pidgeon_hole(self):
        for uid in self.pidgeon_hole:
            if datetime.now() > self.pidgeon_hole[uid]["expired_at"]:
                del self.pidgeon_hole[uid]

    def create_daemon(self, queue, func):
        t = Thread(
            target=self.run,
            args=(queue, func),
        )
        self.threads.append(t)
        t.start()

    def create_pidgeon_hole(self, pidgeon_uid):
        current_time = datetime.now()
        self.pidgeon_hole[pidgeon_uid] = {
            "queue": Queue(),
            "created_at": current_time,
            "expired_at": current_time + timedelta(hours=1),
        }
        # clean up pidgeon holes
        self.clean_up_pidgeon_hole()

    def put_pidgeon(self, pidgeon_uid, result):
        if pidgeon_uid not in self.pidgeon_hole:
            self.create_pidgeon_hole(pidgeon_uid)
        try:
            self.pidgeon_hole[pidgeon_uid]["queue"].put(result, timeout=1)
        except Exception as e:
            self.log.exception(e)  # queue might be full, no remedy, but just log it for now

    def get_pidgeon(self, pidgeon_uid, timeout=60):
        if pidgeon_uid not in self.pidgeon_hole:
            self.create_pidgeon_hole(pidgeon_uid)
        try:
            return self.pidgeon_hole[pidgeon_uid]["queue"].get(timeout=timeout)
        except queue.Empty:
            self.log.error(f"[puid={pidgeon_uid}] Timeout for get_pidgeon")

        return None

    def run(self, q, func):
        while not self.exit_event.is_set():
            try:
                args, kwargs = q.get(timeout=1)
                pidgeon_uid = kwargs.pop("pidgeon_uid")
                result = func(*args, **kwargs)
                if pidgeon_uid:
                    self.put_pidgeon(pidgeon_uid, result)
            
            except queue.Empty:
                pass
            
            except Exception as e:
                self.log.exception(e)
