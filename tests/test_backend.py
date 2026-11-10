import asyncio
import json
import pytest
from iphone_location.backend import session

class Context:
    def __init__(self,*_):pass
    async def __aenter__(self):return self
    async def __aexit__(self,*_):pass

class Simulation(Context):
    def __init__(self,log):self.log=log
    async def set(self,lat,lon):self.log.append(('set',lat,lon))
    async def clear(self):self.log.append(('clear',))

async def noop():pass

def run(lines,log):
    messages=iter(lines)
    async def read():return next(messages,'')
    return asyncio.run(session(noop,Context,lambda _:Simulation(log),noop,read))

def test_stop_restores_after_set_and_uses_wgs_by_default(capsys):
    log=[]
    run([json.dumps(dict(action='set',lat=40,lon=116)),json.dumps(dict(action='stop'))],log)
    assert log==[('set',40,116),('clear',)]
    assert '"event": "cleared"' in capsys.readouterr().out

def test_bad_coordinate_clears_simulation():
    log=[]
    with pytest.raises(ValueError):run(['{"action":"set","lat":90,"lon":116}'],log)
    assert log==[('clear',)]

def test_eof_clears_and_gcj_import_is_explicit():
    log=[]
    run(['{"action":"set","lat":40.158649,"lon":116.286210,"coordinateSystem":"gcj02"}'],log)
    assert log[0][1:]==pytest.approx((40.1574011978,116.2801353860),abs=1e-8)
    assert log[-1]==('clear',)
