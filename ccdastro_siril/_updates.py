"""Optional daily startup notices and manual release checks; no automatic installation."""
import json,re,threading,time
from urllib.request import Request,urlopen
from PyQt6.QtCore import QObject,pyqtSignal,pyqtSlot,QUrl,QSettings,QTimer
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QMessageBox,QCheckBox,QPushButton,QHBoxLayout
from ._core import VERSION

REPOSITORY = 'CCDASTRO/CCDASTRO-Siril-Workflow'
RELEASES_URL = 'https://github.com/'+REPOSITORY+'/releases'
API_URL = 'https://api.github.com/repos/'+REPOSITORY+'/releases?per_page=20'

def version_tuple(tag):
    if not isinstance(tag,str):return None
    match=re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)',tag)
    return tuple(map(int,match.groups())) if match else None

def select_update(releases,current=VERSION):
    current_number=version_tuple(current)
    if current_number is None:raise ValueError('Invalid installed version.')
    if not isinstance(releases,list):raise ValueError('Unexpected release response.')
    choices=[]
    for release in releases:
        if not isinstance(release,dict) or release.get('draft'):continue
        number=version_tuple(release.get('tag_name',''))
        if number is not None and number>current_number:
            choices.append((number,release))
    if not choices:return None
    _,release=max(choices,key=lambda pair:pair[0])
    # Build the URL ourselves from a validated version, never from remote links.
    return {'version':release['tag_name'].lstrip('v'),
            'url':RELEASES_URL+'/tag/v'+release['tag_name'].lstrip('v'),
            'prerelease':bool(release.get('prerelease'))}

SETTINGS_APP = 'SirilWorkflow'

class ReleaseCheck(QObject):
    completed=pyqtSignal(object,str)
    def __init__(self):
        super().__init__();self._network_thread=None
    def isRunning(self):return self._network_thread is not None and self._network_thread.is_alive()
    def start(self):
        if self.isRunning():return
        self._network_thread=threading.Thread(target=self.run,daemon=True,name='CCDASTRO release check');self._network_thread.start()
    def run(self):
        update=None;error=''
        try:
            request=Request(API_URL,headers={'Accept':'application/vnd.github+json','User-Agent':'CCDASTRO-Workflow/'+VERSION})
            with urlopen(request,timeout=12) as response:
                raw=response.read(1024*1024+1)
            if len(raw)>1024*1024:raise ValueError('Release response too large.')
            update=select_update(json.loads(raw))
        except Exception as exception:error=str(exception)
        try:self.completed.emit(update,error)
        except RuntimeError:pass  # Application already exited; ignore a late network reply.


# Network work uses a daemon thread: closing a workflow never waits for GitHub.
# Qt signals deliver results to the GUI thread; no image or processing state is touched.
class UpdateController(QObject):
    def __init__(self, dialog, layout, settings=None, worker_factory=ReleaseCheck, clock=time.time):
        super().__init__(dialog)
        self.dialog = dialog
        self.settings = settings if settings is not None else QSettings('CCDASTRO', SETTINGS_APP)
        self.worker_factory = worker_factory
        self.clock = clock
        self.worker = None
        self.closed = False
        self.manual = False
        self.available = None
        self.auto = QCheckBox('Check for updates at startup')
        self.auto.setToolTip('Contacts this workflow’s GitHub releases at most once every 24 hours. Updates are downloaded and installed only when you choose.')
        self.auto.setChecked(self.settings.value('updates/startupEnabled', True, type=bool))
        row = QHBoxLayout()
        row.addWidget(self.auto)
        row.addWidget(dialog.update_button)
        self.notice = QPushButton()
        self.notice.hide()
        self.notice.clicked.connect(self.open_release)
        row.addWidget(self.notice)
        row.addStretch()
        layout.addLayout(row)
        self.auto.toggled.connect(self.toggle_auto)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.startup)
        self.timer.start(1000)

    def toggle_auto(self, enabled):
        self.settings.setValue('updates/startupEnabled', bool(enabled))
        self.timer.stop()
        if enabled:
            self.startup()
        elif not self.manual:
            self.notice.hide()

    def startup(self):
        if self.closed or not self.auto.isChecked(): return
        cached = self.settings.value('updates/availableVersion', '', type=str)
        if version_tuple(cached) is not None and version_tuple(cached) > version_tuple(VERSION):
            self.show_update({'version': cached, 'url': RELEASES_URL+'/tag/v'+cached,
                'prerelease': self.settings.value('updates/availablePrerelease', False, type=bool)})
        try: last = float(self.settings.value('updates/lastAttempt', 0))
        except (TypeError, ValueError): last = 0
        elapsed = self.clock()-last
        if last > 0 and 0 <= elapsed < 24*60*60: return
        self.check(manual=False)

    def show_update(self, update):
        self.available = update
        label = ' (development)' if update['prerelease'] else ''
        self.notice.setText('Update available: v'+update['version']+label+' — Downloads')
        self.notice.show()

    def open_release(self):
        if self.available: QDesktopServices.openUrl(QUrl(self.available['url']))

    def check(self, manual=True):
        if self.closed or (self.worker is not None and self.worker.isRunning()): return
        self.manual = manual
        self.settings.setValue('updates/lastAttempt', self.clock())
        self.dialog.update_button.setEnabled(False)
        self.dialog.update_button.setText('Checking for updates…')
        self.worker = self.worker_factory()
        self.dialog.release_check = self.worker
        self.worker.completed.connect(self.finished)
        self.worker.start()

    @pyqtSlot(object, str)
    def finished(self, update, error):
        if self.closed or self.sender() is not self.worker: return
        self.dialog.update_button.setEnabled(True)
        self.dialog.update_button.setText('Check for updates')
        if not self.manual and not self.auto.isChecked(): return
        if error:
            if self.manual:
                QMessageBox.information(self.dialog, 'Check for updates',
                    'Could not check GitHub releases.\n'+error+'\n\nRelease page: '+RELEASES_URL)
            return
        if update:
            self.settings.setValue('updates/availableVersion', update['version'])
            self.settings.setValue('updates/availablePrerelease', update['prerelease'])
            self.show_update(update)
            if self.manual:
                label = 'development release' if update['prerelease'] else 'release'
                answer = QMessageBox.question(self.dialog, 'Workflow update available',
                    f"Version {update['version']} ({label}) is available. Installed: {VERSION}.\n\nOpen its release page? Download the Windows installer, close the host application, then run the installer to update. Your saved images and personal presets stay where you saved them.")
                if answer == QMessageBox.StandardButton.Yes: self.open_release()
        else:
            self.available = None
            self.notice.hide()
            self.settings.remove('updates/availableVersion')
            self.settings.remove('updates/availablePrerelease')
            if self.manual:
                QMessageBox.information(self.dialog, 'Check for updates',
                    f'Installed version: {VERSION}. No newer published version is available.')

    def shutdown(self):
        self.closed = True
        self.timer.stop()


def install_update_controls(dialog, layout, **kwargs):
    dialog.update_controller = UpdateController(dialog, layout, **kwargs)


def check_for_updates(dialog):
    dialog.update_controller.check(manual=True)
