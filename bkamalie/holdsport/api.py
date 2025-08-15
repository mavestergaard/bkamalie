import requests
from datetime import date, datetime, timedelta
from bkamalie.database.model import Team, User
from pydantic import BaseModel
from enum import StrEnum, Enum

MENS_TEAM_ID = 5289
FINEBOX_ADMIN_MEMBER_ID = 1053833
FINEBOX_ADMIN_MEMBER_ID_WOMEN = 452163


class TeamLevel(StrEnum):
    FIRST = "first"
    SECOND = "second"
    THIRD = "third"
    ALL = "all"


class PlayerStatus(StrEnum):
    ATTENDING = "Attending"
    NOT_ATTENDING = "Not attending"
    UNKNOWN = "Unknown"


class AcvtivityType(StrEnum):
    TRAINING = "training"
    MATCH = "match"


class Role(Enum):
    PLAYER = 1
    COACH = 2
    TEAMLEADER = 3

    def to_string(self):
        return self.name.lower()


class Player(BaseModel):
    id: int
    name: str
    status: PlayerStatus


class Acvtivity(BaseModel):
    id: int
    name: str
    date_of_activity: date
    week_of_activity: int
    location: str
    team_level: TeamLevel
    activity_type: AcvtivityType
    players: list[Player]


class Member(BaseModel):
    id: int
    name: str
    role: Role


def get_connection(user_name: str, password: str) -> str:
    url = f"https://{user_name}:{password}@api.holdsport.dk"
    return url


def verify_user(user_name: str, password: str) -> User | None:
    url = "https://api.holdsport.dk/v1/user"
    response = requests.get(
        url, auth=(user_name, password), headers={"Accept": "application/json"}
    )
    return (
        User(
            id=response.json().get("id"),
            full_name=response.json().get("firstname")
            + " "
            + response.json().get("lastname"),
        )
        if response.status_code == 200
        else None
    )


def get_available_teams(user_name: str, password: str) -> list[Team] | None:
    url = "https://api.holdsport.dk/v1/teams"
    response = requests.get(
        url, auth=(user_name, password), headers={"Accept": "application/json"}
    )
    return (
        [Team(id=team.get("id"), name=team.get("name")) for team in response.json()]
        if response.status_code == 200
        else None
    )


def get_teams(con: str):
    url = f"{con}/v1/teams"
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None


def get_team_level(activity_name: str):
    if "S2" in activity_name:
        return TeamLevel.FIRST
    elif "S4" in activity_name:
        return TeamLevel.SECOND
    elif "S5" in activity_name:
        return TeamLevel.THIRD
    else:
        return TeamLevel.ALL


def get_current_week_activities(con: str, team_id: int) -> list[Acvtivity]:
    today = date.today()
    start_date = today - timedelta(days=today.weekday())
    url = f"{con}/v1/teams/{team_id}/activities?date={start_date}"
    response = requests.get(url)
    activities = []
    for activity in response.json():
        players = []
        for player in activity["activities_users"]:
            players.append(
                Player(
                    id=player["id"],
                    name=player["name"],
                    status=player["status"],
                )
            )
        activity_date = datetime.fromisoformat(activity["starttime"]).date()
        if start_date.isocalendar().week == activity_date.isocalendar().week:
            activities.append(
                Acvtivity(
                    id=activity["id"],
                    name=activity["name"],
                    date_of_activity=activity_date,
                    week_of_activity=activity_date.isocalendar().week,
                    location=activity["place"],
                    team_level=get_team_level(activity["name"]),
                    activity_type=AcvtivityType.MATCH
                    if "Match" in activity["event_type"]
                    else AcvtivityType.TRAINING,
                    players=players,
                )
            )

    return activities


def get_members(con: str, team_id: int) -> list[Member]:
    url = f"{con}/v1/teams/{team_id}/members"
    response = requests.get(url)
    members = []
    if response.status_code == 200:
        for member in response.json():
            members.append(
                Member(
                    id=member["id"],
                    name=member["firstname"] + " " + member["lastname"],
                    role=Role(member["role"]),
                )
            )
    return members
