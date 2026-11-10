import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS','--disable-gpu')
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication,QEvent,Qt
from PySide6.QtTest import QTest
import shiboken6
from iphone_location.app import Window

def test_window_route_flow_without_phone():
    app=QApplication.instance() or QApplication([])
    w=Window()
    w.show()
    for _ in range(100):
        app.processEvents();QTest.qWait(20)
        if w.map_ready:break
    assert w.map_ready, "Leaflet and QWebChannel must actually initialize"
    assert not w.connected
    assert not w.manual_button.isEnabled()
    QTest.keyPress(w.pad,Qt.Key.Key_W);assert Qt.Key.Key_W in w.keys
    QTest.keyRelease(w.pad,Qt.Key.Key_W);assert not w.keys
    w.generate()
    assert len(w.route_points)==145 and w.loop.isChecked()
    w.clear_route()
    w.map_mode.setCurrentIndex(1)
    w.select_point(40,116)
    assert w.route_points==[(40,116)] # No implicit Mac/default first point.
    w.select_point(40.001,116)
    assert len(w.route_points)==2
    w.undo();assert len(w.route_points)==1
    w.web.stop();w.close();shiboken6.delete(w);QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()

def _dispose(app,w):
    w.worker=None
    w.web.stop();w.close();shiboken6.delete(w);QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()

def test_stale_connect_timeout_ignores_newer_worker():
    app=QApplication.instance() or QApplication([])
    w=Window()
    old,new=object(),object()
    w.worker=new
    w.connect_timeout(old) # Timer armed by an earlier, finished attempt.
    assert not w.worker_error
    w.connect_timeout(new)
    assert w.worker_error and '连接超时' in w.status.text()
    _dispose(app,w)

def test_ack_timeout_pauses_route_and_allows_resume():
    import time
    app=QApplication.instance() or QApplication([])
    w=Window()
    w.generate();w.connected=True;w.speed.setText('10')
    w.run_route() # No worker: send() fails, so nothing stays pending.
    w.engine.advance(50)
    w.mode='route';w.pending=True;w.pending_since=time.monotonic()-13
    w.tick()
    assert not w.pending and w.mode=='route_paused'
    assert w.route_button.text()=='继续路线' and '12 秒' in w.status.text()
    w.tick() # Paused: does not advance or re-trigger.
    assert w.engine.progress==50
    w.run_route()
    assert w.mode=='route' and w.engine.progress==50 # Resumes instead of restarting.
    w.mode='manual';w.pending=True;w.pending_since=time.monotonic()-13
    w.tick()
    assert w.mode=='manual_paused' and w.manual_button.text()=='继续 WASD'
    _dispose(app,w)

def test_search_result_becomes_start_and_track_center():
    app=QApplication.instance() or QApplication([])
    w=Window()
    w.place(31.2304,121.4737,'某地')
    assert w.center==w.point==(31.2304,121.4737)
    assert w.lat.text()=='31.23040000' and '某地' in w.info.text()
    w.generate();assert len(w.route_points)==145
    w.mode='route' # 控制中不允许改起点
    w.place(0,0);assert w.center==(31.2304,121.4737)
    w.mode=None
    _dispose(app,w)
