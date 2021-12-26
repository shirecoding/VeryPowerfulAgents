import queue
from datetime import datetime, timedelta
from queue import Queue
from threading import Thread
from traceback import format_exc

import rx


class DaemonMixin:
    pidgeon_hole = {}

    # clean up every hour
    rx.interval(60 * 60).subscribe(lambda x: self.clean_up_pidgeon_hole())

    def clean_up_pidgeon_hole(self):
        self.pidgeon_hole = {
            key: value
            for key, value in self.pidgeon_hole.items
            if datetime.now() > value["expired_at"]
        }

    def create_daemon(self, queue, func):
        t = Thread(
            target=self.run,
            args=(
                queue,
                func,
            ),
        )
        t.daemon = True
        t.start()

    def create_pidgeon_hole(self, pidgeon_uid):
        current_time = datetime.now()
        self.pidgeon_hole[pidgeon_uid] = {
            "queue": Queue(),
            "created_at": current_time,
            "expired_at": current_time + timedelta(hours=1),
        }

    def put_pidgeon(self, pidgeon_uid, result):
        if pidgeon_uid not in self.pidgeon_hole:
            self.create_pidgeon_hole(pidgeon_uid)

        self.pidgeon_hole[pidgeon_uid]["queue"].put(result)

    def get_pidgeon(self, pidgeon_uid, timeout=60):
        if pidgeon_uid not in self.pidgeon_hole:
            self.create_pidgeon_hole(pidgeon_uid)

        try:
            return self.pidgeon_hole[pidgeon_uid]["queue"].get(timeout=timeout)
        except queue.Empty:
            self.log.error("[puid={}] Timeout for get_pidgeon".format(pidgeon_uid))

        return None

    def run(self, queue, func):
        while True:
            try:
                args, kwargs = queue.get()
                pidgeon_uid = kwargs.pop("pidgeon_uid")

                result = func(*args, **kwargs)
                if pidgeon_uid:
                    self.put_pidgeon(pidgeon_uid, result)
            except Exception as e:
                self.log.error("{}\n\n{}".format(e, format_exc()))
