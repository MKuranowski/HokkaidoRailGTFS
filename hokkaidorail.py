import xml.etree.ElementTree as etree
from datetime import date, datetime, timedelta
from collections import OrderedDict
from bs4 import BeautifulSoup
from itertools import chain
from warnings import warn
import requests
import zipfile
import pytz
import yaml
import csv
import os
import io
import re

from untenbiparser import parse_untenbi

OUTPUT_SERVICE_DESC = False
DEFAULT_AGENCY = "4430001022657"
STR_1UP = "\033[1A\033[K"

# HELPING FUNCTIONS #

def get_text_color(color):
    """Given a color, estimate if it's better to
    show block or white text on top of it.
    """

    r = int(color[0:2], base=16)
    g = int(color[2:4], base=16)
    b = int(color[4:6], base=16)
    yiq = 0.299 * r + 0.587 * g + 0.114 * b

    return "000000" if yiq > 128 else "FFFFFF"

def load_holidays(start, end):
    """Loads Japan holidays into self.holidays.
    Data comes from Japan's Cabinet Office:
    https://www8.cao.go.jp/chosei/shukujitsu/gaiyou.html

    Only holdays within start and end are saved.
    """
    holidays = set()

    try:
        req = requests.get("https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv")
        req.raise_for_status()
    except requests.exceptions.SSLError:
        print("! Connection to cao.go.jp raised an SSL Error")
        print("! Fetching a copy of holidays CSV file from mkuran.pl", end="\n\n")
        req = requests.get("https://mkuran.pl/moovit/japan-cao-shukujitsu.csv")
        req.raise_for_status()

    req.encoding = "shift-jis"
    buffer = io.StringIO(req.text)
    reader = csv.DictReader(buffer)

    for row in reader:
        date_str = row["国民の祝日・休日月日"]
        date_val = datetime.strptime(date_str, "%Y/%m/%d").date()

        if start <= date_val <= end:
            holidays.add(date_val)

    buffer.close()
    return holidays

def has_station(train, look_for_station):
    """Check if this `train` stops at the given station (by the station name).
    Returns the index of this station within train["stations"], or
    if the train does not stop returns -1.
    """
    for idx, stoptime in enumerate(train["stations"]):
        if stoptime["sta"] == look_for_station:
            return idx
    return -1

def split_train(train, split_station, a_stations, b_stations):
    """Splits the train into 2 parts.

    `split_station` should be the station name where the split should occur.

    `a_stations` & `b_stations` should be a collection of station names
    that identify a train part as belonging to route A or B.

    returns a tuple of part_a, part_b; after splitting the train.
    part_a & part_b can be None.
    """
    idx_of_split = has_station(train, split_station)

    # if split doesn't exist or train starts at or finishes at split:
    if idx_of_split == -1 or idx_of_split == 0 or idx_of_split == len(train["stations"]) - 1:
        if any((has_station(train, i) != -1 for i in a_stations)):
            return train, None
        elif any((has_station(train, i) != -1 for i in b_stations)):
            return None, train
        elif train["trip_name"] == "エアポート" and len(train["stations"]) == 1 \
                and train["stations"][0]["sta"] == "札幌":
            # Airport Express stubs left out on Hakodate line timetables
            return None, None
        else:
            raise ValueError(f"train no {train['trip_number']} in should stop at one of: "
                             f"{split_station} {a_stations} {b_stations}. "
                             "It's impossible to split this train into correct routes.")

    # otherwise we try to split the train
    else:
        part_1 = train.copy()
        part_1["stations"] = train["stations"][:idx_of_split + 1]
        part_1["stations"][-1]["dep"] = part_1["stations"][-1]["arr"]

        part_2 = train.copy()
        part_2["stations"] = train["stations"][idx_of_split:]
        part_2["stations"][0]["arr"] = part_2["stations"][0]["dep"]

        # part 1 contains any "a" stations → part_1=part_a, part_2=part_b
        if any((has_station(part_1, i) != -1 for i in a_stations)):
            return part_1, part_2

        # part 1 contains any "b" stations → part_2=part_a, part_1=part_b
        elif any((has_station(part_1, i) != -1 for i in b_stations)):
            return part_2, part_1

        # part 2 contains any "a" stations → part_2=part_a, part_1=part_b
        elif any((has_station(part_2, i) != -1 for i in a_stations)):
            return part_2, part_1

        # part 2 contains any "b" stations → part_1=part_a, part_2=part_b
        elif any((has_station(part_2, i) != -1 for i in b_stations)):
            return part_1, part_2

        else:
            raise ValueError(f"train no {train['trip_number']} in should stop at one of: "
                             f"{split_station} {a_stations} {b_stations}. "
                             "It's impossible to split this train into correct routes.")

class Time:
    """An object representing a GTFS time value.

    :param seconds: The amount of seconds since midnight.
    :type secnonds: int
    """
    def __init__(self, seconds):
        self.m, self.s = divmod(int(seconds), 60)
        self.h, self.m = divmod(self.m, 60)

    def __str__(self):
        """Return GTFS-compliant string representation of time
        """
        return f"{self.h:0>2}:{self.m:0>2}:{self.s:0>2}"

    def __repr__(self): return "<Time " + self.__str__() + ">"
    def __int__(self): return self.h * 3600 + self.m * 60 + self.s
    def __hash__(self): return hash(self.__int__())
    def __add__(self, other): return Time(self.__int__() + int(other))
    def __sub__(self, other): return Time(self.__int__() - int(other))
    def __lt__(self, other): return self.__int__() < int(other)
    def __le__(self, other): return self.__int__() <= int(other)
    def __gt__(self, other): return self.__int__() > int(other)
    def __ge__(self, other): return self.__int__() >= int(other)
    def __eq__(self, other): return self.__int__() == int(other)
    def __ne__(self, other): return self.__int__() != int(other)

    @classmethod
    def from_str(cls, string):
        value = re.sub(r"\D", "", string)

        if len(value) == 3:
            return cls(int(value[0]) * 3600 + int(value[1:]) * 60)

        elif len(value) == 4:
            return cls(int(value[:2]) * 3600 + int(value[2:]) * 60)

        else:
            raise ValueError(f"invalid string for Time.from_str(), {value} "
                             f"(should be HHMM or HMM) (passed: {string})")

class HokkaidoRailGTFS:
    def __init__(self):
        # Relations between trains
        self.blocks = {}
        self.services = {"毎日": 0}
        self.trip_enumerator = 0

        # Route data (data/routes.yaml)
        self.routes = {}
        self.expresses = {}

        # Calendar data
        self.calendar_data = {}

        # Shape generation (todo)
        self.train_shaper = None
        self.bus_shaper = None

        # Station name → ID
        self.bus_stops = {}
        self.rail_stations = {}

        # File and CSV writers for exporting trains
        self.file_routes = None
        self.file_times = None
        self.file_trips = None

        self.wrtr_routes = None
        self.wrtr_trips = None
        self.wrtr_times = None

        # Translations - loaded with agency_name and agency_official_name translations
        self.type_translation = {}

        self.to_kana = {
            "JR北海道": "じぇいあーるほっかいどう",
            "北海道旅客鉄道株式会社": "ほっかいどうりょかくてつどうかぶしきがいしゃ",
            "道南いさりび鉄道": "どうなんいさりびてつどう",
            "道南いさりび鉄道株式会社": "どうなんいさりびてつどうかぶしきがいしゃ",
        }

        self.to_english = {
            "JR北海道": "JR Hokkaido",
            "北海道旅客鉄道株式会社": "Hokkaido Railway Company",
            "道南いさりび鉄道": "South Hokkaido Railway",
            "道南いさりび鉄道株式会社": "South Hokkaido Railway Company",
        }

    # DATA SCRAPING FUNCTIONS #

    def parse_web_ekidori(self, div):
        """Parse the left column, `ekidori` and map row_index to data that is stored there
        """
        rows = {}

        for idx, row in enumerate(div.find_all("tr")):
            # Check row label
            item_name = row.find(lambda i: "item-name" in i.get("class", []))
            if item_name:
                item_name = item_name.get_text().strip()
            else:
                item_name = ""

            # Check if this row is a departure or an arrival
            dep_arr = row.find(lambda i: "dep-arv" in i.get("class", []))
            if dep_arr:
                dep_arr = dep_arr.get_text().strip()
            else:
                dep_arr = ""

            # Generate row label (switch-case, but Python)
            if item_name == "列車番号":
                item = "trip_number"
            elif item_name == "列車名":
                item = "trip_name"
            elif item_name == "" and rows.get(idx - 1, "") == "trip_name":
                item = "trip_name_suffix"
            elif item_name == "始発":
                item = "first_station"
            elif item_name == "運転日":
                item = "active_days"
            elif item_name == "終着":
                item = "last_station"
            elif dep_arr == "着":
                item = "station_{}_arr".format(item_name)
            elif dep_arr == "発":
                item = "station_{}_dep".format(item_name)
            else:
                item = None

            rows[idx] = item

        return rows

    def parse_web_timeheader(self, div, rows, dir_id):
        """Parse the timeHeader and map column_idx to train data
        """
        trains = {}

        for row_idx, row in enumerate(div.find_all("tr")):
            row_data = rows[row_idx]

            # Skip row if it has uniteresting data
            if not row_data:
                continue

            # Iterate over each column (each representing one train, i guess)
            for col_idx, cell in enumerate(row.find_all("td")):
                value = cell.get_text().strip()

                # Ignore empty values
                if not value:
                    continue

                # Create an empty entry for column, if it's undefined
                if col_idx not in trains:
                    trains[col_idx] = {"stations": [], "dir": dir_id}

                # Some additional data derived from train name
                if row_data == "trip_name":
                    style = cell.get("style", "")

                    if value == "バス":
                        trains[col_idx]["type"] = "バス"
                    elif style == "color: #FF0000;":
                        trains[col_idx]["type"] = "特急"
                    elif style == "color: #008080;":
                        trains[col_idx]["type"] = "特別快速"
                    elif style == "color: #0000CD;":
                        trains[col_idx]["type"] = "快速"
                    else:
                        trains[col_idx]["type"] = "普通"

                trains[col_idx][row_data] = value

        return trains

    def parse_web_timebody(self, div, rows, trains):
        """Parse the timeBody and add time data to trains
        """
        evening = False

        for row_idx, row in enumerate(div.find_all("tr")):
            row_data = rows[row_idx]

            # Ignore uninteresting rows
            if not row_data:
                continue

            for col_idx, cell in enumerate(row.find_all("td")):
                value = cell.get_text().strip()

                # Ignore empty values
                if not value:
                    continue

                # Fix for on_click items
                # If a value is too long JRH creates a popup
                on_click = cell.get("onclick", "")

                if on_click:
                    on_click = re.search(
                        r"displayDialog\(jQuery,\s+'(.*?)',\s+'(.*?)'\)",
                        on_click
                    )

                # Also split first_station and last_station to (Station, Time)
                if on_click and row_data in {"first_station", "last_station"}:
                    value = (on_click[2], Time.from_str(value))

                elif row_data in {"first_station", "last_station"}:
                    value = (re.sub(r"(\W|\d)", "", value), Time.from_str(value))

                elif on_click:
                    value = on_click[2]

                # Handle 区休 services
                if row_data == "active_days" and value == "区休":
                    calendar_key = trains[col_idx - 1]["active_days"]

                    if calendar_key not in self.calendar_data["section_changing"]:
                        raise ValueError("Key is missing from calendars.yaml→section_changing "
                                         + calendar_key)

                    days_prev, value = self.calendar_data["section_changing"][calendar_key]

                    # Previous train's active_days have to be modified
                    trains[col_idx - 1]["active_days"] = days_prev

                    del calendar_key, days_prev

                # Avoid time-travelling first_station, last_station pair
                if row_data == "last_stations" and value[1] < trains[col_idx]["first_station"][1]:
                    value = (value[0], value[1] + 86400)

                # This is a row with time info
                if row_data.startswith("station_"):
                    row_data_split = row_data.split("_")
                    station = row_data_split[1]
                    dep_arr = row_data_split[2]

                    # Train-skips-this-station values
                    if value in {"||", "レ", "・", "┐", "＝", ""}:
                        continue

                    # Try to parse the value
                    value = Time.from_str(value)

                    # Set evening flag after 22:00
                    if (not evening) and value > 79200:
                        evening = True

                    # Avoid timetravel: If we reached late-night departures
                    # # but suddendly we have a time between 00:00~04:00, add 24h to value
                    if evening and value < 14400:
                        value += 86400

                    # Check if we encountered this station earlier, if we did get its index
                    station_already_listed = [i for i in trains[col_idx]["stations"]
                                              if i["sta"] == station]
                    if station_already_listed:
                        station_already_listed = trains[col_idx]["stations"]\
                            .index(station_already_listed[0])
                    else:
                        station_already_listed = None

                    # If the station was listed, overwrite its arr/dep time
                    if station_already_listed is not None and dep_arr == "dep":
                        trains[col_idx]["stations"][station_already_listed]["dep"] = value

                    elif station_already_listed is not None and dep_arr == "arr":
                        trains[col_idx]["stations"][station_already_listed]["arr"] = value

                    # If not, just add the station to the list
                    else:
                        trains[col_idx]["stations"].append({
                            "sta": station,
                            "arr": value,
                            "dep": value
                        })

                else:
                    trains[col_idx][row_data] = value

        return trains

    def get_trains(self, ttable_id, dir_id):
        """Return train schedules, parsed from jrhokkaidonorike.com
        """
        print(STR_1UP + f"Requesting page for timetable {ttable_id}")
        req = requests.get("https://jrhokkaidonorikae.com/vtime/vtime.php",
                           params={"s": ttable_id, "d": "0"})
        req.raise_for_status()
        req.encoding = "utf-8"

        print(STR_1UP + f"Parsing timetable {ttable_id}")
        soup = BeautifulSoup(req.text, "html.parser")

        # First, header
        row_data = self.parse_web_ekidori(soup.find("div", id="ekidoriHeader"))
        trains = self.parse_web_timeheader(soup.find("div", id="timeHeader"), row_data, dir_id)

        # Now, actual timetable
        row_data = self.parse_web_ekidori(soup.find("div", id="ekidoriBody"))
        trains = self.parse_web_timebody(soup.find("div", id="timeBody"), row_data, trains)

        # Filter train list
        trains = filter(
            lambda i: len(i["stations"]) > 0 and i.get("active_days") not in {"時変", "臨停"},
            trains.values()
        )

        return trains

    # GTFS CREATION FUNCTIONS #

    @staticmethod
    def agency():
        """Generate agency.txt & agency_jp.txt
        """
        f = open("gtfs/agency.txt", "w", encoding="utf8", newline="\r\n")
        f.write('agency_id,agency_name,agency_url,agency_timezone,agency_lang\n')
        f.write('4430001022657,"JR北海道","https://www.jrhokkaido.co.jp/",Asia/Tokyo,ja\n')
        f.write('3430001067100,"道南いさりび鉄道","https://www.shr-isaribi.jp/",Asia/Tokyo,ja\n')
        f.close()

        f = open("gtfs/agency_jp.txt", "w", encoding="utf8", newline="\r\n")
        f.write('agency_id,agency_official_name,agency_zip_number,agency_address\n')
        f.write('4430001022657,"北海道旅客鉄道株式会社",0608644,'
                '"北海道札幌市中央区北十一条西１５丁目１番１号"\n')
        f.write('3430001067100,"道南いさりび鉄道株式会社",0400063,"北海道函館市若松町１２番５号"\n')
        f.close()

    def stops(self):
        """Parse stops from data/stops_shapes.osm
        """
        with open("gtfs/stops.txt", "w", encoding="utf8", newline="") as f:
            w = csv.DictWriter(f, ["stop_id", "stop_name", "stop_code", "stop_lat", "stop_lon"])
            w.writeheader()

            root = etree.parse("data/stops_shapes.osm").getroot()

            for node in root.iterfind("node"):
                tags = {tag.get("k"): tag.get("v") for tag in node.findall("tag")}

                if tags.get("railway") != "station" and tags.get("highway") != "bus_stop":

                    continue

                w.writerow({
                    "stop_id": tags["id"],
                    "stop_name": tags["name"],
                    "stop_code": tags.get("ref", ""),
                    "stop_lat": node.attrib["lat"],
                    "stop_lon": node.attrib["lon"],
                })

                self.to_kana[tags["name"]] = tags["name:ja_kana"]
                self.to_english[tags["name"]] = tags["name:en"]

                if tags.get("highway") == "bus_stop":
                    self.bus_stops[tags["name"]] = tags["id"]
                else:
                    self.rail_stations[tags["name"]] = tags["id"]

    def translations(self):
        """Dump gathered translations to GTFS
        """
        with open("gtfs/translations.txt", mode="w", encoding="utf8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["trans_id", "lang", "translation"])

            for jp, kana in self.to_kana.items():
                en = self.to_english[jp]

                w.writerow([jp, "ja", jp])
                w.writerow([jp, "ja-Hrkt", kana])
                w.writerow([jp, "en", en])

    def load_calendar_data(self):
        """Load data from data/calendars.yaml
        """
        with open("data/calendars.yaml", "r", encoding="utf8") as f:
            data = yaml.safe_load(f)

        self.calendar_data = data

        for desc, values in self.calendar_data["other"].items():
            # Convert start and end dated into tuple
            if "start" in values:
                self.calendar_data["other"][desc]["start"] = tuple(values["start"])

            if "end" in values:
                self.calendar_data["other"][desc]["end"] = tuple(values["end"])

            # Convert removed and added to sets of tuples
            if "removed" in values:
                self.calendar_data["other"][desc]["removed"] = \
                    {tuple(i) for i in values["removed"]}

            if "added" in values:
                self.calendar_data["other"][desc]["added"] = {tuple(i) for i in values["added"]}

    def calendars(self):
        """Parse all used calendars and save them to calendar_dates.txt
        """
        with open("gtfs/calendar_dates.txt", mode="w", encoding="utf8", newline="") as f:
            if OUTPUT_SERVICE_DESC:
                header = ["service_id", "service_desc", "date", "exception_type"]
            else:
                header = ["service_id", "date", "exception_type"]

            w = csv.DictWriter(f, header)
            w.writeheader()

            start = date.today()
            end = start + timedelta(days=365)

            print(STR_1UP + "requesting list of holidays")
            holidays = load_holidays(start, end)

            for service_desc, service_id in self.services.items():

                # Load service pattern
                if service_desc in self.calendar_data["regular"]:
                    print(STR_1UP + f"saving regular calendar: {service_desc}")

                    service_data = {}
                    pattern_days = self.calendar_data["regular"][service_desc]

                elif service_desc in self.calendar_data["other"]:
                    print(STR_1UP + f"saving calendar manually described: {service_desc}")

                    service_data = self.calendar_data["other"][service_desc]
                    pattern_days = self.calendar_data["regular"][service_data["pattern"]]

                else:
                    print(STR_1UP + f"saving untenbi-parsed calendar: {service_desc}")
                    service_data = parse_untenbi.parse(service_desc)
                    pattern_days = self.calendar_data["regular"][service_data["pattern"]]

                # Iterate over valid day
                current_day = start

                while current_day <= end:
                    write = False
                    weekday = 6 if current_day in holidays else current_day.weekday()
                    # ↑ all holidays behave like sundays

                    date_tpl = current_day.month, current_day.day

                    # 1. Ignore day if it's past-end or pre-start
                    if date_tpl > service_data.get("end", (12, 31)) \
                            or date_tpl < service_data.get("start", (1, 1)):
                        write = False

                    # 2. Check if this calendar is marked as "removed" for this day
                    elif date_tpl in service_data.get("removed", set()):
                        write = False

                    # 3. Check if this calendar is marked as "added" for this day
                    elif date_tpl in service_data.get("added", set()):
                        write = True

                    # 4. Check if this calendar is active
                    elif pattern_days[weekday] == 1:
                        write = True

                    # 5. Fallback to disabled
                    else:
                        write = False

                    if write:
                        row = {
                            "service_id": service_id,
                            "date": current_day.strftime("%Y%m%d"),
                            "exception_type": 1,
                        }

                        if OUTPUT_SERVICE_DESC:
                            row["service_desc"] = service_desc

                        w.writerow(row)

                    current_day += timedelta(days=1)

    def feed_info(self):
        """Create feed_info.txt
        """
        with open("gtfs/feed_info.txt", mode="w", encoding="utf8", newline="") as f:
            w = csv.writer(f)

            w.writerow(["feed_publisher_name", "feed_publisher_url", "feed_lang", "feed_version"])
            w.writerow([
                "HokkaidoRailGTFS",
                "https://github.com/MKuranowski/HokkaidoRailGTFS",
                "ja",
                datetime.now(tz=pytz.timezone("Asia/Tokyo")).strftime("%Y%m%d_%H%M%S")
            ])

    @staticmethod
    def compress():
        with zipfile.ZipFile("hokkaidorail.zip", "w", zipfile.ZIP_DEFLATED) as arch:
            for entry in os.scandir("gtfs"):
                if entry.name.endswith(".txt"):
                    arch.write(entry.path, entry.name)

    # CONVERTING TRAINS TO GTFS #

    def load_routes_info(self):
        """Load data/routes.yaml
        """
        with open("data/routes.yaml", "r", encoding="utf8") as f:
            ext_data = yaml.safe_load(f)
            self.routes = ext_data["routes"]
            self.expresses = ext_data["expresses"]

    def load_type_translation(self):
        """Load data/type_translation.csv
        """
        with open("data/type_translation.csv", mode="r", encoding="utf8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.type_translation[row["name_ja"]] = row["name_en"], row["name_kana"]

    def open_sched_files(self):
        """Open routes.txt, trips.txt & stop_times.txt,
        and create csv.DictWriters wrapped around those files.
        """
        self.file_routes = open("gtfs/routes.txt", "w", encoding="utf8", newline="")
        self.file_trips = open("gtfs/trips.txt", "w", encoding="utf8", newline="")
        self.file_times = open("gtfs/stop_times.txt", "w", encoding="utf8", newline="")

        self.wrtr_routes = csv.DictWriter(
            self.file_routes,
            ["agency_id", "route_id", "route_short_name", "route_long_name",
             "route_type", "route_color", "route_text_color"]
        )

        self.wrtr_trips = csv.DictWriter(
            self.file_trips,
            ["route_id", "trip_id", "service_id", "trip_headsign",
             "trip_short_name", "direction_id", "block_id", "shape_id"]
        )

        self.wrtr_times = csv.DictWriter(
            self.file_times,
            ["trip_id", "stop_sequence", "stop_id", "arrival_time", "departure_time"]
        )

        self.wrtr_routes.writeheader()
        self.wrtr_trips.writeheader()
        self.wrtr_times.writeheader()

    def close_sched_files(self):
        """Close routes.txt, trips.txt & stop_times.txt
        """
        self.file_routes.close()
        self.file_times.close()
        self.file_trips.close()

        self.wrtr_routes = None
        self.wrtr_trips = None
        self.wrtr_times = None

    def get_trip_headsign(self, train_type, train_name, train_name_suffix, dest):
        """Given some information about a train generate
        and return the trip_headsign.
        Headsign translations are also handled.
        """
        type_en, type_kana = self.type_translation[train_type]
        name_en, name_kana = self.type_translation[train_name]

        dest_en = self.to_english[dest]
        dest_kana = self.to_kana[dest]

        if train_type == train_name:
            ja_headsign = f"（{train_type}）"
            en_headsign = f" ({type_en}) "
            kana_headsign = f"（{type_kana}）"

        elif train_name_suffix:
            ja_headsign = f'（{train_type}「{train_name}{train_name_suffix}」）'
            en_headsign = f' ({type_en} "{name_en} {train_name_suffix}") '
            kana_headsign = f'（{type_kana}「{name_kana}{train_name_suffix}」）'

        else:
            ja_headsign = f'（{train_type}「{train_name}」）'
            en_headsign = f' ({type_en} "{name_en}") '
            kana_headsign = f'（{type_kana}「{name_kana}」）'

        ja_headsign += dest
        en_headsign += dest_en
        kana_headsign += dest_kana

        self.to_kana[ja_headsign] = kana_headsign
        self.to_english[ja_headsign] = en_headsign

        return ja_headsign

    def convert_to_gtfs(self, train):
        """Given a train (as yielded by get_trains()), convert it to
        GTFS. route_id is not added to the trip entry.
        Returns (gtfs_trip, list_of_gtfs_stop_times).
        """
        gtfs_trip = {}
        gtfs_times = []

        # service_id
        service_id = self.services.get(train["active_days"])

        if service_id is None:
            service_id = len(self.services)
            self.services[train["active_days"]] = service_id

        gtfs_trip["service_id"] = service_id

        # trip_id
        trip_id = self.trip_enumerator
        self.trip_enumerator += 1

        gtfs_trip["trip_id"] = trip_id

        # block_id
        first_trip_station = train["stations"][0]["sta"], train["stations"][0]["dep"]
        last_trip_station = train["stations"][-1]["sta"], train["stations"][-1]["arr"]
        block_hash = (*train["first_station"], *train["last_station"])

        if first_trip_station != train["first_station"] \
                or last_trip_station != train["last_station"]:

            block_id = self.blocks.get(block_hash)

            if block_id is None:
                block_id = len(self.blocks)
                self.blocks[block_hash] = block_id

        else:
            block_id = ""

        gtfs_trip["block_id"] = block_id

        # Other Data
        gtfs_trip["trip_headsign"] = self.get_trip_headsign(
            train["type"], train["trip_name"],
            train.get("trip_name_suffix", ""), train["last_station"][0]
        )

        gtfs_trip["direction_id"] = train["dir"]
        gtfs_trip["trip_short_name"] = train.get("trip_number", "")

        # Stop times
        for idx, stoptime in enumerate(train["stations"]):

            # stop_id
            if train["type"] == "バス":
                stop_id = self.bus_stops.get(stoptime["sta"])

                if stop_id is None:
                    stop_id = -1
                    warn(f"!!! missing bus stop with name {stoptime['sta']}")

            else:
                stop_id = self.rail_stations.get(stoptime["sta"])

                if stop_id is None:
                    stop_id = -1
                    warn(f"!!! missing rail station with name {stoptime['sta']}")

            gtfs_times.append({
                "trip_id": trip_id,
                "stop_sequence": idx,
                "stop_id": stop_id,
                "arrival_time": str(stoptime["arr"]),
                "departure_time": str(stoptime["dep"]),
            })

        return gtfs_trip, gtfs_times

    def trains_normal(self):
        """Generate and save to GTFS all 'normal' trains (from self.routes)
        """
        ignore_names = {name for exp in self.expresses["trains"] for name in exp["web_names"]}

        print("")

        for route in self.routes:
            used_routes = set()

            if route.get("split") is True:
                print(STR_1UP
                      + f"Parsing routes {route['route_a']['id']} & {route['route_b']['id']} "
                      f"({route['route_a']['name_en']!r} & {route['route_b']['name_en']!r})",
                      end="\n\n")
            else:
                print(STR_1UP + f"Prasing route {route['id']} ({route['name_en']!r})", end="\n\n")

            print(STR_1UP + "Scraping jrhokkaidonorikae.com pages")
            trains = chain(self.get_trains(route["web_down"], 0),
                           self.get_trains(route["web_up"], 1))

            # Prase trains
            for train in trains:
                # Filter out trains we get from express timetables
                if train["trip_name"] in ignore_names:
                    continue

                print(STR_1UP + f"Train no: {train.get('trip_number', '')}")

                # Filter out some stations
                if "exclude" in route:
                    train["stations"] = [i for i in train["stations"]
                                         if i["sta"] not in route["exclude"]]

                if route["split"] is True:
                    part_a, part_b = split_train(train, route["split_at"],
                                                 route["route_a"]["id_station"],
                                                 route["route_b"]["id_station"])

                    # Filter parts _only_ between Sapporo and Shiroishi and Tomakomai-Numanohata
                    # Those are stubs left out by Hakodate-Chitose line through service and
                    # Muroran Oiwake-Tomakomai-Itoi through train
                    if part_a is not None \
                            and {part_a["stations"][0]["sta"], part_a["stations"][-1]["sta"]} \
                            in [{"札幌", "白石"}, {"苫小牧", "沼ノ端"}]:

                        part_a = None

                    elif part_b is not None \
                            and {part_b["stations"][0]["sta"], part_b["stations"][-1]["sta"]} \
                            in [{"札幌", "白石"}, {"苫小牧", "沼ノ端"}]:

                        part_b = None

                    # Convert part blonging to route a
                    if part_a is not None and len(part_a["stations"]) > 0:
                        trip, times = self.convert_to_gtfs(part_a)
                        route_id = route["route_a"]["id"]

                        if part_a["type"] == "バス":
                            route_id += 100

                        trip["route_id"] = route_id
                        used_routes.add(route_id)

                        # write to GTFS
                        self.wrtr_trips.writerow(trip)
                        self.wrtr_times.writerows(times)

                    # Convert part belonging to route b
                    if part_b is not None and len(part_b["stations"]) > 0:
                        trip, times = self.convert_to_gtfs(part_b)
                        route_id = route["route_b"]["id"]

                        if part_b["type"] == "バス":
                            route_id += 100

                        trip["route_id"] = route_id
                        used_routes.add(route_id)

                        # write to GTFS
                        self.wrtr_trips.writerow(trip)
                        self.wrtr_times.writerows(times)

                elif len(train["stations"]) > 0:
                    # convert train data to GTFS
                    trip, times = self.convert_to_gtfs(train)

                    # route_id
                    if train["type"] == "バス":
                        trip["route_id"] = route["id"] + 100
                        used_routes.add(route["id"] + 100)
                    else:
                        trip["route_id"] = route["id"]
                        used_routes.add(route["id"])

                    # write to GTFS
                    self.wrtr_trips.writerow(trip)
                    self.wrtr_times.writerows(times)

            # Make all known routes into an iterable
            if route["split"]:
                known_gtfs_routes = [route["route_a"], route["route_b"]]

            else:
                known_gtfs_routes = [route]

            # Iterate over each known GTFS route and check if it should be exported
            for gtfs_route in known_gtfs_routes:
                txt_color = get_text_color(gtfs_route["color"])

                if gtfs_route["id"] in used_routes:
                    self.wrtr_routes.writerow({
                        "agency_id": gtfs_route.get("agency", DEFAULT_AGENCY),
                        "route_id": gtfs_route["id"],
                        "route_short_name": gtfs_route["name"],
                        "route_long_name": gtfs_route["desc"],
                        "route_type": 2,
                        "route_color": gtfs_route["color"],
                        "route_text_color": txt_color,
                    })

                    self.to_kana[gtfs_route["name"]] = gtfs_route["name_kana"]
                    self.to_english[gtfs_route["name"]] = gtfs_route["name_en"]

                    self.to_kana[gtfs_route["desc"]] = gtfs_route["desc_kana"]
                    self.to_english[gtfs_route["desc"]] = gtfs_route["desc_en"]

                if gtfs_route["id"] + 100 in used_routes:
                    repl_desc = "【バス代行】" + gtfs_route["desc"]
                    self.wrtr_routes.writerow({
                        "agency_id": gtfs_route.get("agency", DEFAULT_AGENCY),
                        "route_id": gtfs_route["id"] + 100,
                        "route_short_name": gtfs_route["name"],
                        "route_long_name": repl_desc,
                        "route_type": 3,
                        "route_color": gtfs_route["color"],
                        "route_text_color": txt_color,
                    })

                    self.to_kana[gtfs_route["name"]] = gtfs_route["name_kana"]
                    self.to_english[gtfs_route["name"]] = gtfs_route["name_en"]

                    self.to_kana[repl_desc] = "【ばすだいこう】" + gtfs_route["desc_kana"]
                    self.to_english[repl_desc] = "[Replacement Bus] " + gtfs_route["desc_en"]

    def trains_express(self):
        """Generate and save to GTFS all express trains (from self.expresses)
        """

        train_name_to_route = {}

        print(STR_1UP + "Parsing express trains", end="\n\n")

        # Iterate over each express route:
        for train in self.expresses["trains"]:
            txt_color = get_text_color(train["color"])

            for name in train["web_names"]:
                train_name_to_route[name] = train["id"]

            self.wrtr_routes.writerow({
                "agency_id": train.get("agency", DEFAULT_AGENCY),
                "route_id": train["id"],
                "route_short_name": train["name"],
                "route_long_name": train["desc"],
                "route_type": 2,
                "route_color": train["color"],
                "route_text_color": txt_color,
            })

            self.to_kana[train["name"]] = train["name_kana"]
            self.to_english[train["name"]] = train["name_en"]

            self.to_kana[train["desc"]] = train["desc_kana"]
            self.to_english[train["desc"]] = train["desc_en"]

            self.type_translation[train["name"]] = train["name_en"], train["name_kana"]

        print(STR_1UP + "Scraping jrhokkaidonorikae.com pages")
        down_trains = (t for r in self.expresses["web_down"] for t in self.get_trains(r, 0))
        up_trains = (t for r in self.expresses["web_up"] for t in self.get_trains(r, 1))

        # Dump train data
        for train in chain(down_trains, up_trains):
            if train["trip_name"] == "普通" or len(train["stations"]) == 0:
                continue

            print(STR_1UP + f"Train no: {train['trip_number']}")

            # route_id
            route_id = train_name_to_route.get(train["trip_name"])

            if route_id is None:
                raise ValueError(f"unrecognized express train {train['trip_name']!r}"
                                 "make sure it is present in data/routes.yaml → expresses")

            train["type"] = "特急"

            gtfs_trip, gtfs_times = self.convert_to_gtfs(train)
            gtfs_trip["route_id"] = route_id

            self.wrtr_trips.writerow(gtfs_trip)
            self.wrtr_times.writerows(gtfs_times)

    def trains(self):
        """Create gtfs/trips.txt and gtfs/stop_times.txt from jrhokkaidonorike.com"""
        self.load_routes_info()
        self.load_type_translation()

        self.open_sched_files()
        try:
            self.trains_normal()
            self.trains_express()
        finally:
            self.close_sched_files()

    # AUTO-PARSING #

    @classmethod
    def parse(cls):
        self = cls()

        print("agency")
        self.agency()

        print("stops")
        self.stops()

        print("loading calendars.yaml")
        self.load_calendar_data()

        print("trains")
        self.trains()

        print(STR_1UP + "calendars", end="\n\n")
        self.calendars()

        print(STR_1UP + "translations")
        self.translations()

        print("feed_info")
        self.feed_info()

        print("saving to hokkaidorail.zip")
        self.compress()

if __name__ == "__main__":
    HokkaidoRailGTFS.parse()
