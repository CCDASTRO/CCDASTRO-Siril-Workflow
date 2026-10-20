"""User-requested release checks. Never downloads or executes update code."""
import json,re
from urllib.request import Request,urlopen
from PyQt6.QtCore import QThread,pyqtSignal,QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QMessageBox
from ._core import VERSION

REPOSITORY = 'CCDASTRO/CCDASTRO-Siril-Workflow'
RELEASES_URL = 'https://github.com/'+REPOSITORY+'/releases'
API_URL = 'https://api.github.com/repos/'+REPOSITORY+'/releases?per_page=20'

def version_tuple(tag):
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

class ReleaseCheck(QThread):
    completed=pyqtSignal(object,str)
    def run(self):
        try:
            request=Request(API_URL,headers={'Accept':'application/vnd.github+json','User-Agent':'CCDASTRO-Workflow/'+VERSION})
            with urlopen(request,timeout=12) as response:
                raw=response.read(1024*1024+1)
            if len(raw)>1024*1024:raise ValueError('Release response too large.')
            self.completed.emit(select_update(json.loads(raw)), '')
        except Exception as error:self.completed.emit(None,str(error))

def check_for_updates(dialog):
    if getattr(dialog,'release_check',None) is not None and dialog.release_check.isRunning():return
    worker=ReleaseCheck(dialog);dialog.release_check=worker
    dialog.update_button.setEnabled(False)
    dialog.status.setText('Checking GitHub releases…')
    def finished(update,error):
        dialog.update_button.setEnabled(True)
        if error:
            dialog.status.setText('Update check unavailable. You can try again later.')
            QMessageBox.information(dialog,'Check for updates','Could not check GitHub releases.\n'+error+'\n\nRelease page: '+RELEASES_URL)
        elif update:
            label='development release' if update['prerelease'] else 'release'
            answer=QMessageBox.question(dialog,'Workflow update available',
                f"Version {update['version']} ({label}) is available. Installed: {VERSION}.\n\nOpen its release page? Download the Windows installer, close the host application, then run the installer to update. Your saved images and personal presets stay where you saved them.")
            if answer==QMessageBox.StandardButton.Yes:QDesktopServices.openUrl(QUrl(update['url']))
            dialog.status.setText('New version available: '+update['version'])
        else:
            dialog.status.setText('No newer published version is available.')
            QMessageBox.information(dialog,'Check for updates',f'Installed version: {VERSION}. No newer published version is available.')
    worker.completed.connect(finished);worker.start()
