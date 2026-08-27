import logging


def setup_logging(debug: bool = False) -> None:
    """Initialize application-wide logging."""
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        # format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
