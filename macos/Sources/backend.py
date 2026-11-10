import asyncio, json, sys, warnings, math
from coordinate_conversion import gcj02_to_wgs84
warnings.filterwarnings('ignore', message='urllib3 v2 only supports')
from pymobiledevice3.remote.userspace_tunnel import establish_userspace_rsd
from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation

def emit(event, **fields):
    print(json.dumps(dict(event=event, **fields)), flush=True)

async def main():
    location = None
    try:
        emit('status', message='正在准备开发支持组件…')
        p = await asyncio.create_subprocess_exec(sys.executable, '-m', 'pymobiledevice3', 'mounter', 'auto-mount', stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, err = await asyncio.wait_for(p.communicate(), 90)
        if p.returncode:
            raise RuntimeError((err or out).decode(errors='replace')[-1500:])
        emit('status', message='正在建立手机开发连接…')
        rsd = await asyncio.wait_for(establish_userspace_rsd(), 30)
        async with DvtProvider(rsd) as dvt, LocationSimulation(dvt) as loc:
            location = loc
            emit('ready')
            try:
                while True:
                    line = await asyncio.get_running_loop().run_in_executor(None, sys.stdin.readline)
                    if not line: break
                    cmd = json.loads(line)
                    if cmd['action'] == 'stop': break
                    lat, lon = float(cmd['lat']), float(cmd['lon'])
                    if not math.isfinite(lat) or not math.isfinite(lon) or not -85 <= lat <= 85 or not -180 <= lon <= 180:
                        raise ValueError('坐标超出范围')
                    gps_lat,gps_lon=gcj02_to_wgs84(lat,lon) if cmd.get('coordinateSystem')=='gcj02' else (lat,lon)
                    await asyncio.wait_for(loc.set(gps_lat, gps_lon), 8)
                    emit('position', lat=lat, lon=lon, gpsLat=gps_lat, gpsLon=gps_lon)
            finally:
                try:
                    await asyncio.wait_for(loc.clear(), 8)
                    emit('cleared')
                except Exception as e:
                    emit('error', message='恢复定位未确认，请重连后点击恢复，或重启手机：'+str(e))
    except Exception as e:
        emit('error', message=str(e))

asyncio.run(main())
