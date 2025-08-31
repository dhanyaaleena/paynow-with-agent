import logging
import contextvars

# Async-safe context variable to hold the current request ID
request_id_var = contextvars.ContextVar("request_id", default=None)


class RequestIdFilter(logging.Filter):
    """Injects request_id from contextvars into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get() or "-"
        return True


def configure_logging(level: int = logging.INFO) -> None:
    """Configure logging with requestId support for all log records.

    - Sets a LogRecord factory to always include request_id.
    - Configures a root StreamHandler with formatter including request_id.
    - Adds a RequestIdFilter to the handler for extra safety.
    """
    # Ensure every LogRecord has request_id set
    original_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = original_factory(*args, **kwargs)
        # Inject request_id attribute for all records
        if not hasattr(record, "request_id"):
            record.request_id = request_id_var.get() or "-"
        return record

    logging.setLogRecordFactory(record_factory)

    # Configure handlers/formatters
    logging.basicConfig(
        level=level,
        format='%(asctime)s %(levelname)s [requestId=%(request_id)s] %(name)s: %(message)s'
    )

    # Attach filter to all existing handlers
    root_logger = logging.getLogger()
    req_filter = RequestIdFilter()
    for handler in root_logger.handlers:
        # Avoid duplicate filters
        if not any(isinstance(f, RequestIdFilter) for f in handler.filters):
            handler.addFilter(req_filter)


