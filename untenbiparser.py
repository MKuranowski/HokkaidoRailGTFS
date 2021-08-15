import parsec
import sys

# Whole string can start with (土曜・休日|全日運転)(と|。)
#
# Terminology:
#
#   RULE
# ┌─┴────────────────────────────────────┐
# 3月19日～4月10・13～17・20～24・27・28日運転
# └───────┬───┘└─┬────┘└─┬───┘└─┬┘└┬┘└──┬┘
#   ┌─────┴──────┴───────┘      ├──┘    │
# RANGE                 SINGLE_DAY RULE_TYPE
#  └─┬────────────────────┘
#  DATE

max_days_in_month = {
    1: 31, 2: 29, 3: 31, 4: 30, 5: 31, 6: 30,
    7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31,
}


def day_plus_one(day):
    if (day[1] + 1) > max_days_in_month[day[0]]:
        return ((day[0] + 1) % 12, 1)
    else:
        return (day[0], day[1] + 1)


def day_minus_one(day):
    m, d = day
    d -= 1

    if d <= 0:
        m -= 1
        if m <= 0:
            m = 12
        return (m, max_days_in_month[m])
    else:
        return (m, d)


# === DAYS AND RANGES === #

number = parsec.regex(r"[０-９0-9]{1,2}")
month_def = (number << parsec.string("月")) ^ parsec.string("")
day_def = number << parsec.regex(r"日?")

@parsec.generate
def range_def():
    start_month = yield month_def
    start_day = yield day_def

    yield parsec.string("～")

    end_month = yield month_def
    end_day = yield day_def

    start_month = int(start_month) if start_month else None
    start_day = int(start_day)

    end_month = int(end_month) if end_month else None
    end_day = int(end_day)

    return {
        "type": "range",
        "start": (start_month, start_day),
        "end": (end_month, end_day)
    }

@parsec.generate
def single_day_def():
    month = yield month_def
    day = yield day_def

    month = int(month) if month else None
    day = int(day)

    return {
        "type": "single",
        "day": (month, day)
    }

date = range_def ^ single_day_def
multiple_dates = parsec.sepBy1(date, parsec.string("・"))

# Converts whatever multiple_days parsed into a list of days
# Also keeps track of the month and appends it to each day.
def flatten_multiple_dates(multi_days):
    month = None
    flat_dates = []

    for date in multi_days:

        if date["type"] == "single":
            if date["day"][0] is None:
                if month is None:
                    raise ValueError("first part of date definition should include month number")
                else:
                    flat_dates.append((month, date["day"][1]))
            else:
                month = date["day"][0]
                flat_dates.append(date["day"])

        elif date["type"] == "range":
            start = date["start"]

            if start[0] is None:
                if month is None:
                    raise ValueError("first part of date definition should include month number")
                else:
                    start = (month, start[1])
            else:
                month = start[0]

            end = date["end"]

            if end[0] is None:
                if month is None:
                    raise ValueError("first part of date definition should include month number")
                else:
                    end = (month, end[1])
            else:
                month = end[0]

            # Iterate over each day in given range
            current_day = start
            while current_day <= end:
                flat_dates.append(current_day)

                current_day = day_plus_one(current_day)

    return flat_dates

# === RULES === #

rule_type_translations = {
    "から運転": "start_date",
    "からは運転": "start_date",
    "からは運休": "end_date_minus1",
    "まで運転": "end_date",
    "までは運転": "end_date",
    "まで運休": "start_date_plus1",
    "までは運休": "start_date_plus1",
    "運転": "added",
    "運休": "removed",
}

# Rules which are only applicable to one day

@parsec.generate
def single_day_rule():
    date = yield single_day_def
    rule_type = yield (parsec.string("から運転")
                       ^ parsec.string("からは運転")
                       ^ parsec.string("からは運休")
                       ^ parsec.string("まで運転")
                       ^ parsec.string("までは運転")
                       ^ parsec.string("まで運休")
                       ^ parsec.string("までは運休"))

    if date["day"][0] is None:
        raise ValueError("month definition is required in から運転・まで運転 rules")

    return {
        "day": date["day"],
        "rule": rule_type_translations[rule_type]
    }

# Rules which can apply to any combination of days

particle = parsec.regex(r"は?")
possible_types = parsec.string("運転") ^ parsec.string("運休")
rule_type_def = particle >> possible_types

@parsec.generate
def multi_day_rule():
    dates = yield multiple_dates
    rule_type = yield rule_type_def
    return {
        "days": flatten_multiple_dates(dates),
        "rule": rule_type_translations[rule_type]
    }

# All rules
rule = single_day_rule ^ multi_day_rule
all_rules = parsec.sepEndBy1(rule, parsec.one_of("、。"))

# === COMBINE EVERYTHING === #
pattern_suffix = parsec.one_of("と。")
pattern_name = parsec.string("全日運転") ^ parsec.string("土曜・休日")
pattern_def = pattern_name << pattern_suffix

pattern_translate = {
    "全日運転": "毎日",
    "土曜・休日": "土曜・休日",
}

@parsec.generate
def parse_untenbi():
    raw_pattern = yield (pattern_def ^ parsec.string(""))
    raw_rules = yield all_rules

    result = {}

    if raw_pattern:
        result["pattern"] = pattern_translate[raw_pattern]

    # Interpret each rule
    for raw_rule in raw_rules:

        if raw_rule["rule"] in {"start_date", "start_date_plus1"}:
            if raw_rule["rule"] == "start_date_plus1":
                result["start"] = day_plus_one(raw_rule["day"])
            else:
                result["start"] = raw_rule["day"]

            if "end" not in result:
                result["end"] = (12, 31)

            if "pattern" not in result:
                result["pattern"] = "毎日"

        elif raw_rule["rule"] in {"end_date", "end_date_minus1"}:
            if raw_rule["rule"] == "end_date_minus1":
                result["end"] = day_minus_one(raw_rule["day"])
            else:
                result["end"] = raw_rule["day"]

            if "start" not in result:
                result["start"] = (1, 1)

            if "pattern" not in result:
                result["pattern"] = "毎日"

        else:

            if "pattern" not in result:
                result["pattern"] = "全休" if raw_rule["rule"] == "added" else "毎日"

            if raw_rule["rule"] not in result:
                result[raw_rule["rule"]] = set()

            result[raw_rule["rule"]].update(raw_rule["days"])

    # Nullyfing exceptions
    if "added" in result and "removed" in result:
        if result["pattern"] == "毎日":
            result["removed"].difference_update(result["added"])
            del result["added"]

        elif result["pattern"] == "全休":
            result["added"].difference_update(result["removed"])
            del result["removed"]

    return result

if __name__ == "__main__":
    from pprint import pprint

    if len(sys.argv) >= 2:
        txt = sys.argv[1]
    else:
        txt = input("> ")

    pprint(parse_untenbi.parse(txt))
