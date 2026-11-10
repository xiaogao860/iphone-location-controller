import math
import pytest
from iphone_location.motion import DEFAULT_CENTER, Route, distance, manual_step, track, validate
from iphone_location.coordinates import gcj02_to_wgs84, wgs84_to_gcj02

def test_speed_and_diagonal_normalization():
    origin=(40,116)
    north=manual_step(origin,1,0,36,2)
    diagonal=manual_step(origin,1,1,36,2)
    assert distance(origin,north)==pytest.approx(20,abs=.001)
    assert distance(origin,diagonal)==pytest.approx(20,abs=.001)
    assert manual_step(origin,0,0,36,2)==origin

@pytest.mark.parametrize('point',[(math.nan,116),(40,math.inf),(86,116),(40,181)])
def test_invalid_coordinates(point):
    with pytest.raises(ValueError):validate(point)

def test_track_perimeter_rotation_and_closed_loop():
    for angle in [0,45,90,-15]:
        points=track(DEFAULT_CENTER,400,angle)
        assert len(points)==145 and points[0]==points[-1]
        assert Route(points).total==pytest.approx(400,abs=.2)
    assert Route(track(DEFAULT_CENTER,800,0)).total==pytest.approx(800,abs=.3)

def test_route_turn_endpoint_and_full_laps():
    points=[(40,116),(40.001,116),(40.001,116.001)]
    r=Route(points);first=distance(points[0],points[1]);second=distance(points[1],points[2])
    mid=r.advance(first/2);assert mid[0]==pytest.approx(40.0005,abs=1e-6)
    turned=r.advance(first/2+second/2);assert turned[1]==pytest.approx(116.0005,abs=1e-6)
    assert r.advance(10000)==points[-1] and r.completed
    lap=Route(points+[points[0]])
    expected=Route(lap.points).advance(5,True)
    assert distance(lap.advance(lap.total*1000+5,True),expected)<.001
    assert not lap.completed

def test_duplicate_segments_and_dateline():
    r=Route([(40,116),(40,116),(40.001,116)])
    assert distance(r.advance(5),(40,116))==pytest.approx(5,abs=.001)
    r=Route([(0,179.9),(0,-179.9)])
    assert abs(abs(r.advance(r.total/2)[1])-180)<1e-6

def test_coordinate_import_only_once():
    converted=gcj02_to_wgs84(39.904123,116.397682)
    assert converted==pytest.approx(DEFAULT_CENTER,abs=1e-9)
    assert wgs84_to_gcj02(*converted)==pytest.approx((39.904123,116.397682),abs=1e-8)
    assert gcj02_to_wgs84(48.85,2.35)==(48.85,2.35)

def test_unlimited_speed_and_zero_speed():
    assert distance((40,116),manual_step((40,116),1,0,3600,1))==pytest.approx(1000,abs=.01)
    assert manual_step((40,116),1,0,0,1)==pytest.approx((40,116))
