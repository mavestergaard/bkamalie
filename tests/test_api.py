from bkamalie.holdsport.api import get_current_week_activities, get_teams, get_members


def test_get_teams(holdsport_con):
    teams = get_teams(holdsport_con)
    assert len(teams) == 3 != None
    team_ids = [team["id"] for team in teams]
    assert team_ids == [5289, 53781, 55219]


def test_get_activities(holdsport_con):
    # start_date = date.today()
    activities = get_current_week_activities(holdsport_con, team_id=5289)
    assert len(activities) > 0


def test_get_members(holdsport_con):
    members = get_members(holdsport_con, team_id=5289)
    assert len(members) > 0
