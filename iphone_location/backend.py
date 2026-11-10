"""Headless worker; one line of JSON in/out. Works in source and frozen builds."""
import asyncio
import json
import os
import sys
from .motion import validate
from .coordinates import gcj02_to_wgs84

def emit(event, **fields):
    sys.stdout.write(json.dumps(dict(event=event,**fields),ensure_ascii=False)+'\n')
    sys.stdout.flush()

def child_command(*args):
    if getattr(sys,'frozen',False):
        return [sys.executable,'--pmd3',*args]
    return [sys.executable,'-m','pymobiledevice3',*args]

async def prepare():
    options = {'creationflags':0x08000000} if os.name=='nt' else {}
    p = await asyncio.create_subprocess_exec(*child_command('mounter','auto-mount'),stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,**options)
    try:
        out,err = await asyncio.wait_for(p.communicate(),120)
    except BaseException:
        if p.returncode is None:
            p.kill()
            await p.wait()
        raise
    if p.returncode:
        raise RuntimeError((err or out).decode(errors='replace')[-2000:])

async def session(provider_factory=None, dvt_factory=None, simulation_factory=None, prepare_fn=prepare, reader=None):
    if provider_factory is None:
        from pymobiledevice3.remote.userspace_tunnel import establish_userspace_rsd
        from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
        from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation
        provider_factory,dvt_factory,simulation_factory=establish_userspace_rsd,DvtProvider,LocationSimulation
    emit('status',message='正在准备开发支持组件，请解锁手机…')
    await prepare_fn()
    emit('status',message='正在建立 USB 开发连接…')
    rsd=await asyncio.wait_for(provider_factory(),40)
    async with dvt_factory(rsd) as dvt, simulation_factory(dvt) as loc:
        emit('ready')
        try:
            while True:
                line=await reader() if reader else await asyncio.get_running_loop().run_in_executor(None,sys.stdin.readline)
                if not line: break
                cmd=json.loads(line)
                if cmd.get('action')=='stop': break
                if cmd.get('action')!='set': raise ValueError('未知操作')
                lat,lon=validate((cmd['lat'],cmd['lon']))
                if cmd.get('coordinateSystem','wgs84')=='gcj02':
                    lat,lon=gcj02_to_wgs84(lat,lon)
                lat,lon=validate((lat,lon))
                await asyncio.wait_for(loc.set(lat,lon),8)
                emit('position',lat=lat,lon=lon)
        finally:
            try:
                await asyncio.wait_for(loc.clear(),8)
                emit('cleared')
            except Exception as exc:
                emit('error',message='恢复定位未确认，请重新连接后恢复，或重启手机：'+str(exc))
                raise

def main():
    try:
        asyncio.run(session())
    except Exception as exc:
        emit('error',message=str(exc) or type(exc).__name__)
        return 1
    return 0
