import sys
import threading
from urllib.request import urlopen
from bs4 import BeautifulSoup as BS
from pytube import YouTube
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
from licensing.methods import Key, Helpers
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, QGridLayout, QHBoxLayout, QVBoxLayout, QMessageBox , QSizePolicy
from PyQt5.QtCore import Qt, QUrl, QEvent, QSize, QThread, QLine
from PyQt5.QtGui import QIcon, QMovie, QPixmap, QPainter, QPen, QColor
from PyQt5.QtWebEngineWidgets import QWebEngineSettings, QWebEngineView
from PyQt5 import QtWidgets, QtCore
from superqt import QRangeSlider, QLabeledSlider
from PyQt5.QtWidgets import QFileDialog
import json
import html_to_json
import re


RSAPubKey = "<RSAKeyValue><Modulus>5KRqVeLbPIRjP331BuWcPuPNW5AofAGKw8hCtxk4D97pn4qVJ16QB2C48Sw5RA2CIslSX5D9Fk8jUNL2bwIXJ3aOeVxrBgXflZdBy7TGASBRPNa6Rok1zHle/mJwx/0J9SxCGKb929ZeZJW6WC2WaGbFowFpNqBzaei7BtYIQzEZxE4q2O1N4TycSN4WhZPZcMx4vUb7wJ/MvZ053ADEH/8+cxhFzpCrOu+63HH1ROKD0Wqak+2kzrcFKbevQmvqF9iGBLZmxg+0VRlLNOLyTqhwaDVTODPGbR6C4XY4pVFejn2vAHwz8RDFF5fxtlk4V9a/UWnUFZkN5hICCZVXDQ==</Modulus><Exponent>AQAB</Exponent></RSAKeyValue>"
auth = "WyIzNDc3NzI0MyIsInpkbmoxNFlFVHpmREVkVFE2V0xVcGFBL0JTZlJmSHhmWnd5cFhiVXEiXQ=="

__version__ = 'v1.0'
__author__ = ' Kevin'
download_Path = ''
youtubeVideoLength = None
youtubeVideoTitle = ''

class QPyTube(QtCore.QObject):
    initialized = QtCore.pyqtSignal(bool, str)
    download_started = QtCore.pyqtSignal()
    download_progress_changed = QtCore.pyqtSignal(int)
    download_finished = QtCore.pyqtSignal()

    def __init__(self, url):
        super().__init__()
        print('I have started running')
        self._url = url
        self._yt = None
        self._mutex = threading.Lock()
        threading.Thread(target=self._init, daemon=True).start()

    @property
    def url(self):
        return self._url

    def _init(self):
        try:
            self._yt = YouTube(
                self.url,
                on_progress_callback=self._on_progress,
                on_complete_callback=self._on_complete,
            )
            
            streams = self._yt.streams.filter(mime_type="video/mp4", progressive="True")
            
            
            global youtubeVideoTitle
            youtubeVideoTitle = streams[0].title
            
            global youtubeVideoLength 
            youtubeVideoLength = self._yt.length
            
            
        except Exception as e:
            self.initialized.emit(False, str(e))
            return
        self.initialized.emit(True, "")

    def download(self, resolution, directory):
        print('I have started downloading')
        threading.Thread(
            target=self._download, args=(resolution, directory), daemon=True
        ).start()

    def _download(self, resolution, directory):
        stream = self._yt.streams.filter(progressive=True).last()
        self.download_started.emit()
        stream.download(directory)

    def _on_progress(self, stream, chunk, bytes_remaining):
        print('progresando con la descarga')
        self.download_progress_changed.emit(
            100 * (stream.filesize - bytes_remaining) // stream.filesize
        )

    def _on_complete(self, stream, filepath):
        self.download_finished.emit()

class YouTubePlayer(QWidget):            
    file_path = ''
    mostViewedMoments = ''
    heatMapAverage = 0
    slider = ''
    buttonDirectory = None
    circle = None
    downloadingLabel = None
    numberOfClips = None
    youtubeLink = None
    clipList = []
    def __init__(self , video_id , parent=None):
        super().__init__()
        self.parent = parent
        self.video_id = video_id

        self.layout = QVBoxLayout()
        self.setLayout(self.layout )

        topLayout = QHBoxLayout()
        self.layout.addLayout(topLayout)
        
        label = QLabel ('Enter Video Id or URL : ')
        self.input = QLineEdit()
        self.input.installEventFilter(self)
        self.input.setText (self.video_id )
        

        
        buttonAddPlayer = QPushButton('&Update', clicked=self.updateVideo )
        
        topLayout.addWidget (label , 1)
        topLayout.addWidget (self.input , 9)
        topLayout.addWidget(buttonAddPlayer, 5)
        
        self.addInitialWebView(self.input.text())
        
        clipBarLayout = QHBoxLayout() 
        self.layout.addLayout(clipBarLayout)
        self.clipBar = QRangeSlider(Qt.Orientation.Horizontal)
        clipBarLayout.addWidget(self.clipBar)
        self.clipBar.show()
        
        self._qpytube = None
        
        buttonLayout = QHBoxLayout()
        secondButtonLayout = QHBoxLayout()
        
        layoutToSeparate = QHBoxLayout()
        lastButtonLayout = QHBoxLayout()
        self.layout.addLayout(buttonLayout)
        self.layout.addLayout(secondButtonLayout)
        self.layout.addLayout(layoutToSeparate)
        self.layout.addLayout(lastButtonLayout)
        
        layoutToSeparate.addWidget(QLabel(' ───────────────────────── ' ), alignment=Qt.AlignCenter  | Qt.AlignCenter )
        
        self.buttonDirectory = QPushButton('Select directory' , clicked=self.selectDirectory)
        self.buttonDirectory.setMaximumWidth(350)
        
        self.buttonDownload = QPushButton('Download')
        
        self.buttonDownload.clicked.connect(self.handle_download_clicked)
        self.buttonBestMoments = QPushButton('Get best moments' , clicked=self.getBestMoments)
        self.buttonMakeClips = QPushButton('Make clips', clicked = self.makeClips)
        
        self.buttonDirectory.setEnabled(True)
        self.buttonDownload.setEnabled(False)
        self.buttonBestMoments.setEnabled(False)
        self.buttonMakeClips.setEnabled(False)
        
        
        buttonLayout.addWidget(self.buttonDirectory)
        buttonLayout.addWidget(self.buttonDownload)
        
        
        self.labelGettingResources = QLabel('')
        self.labelGettingResources.setMaximumWidth(200)
        self.labelGettingResources.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        buttonLayout.addWidget(self.labelGettingResources)
        
        self.progressBarDownload = QtWidgets.QProgressBar()
        self.progressBarDownload.setMinimumWidth(200)
        self.progressBarDownload.setMaximumWidth(300)
        buttonLayout.addWidget(self.progressBarDownload)
        
        self.youtubeLink = 'https://www.youtube.com/watch?v=09wcDevb1q4'
        self._qpytube = QPyTube(self.youtubeLink)
        self._qpytube.download_progress_changed.connect(self.progressBarDownload.setValue)
        self._qpytube.download_started.connect(self.handle_download_started)
        self._qpytube.download_finished.connect(self.handle_download_finished)
        
        secondButtonLayout.addWidget(self.buttonBestMoments)
        self.buttonBestMoments.setMaximumWidth(300)
        self.slider = QtWidgets.QSlider(orientation=Qt.Vertical)
        self.slider.setRange(0, 100)
        self.slider.setSingleStep(1)
        self.slider.valueChanged.connect(self.onSliderValueChanged)
        self.slider.mouseReleaseEvent = self.slider_released
        self.slider.setEnabled(False)
        secondButtonLayout.addWidget(self.slider)
        
        self.numberOfClips = QLabel ('Number of clips \n will be')
        self.numberOfClips.setMaximumWidth(300)
        secondButtonLayout.addWidget(self.numberOfClips)
        
        labelOrDothis = QLabel(' ‎‎or make your own clips ' )

        labelOrDothis.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        secondButtonLayout.addWidget(labelOrDothis)
        
        self.buttonResetClipBar = QPushButton('Reset clip bar', clicked = self.resetClipBar)
        self.buttonResetClipBar.setMaximumWidth(250)
        secondButtonLayout.addWidget(self.buttonResetClipBar)       
        
        self.buttonAddClipToEnd = QPushButton('Add clip', clicked = self.AddClipEnd)
        self.buttonAddClipToEnd.setMaximumWidth(250)
        secondButtonLayout.addWidget(self.buttonAddClipToEnd)
        
        self.buttonRemoveClipFromEnd = QPushButton('Remove last clip', clicked = self.RemoveClipEnd)
        self.buttonRemoveClipFromEnd.setMaximumWidth(250)
        secondButtonLayout.addWidget(self.buttonRemoveClipFromEnd)
        
        self.buttonResetClipBar.setEnabled(False)
        self.buttonAddClipToEnd.setEnabled(False)
        self.buttonRemoveClipFromEnd.setEnabled(False)

        lastButtonLayout.addWidget(self.buttonMakeClips)
        self.buttonMakeClips.setMaximumWidth(300)
        
    def resetClipBar(self):
        self.clipList = []
        self.clipBar.setValue(((20,30)))
        
    def AddClipEnd(self):
        if (len(self.clipList) != 0):
            indexLastItem = len(self.clipList)-1
        else:
            indexLastItem = 0
        self.clipList.append(indexLastItem+1)
        self.clipList.append(indexLastItem+2)

             
        self.clipBar.setValue(self.clipList)
        
    def RemoveClipEnd(self):
        self.clipList.pop(len(self.clipList)-1)
        self.clipList.pop(len(self.clipList)-2)
        if(len(self.clipList)==0):
            self.buttonMakeClips.setEnabled(False)
        
        self.clipBar.setValue(self.clipList)
        
    def slider_released(self, event):
        self.updateClipBar()
        
    def handle_download_clicked(self):
        self.labelGettingResources.setText('Getting video resources')
        self._qpytube.download(
            '1080', self.file_path
        )
        self.input.setEnabled(False)
        
    def handle_download_started(self):
        self.progressBarDownload.setValue(0)

    def handle_download_finished(self):
        self.progressBarDownload.setValue(100)
        self.input.setEnabled(True)
        
        msgbox = QMessageBox()
        msgbox.setText('Video sucessfully downloaded')
        msgbox.exec_()
        
        self.buttonBestMoments.setEnabled(True)
        self.clipBar.show()
        self.buttonResetClipBar.setEnabled(True)
        self.buttonAddClipToEnd.setEnabled(True)
        self.buttonRemoveClipFromEnd.setEnabled(True)       
        
    def item_generator(self, json_input, lookup_key):
        if isinstance(json_input, dict):
            for k, v in json_input.items():
                if k == lookup_key:
                    yield v
                else:
                    yield from self.item_generator(v, lookup_key)
        elif isinstance(json_input, list):
            for item in json_input:
                yield from self.item_generator(item, lookup_key)
        
    def eventFilter(self, source, event):
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return:
                self.updateVideo()
        return super().eventFilter(source, event)
    

    def addInitialWebView(self, video_id):
        self.webview = QWebEngineView()
        self.webview.setUrl(QUrl(f'https://www.youtube.com/embed/{self.video_id}?rel=0'))
        self.layout.addWidget(self.webview)

    def updateVideo(self):
        self.resetData()
        
        video_Id = self.input.text()
        if '=' in video_Id:
            video_Id = video_Id.rsplit('=', 1)[1]
        self.webview.setUrl(QUrl(f'https://www.youtube.com/embed/{video_Id}?rel=0'))
        
        self.buttonDirectory.setEnabled(True)
        
        self.youtubeLink = f'https://www.youtube.com/watch?v={video_Id}'
        self._qpytube = QPyTube(self.youtubeLink)
        self._qpytube.download_progress_changed.connect(self.progressBarDownload.setValue)
        self._qpytube.download_started.connect(self.handle_download_started)
        self._qpytube.download_finished.connect(self.handle_download_finished)
        
        
    def resetData(self):
        self.file_path = ''
        self.mostViewedMoments = ''
        self.heatMapAverage = 0
        self.youtubeLink = None
        self.clipList = []
        self.clipBar.setValue((2,40))
        
        self.buttonDirectory.setEnabled(False)
        self.buttonDownload.setEnabled(False)
        self.buttonBestMoments.setEnabled(False)
        self.buttonMakeClips.setEnabled(False)
        self.slider.setEnabled(False)
        self.buttonResetClipBar.setEnabled(False)
        self.buttonAddClipToEnd.setEnabled(False)
        self.buttonRemoveClipFromEnd.setEnabled(False)
        self.labelGettingResources.setText('')        
        
        
    def selectDirectory(self):
        current_directory = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
        self.file_path = current_directory
        if current_directory != "":
            self.buttonDownload.setEnabled(True)
        
    def getBestMoments(self):
        url= self.youtubeLink
        result = urlopen(url)
        html = result.read()
        soup = BS(html, "html.parser")
        
        data = re.search(r"var ytInitialData = ({.*?});", soup.prettify()).group(1)
        data = json.loads(data)
        print('hasta aqui bien')
        
        self.mostViewedMoments = data['playerOverlays']['playerOverlayRenderer']['decoratedPlayerBarRenderer']['decoratedPlayerBarRenderer']['playerBar']['multiMarkersPlayerBarRenderer']['markersMap'][0]['value']['heatmap']['heatmapRenderer']['heatMarkers']
        
        for heatmap in self.mostViewedMoments:
            self.heatMapAverage += heatmap['heatMarkerRenderer']['heatMarkerIntensityScoreNormalized']
        self.heatMapAverage = self.heatMapAverage / len(self.mostViewedMoments)
        
        self.slider.setEnabled(True)
        self.numberOfClips.setText('Number of clips \n will be {}.'.format(self.countNumberOfClipsOnSliderValue()))
        self.buttonMakeClips.setEnabled(True)
        self.updateClipBar()
        
    def makeClips(self):
        with open('DEBUGGING.txt', 'a+') as f:
            f.writelines('hemos llamado a la funcion makeClips\n')
            f.close()
            
        required_video_file = self.file_path+'/' + youtubeVideoTitle+'.mp4'
        
        with open('DEBUGGING.txt', 'a+') as f:
            f.writelines('hemos construido la cadena file\n')
            f.close()

        i = 0
        while(i<len(self.clipList)):
            
            with open('DEBUGGING.txt', 'a+') as f:
                f.writelines('hemos entrado en el bucle con i: '+str(i)+'\n')
                f.close()
            
            with open('DEBUGGING.txt', 'a+') as f:
                f.writelines('i e i+1 son : '+str(self.clipList[i])+' '+str(self.clipList[i+1])+'\n')
                f.close()
                
            clipStart = self.clipList[i] * youtubeVideoLength / 100
            clipEnd = self.clipList[i+1] * youtubeVideoLength / 100
                        
            with open('DEBUGGING.txt', 'a+') as f:
                f.writelines('clipStart = '+str(clipStart)+' clipEnd = '+str(clipEnd)+'\n')
                f.close()

            try:
                ffmpeg_extract_subclip(required_video_file, clipStart , clipEnd, targetname=self.file_path+'/'+(str(round(i/2+1)))+".mp4")
            except Exception as e:                    
                with open('DEBUGGING.txt', 'a+') as f:
                    f.writelines('EXCEPCION: '+str(e))
                    f.close()
                
            i=i+2 # go to the next pair
    
    def countNumberOfClipsOnSliderValue(self):
        hardness = self.slider.sliderPosition()/100
        numberOfClips=0
        
        i = 0
        while(i<len(self.mostViewedMoments)):
            clip = self.mostViewedMoments[i]
            if(clip['heatMarkerRenderer']['heatMarkerIntensityScoreNormalized'] > (self.heatMapAverage + hardness)):
                k = 1
                while(self.mostViewedMoments[i+k]['heatMarkerRenderer']['heatMarkerIntensityScoreNormalized']> (self.heatMapAverage + hardness)):
                    k=k+1
                i=i+k
                numberOfClips = numberOfClips + 1
                continue
            else:
                i=i+1
        return numberOfClips
    
    def onSliderValueChanged(self):
        self.numberOfClips.setText('Number of clips \n will be {}.'.format(self.countNumberOfClipsOnSliderValue()))
        pass
    
    def updateClipBar(self):
        hardness = self.slider.sliderPosition()/100
        
        i = 0
        self.clipList = []
        self.clipBar.setValue(self.clipList)
        
        while(i<len(self.mostViewedMoments)):
            clip = self.mostViewedMoments[i]
            if(clip['heatMarkerRenderer']['heatMarkerIntensityScoreNormalized'] > (self.heatMapAverage + hardness)):
                start = clip['heatMarkerRenderer']['timeRangeStartMillis']/1000
                end = (clip['heatMarkerRenderer']['timeRangeStartMillis'] + clip['heatMarkerRenderer']['markerDurationMillis'])//1000
                k = 1
                while(self.mostViewedMoments[i+k]['heatMarkerRenderer']['heatMarkerIntensityScoreNormalized']> (self.heatMapAverage + hardness)):
                    end += self.mostViewedMoments[i+k]['heatMarkerRenderer']['markerDurationMillis']/1000
                    k=k+1
                i=i+k
                self.clipList.append(round(start/youtubeVideoLength*100))
                self.clipList.append(round(end/youtubeVideoLength*100))
                continue
            else:
                i=i+1
        self.clipBar.setValue(self.clipList)
        return 
        
        
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('YouTube Video Player')
        self.setWindowIcon(QIcon('logo.png'))
        self.setMinimumSize(1500, 600)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        self.player = YouTubePlayer('09wcDevb1q4', parent = self);
        self.layout.addWidget(self.player)
        
        self.layout.addWidget(QLabel(__version__ + __author__ ), alignment=Qt.AlignBottom | Qt.AlignRight)
    

if __name__ == '__main__':
    with open("license.txt") as f:
        licenseText = f.readline()
        print(licenseText)
        result = Key.activate(token=auth, rsa_pub_key=RSAPubKey,product_id=18372, key=licenseText, machine_code=Helpers.GetMachineCode(v=2))

        if result[0] == None or not Helpers.IsOnRightMachine(result[0], v=2):
            app = QApplication(sys.argv)
            
            window = MainWindow()
            window.show()
            
            message_box = QMessageBox()
            message_box.setText("The license is not valid. Click OK to close the application.")
            message_box.setStandardButtons(QMessageBox.Ok)
            message_box.exec_()
            
            window.close()
            sys.exit(app.exec_())
            
        else:
            app = QApplication(sys.argv)
            window = MainWindow()
            window.show()
            try:
                sys.exit(app.exec_())
            except SystemExit:
                print('Player Window Closed')
