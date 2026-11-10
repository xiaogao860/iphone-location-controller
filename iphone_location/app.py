import json
import math
import sys
import time
from pathlib import Path
from PySide6.QtCore import QObject, Signal, Slot, QEvent, QProcess, QTimer, QUrl, Qt
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QLineEdit,QCheckBox,QComboBox,QInputDialog)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebChannel import QWebChannel
from .coordinates import gcj02_to_wgs84
from .motion import DEFAULT_CENTER, Route, track, validate, manual_step

class Bridge(QObject):
    selected=Signal(float,float)
    loaded=Signal()
    @Slot(float,float)
    def select(self,lat,lon): self.selected.emit(lat,lon)
    @Slot()
    def ready(self): self.loaded.emit()

class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('iPhone 定位控制器 · Windows 2.0')
        self.resize(1080,900)
        self.point=self.center=DEFAULT_CENTER
        self.route_points=[];self.engine=None;self.mode=None;self.keys=set()
        self.worker=None;self.connected=False;self.pending=False;self.closing=False
        self.stopping=False;self.map_ready=False;self.buffer='';self.worker_error=False;self.cleared=False
        self.last=time.monotonic();self.last_send=0.0;self.pending_since=0.0
        body=QWidget();root=QVBoxLayout(body);self.setCentralWidget(body)
        title=QLabel('iPhone 定位控制器');title.setStyleSheet('font-size:24px;font-weight:700');root.addWidget(title)
        root.addWidget(QLabel('W 北 / A 西 / S 南 / D 东 · 按住移动，松开停止 · 速度无上限'))
        self.web=QWebEngineView();self.web.setMinimumHeight(320);root.addWidget(self.web,1)
        self.bridge=Bridge();channel=QWebChannel(self.web.page());channel.registerObject('bridge',self.bridge);self.web.page().setWebChannel(channel)
        self.web.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,True)
        self.bridge.selected.connect(self.select_point);self.bridge.loaded.connect(self.map_loaded)
        self.web.load(QUrl.fromLocalFile(str(Path(__file__).parent/'assets'/'map.html')))
        row=self.row(root);self.map_mode=QComboBox();self.map_mode.addItems(['选择起点 / 跑道中心','绘制路线（第一次点击即首点）']);row.addWidget(self.map_mode)
        self.button(row,'返回默认操场',self.home);self.button(row,'撤销末点',self.undo);self.button(row,'清空路线',self.clear_route)
        self.info=QLabel('默认：北邮沙河操场中心附近 · 所有地图和发送坐标统一为 WGS-84');root.addWidget(self.info)
        row=self.row(root);self.length=QLineEdit('400');self.angle=QLineEdit('-15')
        for text,field in [('跑道周长(m)',self.length),('朝向(°)',self.angle)]:row.addWidget(QLabel(text));field.setMaximumWidth(100);row.addWidget(field)
        self.button(row,'一键生成跑道',self.generate);self.loop=QCheckBox('循环路线');row.addWidget(self.loop)
        row=self.row(root);self.lat=QLineEdit(f'{self.point[0]:.8f}');self.lon=QLineEdit(f'{self.point[1]:.8f}');self.speed=QLineEdit('5')
        for text,field in [('GPS 纬度',self.lat),('GPS 经度',self.lon),('速度(km/h)',self.speed)]:row.addWidget(QLabel(text));row.addWidget(field)
        row=self.row(root);self.button(row,'应用输入坐标',self.apply_fields);self.button(row,'导入 GCJ-02 坐标',self.import_gcj)
        self.connect_button=self.button(row,'连接手机',self.connect_phone)
        self.manual_button=self.button(row,'开始 WASD',self.manual)
        self.route_button=self.button(row,'开始路线跑步',self.run_route)
        self.restore_button=self.button(row,'恢复真实定位 / 断开',self.stop)
        self.route_label=QLabel('路线：未设置');root.addWidget(self.route_label)
        self.position_label=QLabel('尚未发送模拟位置');root.addWidget(self.position_label)
        self.status=QLabel('USB 连接并解锁 iPhone，开启开发者模式。首次连接请在手机点击信任。');self.status.setWordWrap(True);root.addWidget(self.status)
        self.timer=QTimer(self);self.timer.timeout.connect(self.tick);self.timer.start(250)
        QApplication.instance().installEventFilter(self);self.buttons()
    def row(self,root):
        row=QHBoxLayout();root.addLayout(row);return row
    def button(self,row,text,fn):
        b=QPushButton(text);b.clicked.connect(fn);row.addWidget(b);return b
    def buttons(self):
        self.connect_button.setEnabled(self.worker is None)
        self.manual_button.setEnabled(self.connected and not self.stopping and not self.closing)
        self.route_button.setEnabled(self.connected and not self.stopping and not self.closing and len(self.route_points)>=2)
        self.restore_button.setEnabled(self.worker is not None and not self.closing)
    def js(self,call,*args):
        if self.map_ready:self.web.page().runJavaScript('window.'+call+'('+','.join(json.dumps(a) for a in args)+');')
    def map_loaded(self):
        self.map_ready=True;self.js('setCenter',self.center);self.js('setRoute',self.route_points,False)
    def fields(self):self.lat.setText(f'{self.point[0]:.8f}');self.lon.setText(f'{self.point[1]:.8f}')
    def editable(self):
        if self.mode is not None:self.status.setText('请先恢复真实定位并断开，或结束当前控制后编辑路线。');return False
        return True
    def select_point(self,lat,lon):
        if not self.editable():return
        try:
            p=validate((lat,lon))
            if self.map_mode.currentIndex()==1:self.route_points.append(p);self.update_route()
            else:
                self.center=self.point=p;self.fields();self.js('setCenter',p);self.info.setText('起点 / 跑道中心：地图选点（WGS-84）')
        except ValueError as e:self.status.setText(str(e))
    def apply_fields(self):
        if not self.editable():return
        try:self.center=self.point=validate((self.lat.text(),self.lon.text()));self.fields();self.js('setCenter',self.point);self.js('goHome',self.point)
        except ValueError as e:self.status.setText(str(e))
    def import_gcj(self):
        if not self.editable():return
        text,ok=QInputDialog.getText(self,'导入高德 / 腾讯坐标','输入 GCJ-02 纬度,经度（不会再次自动转换地图点击）')
        if ok:
            try:
                p=validate(text.replace('，',',').split(','));self.center=self.point=gcj02_to_wgs84(*p)
                self.fields();self.js('setCenter',self.point);self.js('goHome',self.point)
                self.info.setText('已将 GCJ-02 输入转换为 GPS / WGS-84')
            except (ValueError,TypeError) as e:self.status.setText('坐标格式错误：'+str(e))
    def home(self):
        if self.editable():self.center=self.point=DEFAULT_CENTER;self.fields();self.js('setCenter',self.point);self.js('goHome',self.point)
    def update_route(self,fit=False):
        self.engine=None;self.js('setRoute',self.route_points,fit)
        try:length=Route(self.route_points).total
        except ValueError:length=0
        self.route_label.setText(f'路线：{len(self.route_points)} 个点 · {length:.1f} 米（按点直线连接）');self.buttons()
    def undo(self):
        if self.editable() and self.route_points:self.route_points.pop();self.update_route()
    def clear_route(self):
        if self.editable():self.route_points=[];self.update_route()
    def generate(self):
        if not self.editable():return
        try:
            self.route_points=track(self.center,float(self.length.text()),float(self.angle.text()));self.loop.setChecked(True);self.update_route(True)
            self.status.setText('闭合跑道已生成；点击开始路线跑步。调整中心、周长和角度可贴合场地。')
        except ValueError as e:self.status.setText(str(e))
    def velocity(self):
        s=float(self.speed.text())
        if not math.isfinite(s) or s<0:raise ValueError('速度须为有限非负数，无人为上限')
        return s
    def connect_phone(self):
        if self.worker:return
        self.worker_error=False;self.cleared=False;self.buffer='';self.closing=False;self.stopping=False
        self.worker=QProcess(self);self.worker.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        self.worker.readyReadStandardOutput.connect(self.read_output)
        self.worker.readyReadStandardError.connect(lambda:self.worker and self.worker.readAllStandardError())
        self.worker.finished.connect(self.finished)
        self.worker.errorOccurred.connect(self.process_error)
        if getattr(sys,'frozen',False):args=['--backend']
        else:args=[str(Path(__file__).resolve().parent.parent/'launcher.py'),'--backend']
        self.worker.start(sys.executable,args);self.status.setText('正在连接手机…');self.buttons()
        QTimer.singleShot(170000,self.connect_timeout)
    def connect_timeout(self):
        if self.worker and not self.connected and not self.closing:self.worker_error=True;self.status.setText('连接超时。请检查 Apple 驱动、信任及开发者模式，再点击恢复 / 断开。')
    def read_output(self):
        if not self.worker:return
        self.buffer+=bytes(self.worker.readAllStandardOutput()).decode('utf-8',errors='replace')
        while '\n' in self.buffer:
            line,self.buffer=self.buffer.split('\n',1)
            try:j=json.loads(line)
            except ValueError:continue
            event=j.get('event')
            if event=='ready':self.connected=True;self.status.setText('手机已连接，尚未修改定位。');self.buttons()
            elif event=='position':
                self.pending=False;p=(j['lat'],j['lon']);self.js('setPosition',p)
                self.position_label.setText(f'已发送 GPS / WGS-84：{p[0]:.8f}, {p[1]:.8f}')
            elif event=='cleared':self.cleared=True;self.status.setText('恢复真实定位指令已发送，请在手机地图确认。')
            elif event=='status':self.status.setText(j['message'])
            elif event=='error':self.worker_error=True;self.mode=None;self.keys.clear();self.status.setText(j['message'])
    def process_error(self,error):
        if self.worker:self.worker_error=True;self.status.setText('连接进程异常：'+self.worker.errorString())
        if error==QProcess.ProcessError.FailedToStart:self.finished()
    def send(self,cmd):
        if self.worker and self.worker.state()==QProcess.ProcessState.Running:
            self.worker.write((json.dumps(cmd)+'\n').encode());return True
        return False
    def manual(self):
        if not self.connected:return
        if self.mode=='manual':self.mode='manual_paused';self.keys.clear();self.manual_button.setText('继续 WASD');self.status.setText('已暂停移动，模拟位置保持。');return
        try:
            self.velocity()
            if self.mode is None:self.point=validate((self.lat.text(),self.lon.text()))
        except ValueError as e:self.status.setText(str(e));return
        self.mode='manual';self.engine=None;self.keys.clear();self.last=time.monotonic();self.last_send=0
        self.manual_button.setText('暂停 WASD');self.route_button.setText('开始路线跑步');self.speed.clearFocus();self.web.setFocus()
    def run_route(self):
        if not self.connected:return
        if self.mode=='route':self.mode='route_paused';self.route_button.setText('继续路线');self.status.setText('路线已暂停，模拟位置保持。');return
        try:
            if self.velocity()<=0:raise ValueError('路线跑步速度须大于零')
            if self.mode!='route_paused' or self.engine is None or self.engine.completed:
                self.engine=Route(self.route_points);self.point=self.route_points[0]
        except ValueError as e:self.status.setText(str(e));return
        self.mode='route';self.keys.clear();self.last=time.monotonic();self.last_send=0
        self.route_button.setText('暂停路线');self.manual_button.setText('开始 WASD');self.status.setText('沿路线移动中，切换窗口仍继续。')
        self.publish() # Send the exact first point before advancing.
    def publish(self):
        if self.pending:return
        self.pending=self.send(dict(action='set',lat=self.point[0],lon=self.point[1],coordinateSystem='wgs84'))
        self.pending_since=self.last_send=time.monotonic();self.fields()
    def tick(self):
        now=time.monotonic()
        if self.pending:
            if now-self.pending_since>12:self.mode=None;self.status.setText('手机未确认更新，已停止推进。请点击恢复 / 断开。')
            return
        dt=min(now-self.last,1);self.last=now
        if not self.connected or self.mode not in ('manual','route'):return
        try:
            speed=self.velocity()
            if self.mode=='route':
                self.point=self.engine.advance(speed/3.6*dt,self.loop.isChecked())
                self.route_label.setText(f'路线进度：{self.engine.progress:.1f} / {self.engine.total:.1f} 米')
                if self.engine.completed:self.mode='route_paused';self.route_button.setText('重新跑路线');self.status.setText('路线完成，停在终点。恢复请点击恢复按钮。')
                self.publish()
            else:
                if not self.isActiveWindow():self.keys.clear()
                n=int(Qt.Key.Key_W in self.keys)-int(Qt.Key.Key_S in self.keys);e=int(Qt.Key.Key_D in self.keys)-int(Qt.Key.Key_A in self.keys)
                self.point=manual_step(self.point,n,e,speed,dt)
                if n or e or now-self.last_send>=1:self.publish()
        except (ValueError,OverflowError) as e:self.mode=None;self.keys.clear();self.status.setText(str(e))
    def eventFilter(self,obj,event):
        if event.type() in (QEvent.Type.ApplicationDeactivate,QEvent.Type.WindowDeactivate):self.keys.clear()
        if event.type() in (QEvent.Type.KeyPress,QEvent.Type.KeyRelease):
            key=event.key()
            if key in (Qt.Key.Key_W,Qt.Key.Key_A,Qt.Key.Key_S,Qt.Key.Key_D):
                if event.type()==QEvent.Type.KeyRelease:self.keys.discard(key)
                elif self.mode=='manual' and self.isActiveWindow() and not isinstance(QApplication.focusWidget(),QLineEdit) and not event.modifiers() & (Qt.KeyboardModifier.ControlModifier|Qt.KeyboardModifier.AltModifier):self.keys.add(key);return True
                if self.mode=='manual' and not isinstance(QApplication.focusWidget(),QLineEdit):return True
        return super().eventFilter(obj,event)
    def stop(self):
        self.stopping=True;self.mode=None;self.keys.clear();self.status.setText('正在清除模拟位置…');self.send({'action':'stop'})
        self.manual_button.setEnabled(False);self.route_button.setEnabled(False)
    def finished(self,*_):
        worker=self.worker;self.worker=None;self.connected=False;self.pending=False;self.stopping=False;self.mode=None;self.keys.clear()
        if worker:worker.deleteLater()
        self.manual_button.setText('开始 WASD');self.route_button.setText('开始路线跑步');self.buttons()
        if not self.cleared and not self.worker_error:self.status.setText('连接已结束，恢复未获确认，请重连恢复或重启手机。')
        if self.closing:self.close()
    def closeEvent(self,event):
        if self.worker:
            event.ignore();self.closing=True;self.stop();self.buttons()
            self.status.setText('正在恢复真实定位并关闭，连接准备期间可能需要等待…')
        else:event.accept()

def main():
    app=QApplication(sys.argv);app.setApplicationName('iPhoneLocationController')
    window=Window();window.show()
    return app.exec()
