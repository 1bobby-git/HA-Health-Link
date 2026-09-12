from custom_components.health_link.intelligence import build_daily_context, progress, relative_to_median, report_payload


def test_progress_and_disabled_goal():
    assert progress(5000,10000)==50.0
    assert progress(10,0) is None

def test_daily_context_uses_user_goals_only():
    data={"steps_today":6000,"exercise_time_today":30,"recovery_below_baseline":False}
    out=build_daily_context(data,{"goal_steps":10000,"goal_exercise_minutes":30,"goal_water_ml":0})
    assert out["goals"]["steps"]["progress"]==60.0
    assert out["goals"]["exercise_minutes"]["reached"] is True
    assert "water_ml" not in out["goals"]
    assert out["daily_focus"]=="steps"

def test_report_is_not_medical_and_has_source():
    report=report_payload({"data_stale":False,"steps_today":1000,"data_confidence":80}, {"goal_steps":2000}, profile="A")
    assert report["medical_diagnosis"] is False
    assert report["source"]=="home_assistant_ios_apple_health_sensors_labs"

def test_relative_to_median():
    assert relative_to_median(120,[100,100,100])==20.0
