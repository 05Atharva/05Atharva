from calendar import month_abbr
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from string import Template
from urllib.request import Request, urlopen


SCRIPT = Path(__file__).resolve()
OUTPUT = SCRIPT.parents[2] / "assets" / "flight-log.svg"
CALENDAR_URL = "https://github.com/users/05Atharva/contributions"


class ContributionCalendar(HTMLParser):
    def __init__(self):
        super().__init__()
        self.levels = {}

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag != "td" or "ContributionCalendar-day" not in attributes.get("class", "").split():
            return

        day = date.fromisoformat(attributes["data-date"])
        level = int(attributes["data-level"])
        if day in self.levels or not 0 <= level <= 4:
            raise ValueError(f"Unexpected contribution calendar cell for {day}")
        self.levels[day] = level


def read_calendar():
    request = Request(CALENDAR_URL, headers={"User-Agent": "05Atharva-profile-flight-log"})
    parser = ContributionCalendar()
    with urlopen(request, timeout=30) as response:
        parser.feed(response.read().decode("utf-8"))
    parser.close()

    days = sorted(parser.levels)
    today = datetime.now(timezone.utc).date()
    if not 365 <= len(days) <= 367:
        raise ValueError(f"Expected a year of contribution data, got {len(days)} days")
    if (days[-1] - days[0]).days + 1 != len(days):
        raise ValueError("GitHub returned an incomplete contribution calendar")
    if not today - timedelta(days=2) <= days[-1] <= today + timedelta(days=1):
        raise ValueError(f"GitHub returned a contribution calendar ending {days[-1]}")

    return {day: parser.levels[day] for day in days}


def render_calendar(levels):
    first_day = min(levels)
    last_day = max(levels)
    first_sunday = first_day - timedelta(days=(first_day.weekday() + 1) % 7)
    month_labels = []
    cells = []

    for day, level in levels.items():
        week, weekday = divmod((day - first_sunday).days, 7)
        x, y = 350 + 10 * week, 77 + 10 * weekday
        if day.day == 1 and week <= 51:
            month_labels.append(f'<text x="{x}" y="68">{month_abbr[day.month]}</text>')
        cells.append(f'<rect class="level-{level}" x="{x}" y="{y}" width="8" height="8" rx="2"/>')

    template = Template(SCRIPT.with_name("flight-log.svg").read_text(encoding="utf-8"))
    return template.substitute(
        months="\n    ".join(month_labels),
        cells="\n    ".join(cells),
        active_days=sum(level > 0 for level in levels.values()),
        through=f"{last_day.day:02} {month_abbr[last_day.month].upper()} {last_day.year}",
    )


if __name__ == "__main__":
    artwork = render_calendar(read_calendar())
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(artwork, encoding="utf-8", newline="\n")
