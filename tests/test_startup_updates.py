import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import json,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
from PyQt6.QtCore import QObject,pyqtSignal,QSettings
from PyQt6.QtWidgets import QApplication,QDialog,QVBoxLayout,QPushButton,QLabel,QMessageBox
from ccdastro_siril import _updates as updates

class FakeWorker(QObject):
    completed=pyqtSignal(object,str)
    def __init__(self):super().__init__();self.running=False
    def start(self):self.running=True
    def isRunning(self):return self.running
    def reply(self,update=None,error=''):self.running=False;self.completed.emit(update,error)

class StartupUpdateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.settings=QSettings(str(Path(self.temp.name)/'settings.ini'),QSettings.Format.IniFormat)
        self.dialog=QDialog();layout=QVBoxLayout(self.dialog)
        self.dialog.update_button=QPushButton('Check for updates')
        self.dialog.status=QLabel('Processing image remains untouched')
        self.controller=updates.UpdateController(self.dialog,layout,settings=self.settings,worker_factory=FakeWorker,clock=lambda:200000)
        self.controller.timer.stop()
        self.new={'version':'99.0.0','url':updates.RELEASES_URL+'/tag/v99.0.0','prerelease':True}
    def tearDown(self):
        self.controller.shutdown();self.dialog.close();self.settings.sync();self.temp.cleanup()
    def test_default_daily_startup_notice_without_popup_or_processing_status_change(self):
        self.assertTrue(self.controller.auto.isChecked())
        with patch.object(QMessageBox,'question') as question,patch.object(QMessageBox,'information') as info:
            self.controller.startup();worker=self.controller.worker
            self.assertTrue(worker.isRunning());worker.reply(self.new)
            self.assertFalse(self.controller.notice.isHidden());self.assertIn('99.0.0',self.controller.notice.text())
            self.assertIn('development',self.controller.notice.text());question.assert_not_called();info.assert_not_called()
        self.assertEqual(self.dialog.status.text(),'Processing image remains untouched')
        self.controller.startup();self.assertIs(self.controller.worker,worker)
    def test_opt_out_persists_and_stops_timer(self):
        self.controller.auto.setChecked(False);self.controller.startup()
        self.assertIsNone(self.controller.worker);self.assertFalse(self.settings.value('updates/startupEnabled',True,type=bool))
        self.assertFalse(self.controller.timer.isActive())
    def test_manual_bypasses_daily_throttle_and_can_open_release(self):
        self.settings.setValue('updates/lastAttempt',199999)
        self.controller.startup();self.assertIsNone(self.controller.worker)
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes),patch.object(updates.QDesktopServices,'openUrl') as opened:
            self.controller.check(manual=True);self.controller.worker.reply(self.new)
            self.assertEqual(opened.call_args.args[0].toString(),self.new['url'])
    def test_cached_notice_without_network_and_upgraded_version_ignored(self):
        self.settings.setValue('updates/lastAttempt',199999);self.settings.setValue('updates/availableVersion','99.0.0')
        self.controller.startup();self.assertFalse(self.controller.notice.isHidden());self.assertIsNone(self.controller.worker)
        self.controller.notice.hide();self.settings.setValue('updates/availableVersion',updates.VERSION)
        self.controller.startup();self.assertTrue(self.controller.notice.isHidden())
    def test_failed_startup_quiet_and_no_new_version_clears_stale_notice(self):
        with patch.object(QMessageBox,'information') as info:
            self.controller.startup();self.controller.worker.reply(None,'offline');info.assert_not_called()
        self.assertTrue(self.dialog.update_button.isEnabled());self.assertTrue(self.controller.notice.isHidden())
        self.settings.setValue('updates/availableVersion','99.0.0');self.controller.show_update(self.new)
        self.controller.check(manual=False);self.controller.worker.reply(None)
        self.assertTrue(self.controller.notice.isHidden());self.assertFalse(self.settings.contains('updates/availableVersion'))
    def test_duplicate_request_close_and_late_reply(self):
        self.controller.startup();worker=self.controller.worker
        self.controller.check();self.assertIs(self.controller.worker,worker)
        self.controller.shutdown();self.dialog.close()
        with patch.object(QMessageBox,'question') as question:
            worker.reply(self.new);question.assert_not_called()
        self.assertTrue(self.controller.notice.isHidden());self.assertFalse(self.controller.timer.isActive())
    def test_turning_off_during_startup_ignores_result(self):
        self.controller.startup();worker=self.controller.worker
        self.controller.auto.setChecked(False);worker.reply(self.new)
        self.assertTrue(self.controller.notice.isHidden());self.assertTrue(self.dialog.update_button.isEnabled())
    def test_future_or_invalid_last_attempt_does_not_disable_checks(self):
        for value in ['invalid',300000]:
            self.controller.worker=None;self.settings.setValue('updates/lastAttempt',value)
            self.controller.startup();self.assertIsNotNone(self.controller.worker)
    def test_notification_link_requires_user_click(self):
        self.controller.startup()
        with patch.object(updates.QDesktopServices,'openUrl') as opened:
            self.controller.worker.reply(self.new);opened.assert_not_called()
            self.controller.notice.click();self.assertEqual(opened.call_args.args[0].toString(),self.new['url'])
    def test_worker_background_signal_and_daemon_lifecycle(self):
        release=threading.Event();started=threading.Event()
        class Response:
            def __enter__(self):started.set();release.wait(2);return self
            def __exit__(self,*args):pass
            def read(self,size):return json.dumps([{'tag_name':'v99.0.0'}]).encode()
        controller=self.controller;controller.worker_factory=updates.ReleaseCheck
        with patch.object(updates,'urlopen',return_value=Response()):
            controller.startup();self.assertTrue(started.wait(1));worker=controller.worker
            self.assertTrue(worker._network_thread.daemon);self.assertTrue(worker.isRunning())
            controller.shutdown();self.dialog.close();release.set();worker._network_thread.join(2)
            self.assertFalse(worker.isRunning());self.app.processEvents()
        self.assertTrue(controller.notice.isHidden())
    def test_background_success_reaches_gui(self):
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,size):return b'[{"tag_name":"v99.0.0"}]'
        self.controller.worker_factory=updates.ReleaseCheck
        with patch.object(updates,'urlopen',return_value=Response()):
            self.controller.startup();self.controller.worker._network_thread.join(2);self.app.processEvents()
        self.assertFalse(self.controller.notice.isHidden());self.assertTrue(self.dialog.update_button.isEnabled())
    def test_workflow_close_does_not_wait_for_check(self):
        import numpy as np
        from ccdastro_siril._ui import WorkflowDialog
        class Host:
            title='Siril'
            def read(self):return np.full((16,16,3),.02,dtype=np.float32),{}
        w=WorkflowDialog(Host());c=w.update_controller;c.timer.stop();c.settings=self.settings;c.worker_factory=FakeWorker
        w.show();self.app.processEvents()
        c.check(manual=False);self.assertTrue(c.worker.isRunning())
        w.close();self.assertTrue(c.closed);self.assertTrue(c.worker.isRunning())
        c.worker.reply(self.new);self.assertTrue(c.notice.isHidden())
