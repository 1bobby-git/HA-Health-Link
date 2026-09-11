from custom_components.health_link.baseline.engine import robust_baseline, robust_zscore, relative_change

def test_robust_baseline_handles_outlier():
    result=robust_baseline([10,10,11,9,10,1000]);assert result.count==6;assert result.median==10;assert result.mean is not None and result.mean>result.median

def test_relative_change():assert relative_change(110,100)==10;assert relative_change(90,100)==-10;assert relative_change(10,0) is None

def test_zscore_needs_nonzero_mad():assert robust_zscore(2,robust_baseline([1,1,1,1])) is None
