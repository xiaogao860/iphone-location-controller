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
