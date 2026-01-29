import datetime


def get_current_date(f: str = "%d-%m-%Y") -> str:
    return datetime.datetime.now().strftime("%d-%m-%Y")

def get_current_time(f: str = "%H:%M") -> str:
    return datetime.datetime.now().strftime("%H:%M")
