import sys
import threading
from functools import cached_property
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, QGridLayout, QHBoxLayout, QVBoxLayout, QMessageBox , QSizePolicy
from PyQt5.QtCore import Qt, QUrl, QEvent, QSize, QThread, QLine
from PyQt5.QtGui import QIcon, QMovie, QPixmap, QPainter, QPen, QColor
from PyQt5 import QtWidgets, QtCore, QtGui
from superqt import QRangeSlider, QLabeledSlider
# pip install PyQtWebEngine
from PyQt5.QtWebEngineWidgets import QWebEngineSettings, QWebEngineView
from bs4 import BeautifulSoup as BS
from tkinter import messagebox, filedialog
import os
os.environ["IMAGEIO_FFMPEG_EXE"] = "C:/ffmpeg/bin/ffmpeg"
from pytube import YouTube
import requests
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

import json
import html_to_json
import re

__version__ = 'v1.1'
__author__ = ' Jie'
download_Path = ''

'''
Structure of the json:
[
    {
        "heatMarkerRenderer": {
            "timeRangeStartMillis": 0,
            "markerDurationMillis": 5950,
            "heatMarkerIntensityScoreNormalized": 0.6002911264243852
        }
    },
'''
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
 
youtubeVideoLength = None
youtubeVideoTitle = ''

class DownloadVideoThread(QThread):
    def __init__(self, video_url, file_path, parent=None):
        super(DownloadVideoThread, self).__init__(parent)
        self.video_url = video_url
        self.file_path = file_path
        
    def run(self):
        videoStream = self.video_url.streams.filter(file_extension='mp4').first()
        videoStream.download(self.file_path)
        # Perform the long running task here
        
        
class QPyTube(QtCore.QObject):
    initialized = QtCore.pyqtSignal(bool, str)
    download_started = QtCore.pyqtSignal()
    download_progress_changed = QtCore.pyqtSignal(int)
    download_finished = QtCore.pyqtSignal()

    def __init__(self, url):
        super().__init__()
        self._url = url
        self._yt = None
        self._mutex = threading.Lock()

        threading.Thread(target=self._init, daemon=True).start()

    @property
    def url(self):
        return self._url

    @cached_property
    def resolutions(self):
        return list()

    def _init(self):
        with self._mutex:
            self.resolutions.clear()
        try:
            self._yt = YouTube(
                self.url,
                on_progress_callback=self._on_progress,
                on_complete_callback=self._on_complete,
            )
            streams = self._yt.streams.filter(mime_type="video/mp4", progressive="True")
            global youtubeVideoLength 
            youtubeVideoLength = self._yt.length
            global youtubeVideoTitle 
            youtubeVideoTitle = streams[0].title
            print(streams[0].title)
            print('xd')
            print(youtubeVideoTitle)
        except Exception as e:
            self.initialized.emit(False, str(e))
            return
        with self._mutex:
            self.resolutions = [stream.resolution for stream in streams]
        self.initialized.emit(True, "")

    def download(self, resolution, directory):
        threading.Thread(
            target=self._download, args=(resolution, directory), daemon=True
        ).start()

    def _download(self, resolution, directory):
        stream = self._yt.streams.filter(progressive=True).last()
        self.download_started.emit()
        stream.download(directory)

    def _on_progress(self, stream, chunk, bytes_remaining):
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
        self.clipBar.setValue((11, 33, 66, 88))
        clipBarLayout.addWidget(self.clipBar)
        self.clipBar.hide()
        #self.clipBar.setStyleSheet("QRangeSlider::handle:horizontal {background-color: #FF0000;}");
        
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
        self.buttonDownload = QPushButton('Download')
        self.buttonDownload.clicked.connect(self.handle_download_clicked)
        self.buttonBestMoments = QPushButton('Get best moments' , clicked=self.getBestMoments)
        self.buttonMakeClips = QPushButton('Make clips', clicked = self.makeClips)
        
        self.buttonDirectory.setEnabled(False)
        self.buttonDownload.setEnabled(False)
        self.buttonBestMoments.setEnabled(False)
        self.buttonMakeClips.setEnabled(False)
        
        
        buttonLayout.addWidget(self.buttonDirectory)
        buttonLayout.addWidget(self.buttonDownload)
        
        
        self.cmb_resolutions = QtWidgets.QComboBox()
        self.progressBarDownload = QtWidgets.QProgressBar()
        self.progressBarDownload.setMaximumWidth(300)
        buttonLayout.addWidget(self.progressBarDownload)
        
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
        #labelOrDothis.setMinimumWidth(400)
        #labelOrDothis.setMaximumWidth(500)
        labelOrDothis.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        secondButtonLayout.addWidget(labelOrDothis)
        
        #Or make your own clips
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

        
        #no sé si borrarlo
        self._qpytube = QPyTube('https://www.youtube.com/watch?v=09wcDevb1q4')
        self._qpytube.initialized.connect(self.handle_initialized)
        self._qpytube.download_progress_changed.connect(self.progressBarDownload.setValue)
        self._qpytube.download_started.connect(self.handle_download_started)
        self._qpytube.download_finished.connect(self.handle_download_finished)
        
    def resetClipBar(self):
        self.clipList = []
        self.clipBar.setValue(self.clipList)
        
    def AddClipEnd(self):
        lenghtOfListBefore = len(self.clipList)
        if (len(self.clipList) != 0):
            indexLastItem = len(self.clipList)-1
        else:
            indexLastItem = 0
        self.clipList.append(indexLastItem+1)
        self.clipList.append(indexLastItem+2)
            
        #if(lenghtOfListBefore+2 != len(self.clipList)): #Couldn't be added on the last index
            #for i in range(100):
             #   if 
             
        self.clipBar.setValue(self.clipList)
        
    def RemoveClipEnd(self):
        self.clipList.pop(len(self.clipList)-1)
        self.clipList.pop(len(self.clipList)-2)
        if(len(self.clipList)==0):
            self.buttonMakeClips.setEnabled(False)
        
        self.clipBar.setValue(self.clipList)
        
    def slider_released(self, event):
        self.updateClipBar()
        print("Slider was released!")

        
    @QtCore.pyqtSlot(bool, str)
    def handle_initialized(self, status, error=""):
        if status:
            self.cmb_resolutions.addItems(self._qpytube.resolutions)

    def handle_download_clicked(self):
        self._qpytube.download(
            '1080', self.file_path
        )
        self.input.setEnabled(False)
        
    def handle_download_started(self):
        print("started")

    def handle_download_finished(self):
        self.progressBarDownload.setValue(100)
        self.input.setEnabled(True)
        
        msgbox = QMessageBox()
        msgbox.setText('video sucessfully downloaded in file')
        msgbox.exec_()
        self.buttonBestMoments.setEnabled(True)
        self.clipBar.show()
        self.buttonResetClipBar.setEnabled(True)
        self.buttonAddClipToEnd.setEnabled(True)
        self.buttonRemoveClipFromEnd.setEnabled(True)
        print("finished")        
        
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
        print(video_Id)
        self.webview.setUrl(QUrl(f'https://www.youtube.com/embed/{video_Id}?rel=0'))
        
        self.buttonDirectory.setEnabled(True)
        
        self.youtubeLink = f'https://www.youtube.com/watch?v={video_Id}'
        self._qpytube = QPyTube(self.youtubeLink)
        self._qpytube.initialized.connect(self.handle_initialized)
        self._qpytube.download_progress_changed.connect(self.progressBarDownload.setValue)
        self._qpytube.download_started.connect(self.handle_download_started)
        self._qpytube.download_finished.connect(self.handle_download_finished)
        
        
    def selectDirectory(self):
        current_directory = filedialog.askdirectory()
        self.file_path = current_directory+'/' + youtubeVideoTitle
        print('hey ' + current_directory)
        if current_directory != "":
            self.buttonDownload.setEnabled(True)
            
        #code for the download progress 
        
    def downloadVideo(self):    
        #animationThread = AnimationThread(self.circle)
        #animationThread.start()
        self.circle.start()
        self.downloadingLabel.setText("DOWNLOADING")
        self.downloadingLabel.repaint()
        
        #animationThread = AnimationThread(self.circle)
        #animationThread.start()
        
    	#download_Folder = download_Path.get()
        getVideo = YouTube(self.youtubeLink)
        
        #downloadThread = DownloadVideoThread(getVideo, self.file_path)
        #downloadThread.start()
        
    	# Getting all the available streams of the youtube video and selecting the mp4 stream
        #videoStream = getVideo.streams.filter(file_extension='mp4').first()
        #videoStream.download(self.file_path)
    
        #messagebox.showinfo("SUCCESSFULLY " + self.file_path)
        #animationThread.stop()
        
    def resetData(self):
        self.file_path = ''
        self.mostViewedMoments = ''
        self.heatMapAverage = 0
        self.youtubeLink = None
        self.clipList = []
        self.clipBar.setValue(())
        
        self.buttonDirectory.setEnabled(False)
        self.buttonDownload.setEnabled(False)
        self.buttonBestMoments.setEnabled(False)
        self.buttonMakeClips.setEnabled(False)
        self.slider.setEnabled(False)
        self.buttonResetClipBar.setEnabled(False)
        self.buttonAddClipToEnd.setEnabled(False)
        self.buttonRemoveClipFromEnd.setEnabled(False)
        
    
    def organizeLayout(self):
        playerCount = self.parent
        # self.organizeLayout()
    def organizeLayout(self):
        playerCount = self.parent.videoGrid.count()
        players = []
        for i in reversed(range(playerCount)):
            player = self.parent.videoGrid.itemAt(i).widget()
            players.append(player)
            for indx, player in enumerate(players[::-1]):
                self.parent.videoGrid.addWidget(player, indx % 3, indx // 3)
                
    def getBestMoments(self):
        url= self.youtubeLink
        soup = BS(requests.get(url).text, "html.parser")
        
        # We locate the JSON data using a regular-expression pattern
        data = re.search(r"var ytInitialData = ({.*?});", soup.prettify()).group(1)
        data = json.loads(data)
        
        self.mostViewedMoments = data['playerOverlays']['playerOverlayRenderer']['decoratedPlayerBarRenderer']['decoratedPlayerBarRenderer']['playerBar']['multiMarkersPlayerBarRenderer']['markersMap'][0]['value']['heatmap']['heatmapRenderer']['heatMarkers']
        print(self.mostViewedMoments)
        
        
        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(self.mostViewedMoments, f, ensure_ascii=False, indent=4)
            
        for heatmap in self.mostViewedMoments:
            self.heatMapAverage += heatmap['heatMarkerRenderer']['heatMarkerIntensityScoreNormalized']
        self.heatMapAverage = self.heatMapAverage / len(self.mostViewedMoments)
        
        self.slider.setEnabled(True)
        print('hey' + str(self.heatMapAverage))
        print('valor del slider'+str(self.slider.sliderPosition()))
        self.numberOfClips.setText('Number of clips \n will be {}.'.format(self.countNumberOfClipsOnSliderValue()))
        self.buttonMakeClips.setEnabled(True)
        self.updateClipBar()
        
    def makeClips(self):
        required_video_file = self.file_path+'/' + youtubeVideoTitle+'.mp4' 
        os.startfile(required_video_file)
        print(required_video_file)
        hardness = self.slider.sliderPosition()/100
        
        i = 0
        while(i<len(self.clipList)):
            clipStart = self.clipList[i] * youtubeVideoLength / 100
            clipEnd = self.clipList[i+1] * youtubeVideoLength / 100
            ffmpeg_extract_subclip(required_video_file, clipStart , clipEnd, targetname=self.file_path+'/'+(str(round(i/2+1)))+".mp4")                    
            i=i+2 # go to the next pair
    
    def countNumberOfClipsOnSliderValue(self):
        required_video_file = self.file_path+ "video clipped.mp4"
        hardness = self.slider.sliderPosition()/100
        numberOfClips=0
        
        i = 0
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
                numberOfClips = numberOfClips + 1
                continue
            else:
                i=i+1
        return numberOfClips
    
    def onSliderValueChanged(self):
        self.numberOfClips.setText('Number of clips \n will be {}.'.format(self.countNumberOfClipsOnSliderValue()))
        pass
    
    def updateClipBar(self):
        required_video_file = self.file_path+ "video clipped.mp4"
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
        print(self.clipList)
        print(type(self.clipList))
        self.clipBar.setValue(self.clipList)
        return 
        
        
class YouTubeWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('YouTube Video Player')
        self.setWindowIcon(QIcon('logo.png'))
        self.setMinimumSize(1500, 600)
        self.players = []

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)


        self.videoGrid = QGridLayout()
        self.layout.addLayout(self.videoGrid)
        
        self.player = YouTubePlayer('09wcDevb1q4', parent = self);
        self.videoGrid.addWidget(self.player, 0, 0)
        

        self.layout.addWidget(QLabel(__version__ + ' by kevin' ), alignment=Qt.AlignBottom | Qt.AlignRight)
    

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = YouTubeWindow()
    window.show()
    try:
        sys.exit(app.exec_())
    except SystemExit:
        print('Player Window Closed')
        