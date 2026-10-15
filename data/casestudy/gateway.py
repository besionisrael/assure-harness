"""Module `gateway`, importable by every program and test of the case study."""


class GatewayTimeout(Exception):
    """The gateway did not answer in time; the charge may or may not have happened."""
