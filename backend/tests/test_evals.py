"""The placeholders in a golden case's checks: filled from the database, so they don't go stale."""

import pytest

import re

from supportpilot import config, evals
from supportpilot.orders import connect, get_order

ADA = 1

CASE = {
    "customer_id": ADA,
    "order_id": 1234,
    "must_include": ["{days_over_window} days"],
    "must_not_include": ["{days_since_delivery} days past"],
}


@pytest.fixture
def days():
    with connect():  # skips cleanly with the others if Postgres isn't up
        pass
    return get_order(1234, ADA).days_since_delivery


def test_the_confusion_this_case_exists_for_fails_the_check(days):
    # Delivered `days` ago and the window is 30: the answer that blames the whole age on the window is wrong.
    wrong = f"The window is 30 days; you are {days} days past the return window."
    assert evals.check_answer(wrong, CASE) is False


def test_the_right_number_passes_the_check(days):
    right = f"It was delivered {days} days ago, so you are {days - config.RETURN_WINDOW_DAYS} days past the window."
    assert evals.check_answer(right, CASE) is True


def test_cases_without_an_order_do_not_touch_the_database():
    case = {"must_include": ["30 days"], "must_not_include": []}
    assert evals.check_answer("You have 30 days.", case) is True


def test_the_return_window_in_the_code_matches_the_policy():
    text = (config.POLICIES_DIR / "returns.md").read_text()
    window = re.search(r"within (\d+) days of the delivery date", text)
    assert window and int(window.group(1)) == config.RETURN_WINDOW_DAYS


def test_get_order_hands_over_the_subtraction(days):
    order = get_order(1234, ADA)
    assert order.return_window_days_left == config.RETURN_WINDOW_DAYS - days
