from holdsport.api import get_current_week_activities, get_teams, get_members
from datetime import date

def test_get_teams():
    teams = get_teams()
    assert len(teams) == 3 is not None
    team_ids = [team['id'] for team in teams]
    assert team_ids == [5289, 53781, 55219]

def test_get_activities():
    # start_date = date.today()
    activities = get_current_week_activities(team_id=5289)
    assert len(activities) == 3

def test_get_members():
    members = get_members(team_id=5289)
    assert len(members) == 3
