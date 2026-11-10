import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication,QEvent
import shiboken6
from iphone_location.app import Window

def test_window_route_flow_without_phone():
    app=QApplication.instance() or QApplication([])
    w=Window()
    assert not w.connected
    assert not w.manual_button.isEnabled()
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
