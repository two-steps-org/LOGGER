"""Tests for twosteps_logger.constants."""
import pytest
from twosteps_logger.constants import StatusType


def test_status_type_values():
    assert StatusType.SUCCESS.value == "SUCCESS"
    assert StatusType.FAILURE.value == "FAILURE"
    assert StatusType.PENDING.value == "PENDING"
    assert StatusType.ERROR.value == "ERROR"


def test_status_type_is_str():
    """StatusType inherits str so it compares equal to plain strings."""
    assert StatusType.SUCCESS == "SUCCESS"
    assert StatusType.FAILURE == "FAILURE"


def test_status_type_members():
    members = {m.value for m in StatusType}
    assert members == {"SUCCESS", "FAILURE", "PENDING", "ERROR"}


def test_status_type_exported_from_package():
    from twosteps_logger import StatusType as ST
    assert ST is StatusType
