import logging, sys, structlog

def configure_logging():
    logging.basicConfig(
        format="%(message)s", stream=sys.stdout,
        level=getattr(logging, "INFO")
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    )

logger = structlog.get_logger()
