from custom_components.health_link.analytics.engine import align_previous, observed_best_range, pearson

def test_pearson_positive():
    result=pearson([(1,1),(2,2),(3,3),(4,4)]);assert result.correlation==1.0;assert result.direction=="positive"

def test_align_previous_uses_persisted_home_state():
    pairs=align_previous([("2026-09-11T10:05:00+00:00",5),("2026-09-11T10:30:00+00:00",7)],[("2026-09-11T10:00:00+00:00",20),("2026-09-11T10:20:00+00:00",21)]);assert pairs==[(5.0,20.0),(7.0,21.0)]

def test_observed_best_range_requires_enough_data():assert observed_best_range([(1,20),(2,21)]) is None
