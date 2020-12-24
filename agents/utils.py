import sys
import logging

# logging
def stdout_logger(name, level=logging.DEBUG):
    log = logging.getLogger(name)
    log.propagate = False
    stream_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(levelname)-8s %(message)s')
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(level)
    log.handlers = [ stream_handler ]
    log.setLevel(level)
    return log

class Logger(logging.LoggerAdapter):

    def process(self, msg, kwargs):
        return '[{}] {}'.format(' '.join([ '{}={}'.format(k, v) for k, v in { **kwargs, **self.extra}.items() ]), msg), kwargs