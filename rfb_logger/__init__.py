import logging
import logging.handlers
import os
from ..rfb_utils.prefs_utils import get_pref

LOGGING_DISABLED = 100
CRITICAL = logging.CRITICAL
ERROR    = logging.ERROR
WARNING  = logging.WARNING
INFO     = logging.INFO
VERBOSE  = 15
DEBUG    = logging.DEBUG
NOTSET   = logging.NOTSET

LOG_LEVELS = { 'CRITICAL': logging.CRITICAL,
               'ERROR': logging.ERROR,
               'WARNING': WARNING,
               'INFO': logging.INFO,
               'VERBOSE': 15,
               'DEBUG': logging.DEBUG,
               'NOTSET':  logging.NOTSET}

RFB_LOG_FILE = ''
RFB_LOG_FILE_HANDLER = None

RFB_CONSOLE_HANDLER = None
RFB_LOG_LEVEL = None

# logger format
LOG_FMT = '[%(levelname)s] (%(threadName)-10s) %(name)s %(funcName)s: %(message)s'

def set_logger_level(level):
    """
    Set the logging level for this module. This is only useful if the module
    is not using another logger.
    """
    global RFB_LOG_LEVEL
    if level == logging.NOTSET:
        RFB_LOG_LEVEL = None
    elif level != RFB_LOG_LEVEL:
        RFB_LOG_LEVEL = level

    __log__.setLevel(level)

def logger_level():
    """Return the logger's current level"""
    return __log__.level

def set_logger(logger):
    """
    Make this module adopt another logger and coalesce outputs into one stream.
    """
    global __log__
    __log__ = logger

def init_log_level():
    global LOG_LEVELS
    global RFB_LOG_LEVEL

    if 'RFB_LOG_LEVEL' in os.environ:
        RFB_LOG_LEVEL = os.environ['RFB_LOG_LEVEL']
        level = WARNING
        if RFB_LOG_LEVEL not in LOG_LEVELS:
            __log__.error("Invalid Log Level: %s" % str(RFB_LOG_LEVEL))
        else:
            level = LOG_LEVELS.get(RFB_LOG_LEVEL, WARNING)
        set_logger_level(level)

    __log__.debug('logger initialized')
    __log__.debug('   |_ logger: %d', logger_level())

def set_file_logger(logFile):
    global RFB_LOG_FILE
    global RFB_LOG_FILE_HANDLER
    global __log__

    err_msg = []
    if not os.path.exists(os.path.dirname(logFile)):
        # make sure the directories exist.
        try:
            os.makedirs(os.path.dirname(logFile))
        except (IOError, OSError) as err:
            err_msg.append('Could not create log directory in %s : %s' %
                        (logFile, err))
        if not os.access(logFile, os.W_OK | os.R_OK):
            err_msg.append('Log file is not writable %s' % (logFile))
            return

    if logFile:
        # generate up to 5 logs of 10MB each.
        RFB_LOG_FILE_HANDLER = logging.handlers.RotatingFileHandler(logFile,
                                                    maxBytes=10485760,
                                                    backupCount=5)
        RFB_LOG_FILE_HANDLER.setLevel(DEBUG)
        # we use a different format for the disk log, to get a time stamp.
        fmtf = logging.Formatter('%(asctime)s %(levelname)8s {%(threadName)-10s}'
                                    ':  %(module)s %(funcName)s: %(message)s')
        RFB_LOG_FILE_HANDLER.setFormatter(fmtf)
        __log__.addHandler(RFB_LOG_FILE_HANDLER)    
        RFB_LOG_FILE = logFile   

def check_log_level_preferences(): 
    global RFB_LOG_LEVEL
    if RFB_LOG_LEVEL:
        return

    level = get_pref('rman_logging_level', WARNING)
    if level in LOG_LEVELS:        
        set_logger_level(level)
    else:
        set_logger_level(WARNING)       

def check_logfile_preferences():
    global RFB_LOG_FILE
    global RFB_LOG_FILE_HANDLER
    global __log__

    if RFB_LOG_FILE:
        return

    logFile = ''
    err_msg = []
    logFile = get_pref('rman_logging_file', '')

    if logFile:
        set_file_logger(logFile)

def rfb_log():
    """
    Return the logger.
    """

    # These are necessary because for some reason getting the preferences
    # in get_logger() seems to always fail
    if not RFB_LOG_FILE:
        check_logfile_preferences()
    if not RFB_LOG_LEVEL:        
        check_log_level_preferences()

    return __log__


def get_logger(name):
    """
    Create a new configured logger and returns it.
    """
    log = logging.getLogger(name)
    # we don't set the logger's level to inherit from the parent logger.
    if log.handlers:
        return log
    fmt = logging.Formatter(LOG_FMT)
    shdlr = logging.StreamHandler()
    shdlr.setFormatter(fmt)
    log.addHandler(shdlr)

    if 'RFB_LOG_FILE' in os.environ:
        logFile = os.environ['RFB_LOG_FILE']    
        set_file_logger(logFile)

    log.propagate = False

    return log

__log__ = get_logger(__name__)
init_log_level()