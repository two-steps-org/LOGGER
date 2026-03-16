from enum import Enum


class StatusType(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    PENDING = "PENDING"
    ERROR = "ERROR"

