from datetime import datetime, timedelta


def split(time_range):
    """
    Splits a query time range into two.
    For given input '000000-235959' will be split to
    '000000-115959' and '120000-235959'
    :param time_range: start and end time, e.g. '000000-235959'
    :return: two time ranges, e.g. '000000-115959' and '120000-235959'
    """
    start, end = time_range.split("-")
    start_value = datetime.strptime(start, "%H%M%S")
    end_value = datetime.strptime(end, "%H%M%S")

    delta_start = timedelta(
        hours=start_value.hour, minutes=start_value.minute, seconds=start_value.second
    )

    delta_end = timedelta(
        hours=end_value.hour, minutes=end_value.minute, seconds=end_value.second + 1
    )

    middle = abs(delta_end.total_seconds() - delta_start.total_seconds()) / 2
    i_right = _format_time(delta_start + timedelta(seconds=middle - 1))
    i_left = _format_time(delta_start + timedelta(seconds=middle))
    left = start + "-" + i_right
    right = i_left + "-" + _format_time(delta_end - timedelta(seconds=1))
    return left, right


def _prefix_zero(value):
    v = str(value)
    if len(v) == 1:
        v = "0" + v
    return v


def _format_time(time_delta):
    hours, remainder = divmod(time_delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return _prefix_zero(hours) + _prefix_zero(minutes) + _prefix_zero(seconds)
