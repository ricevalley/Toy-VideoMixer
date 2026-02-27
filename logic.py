import ctypes
from datetime import datetime, timezone, timedelta
from fractions import Fraction
import glob
import json
from operator import itemgetter
import os
from pathlib import Path
import re
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog
from typing import Annotated, Literal

import eel
from pydantic import BaseModel, Field, ValidationError, StrictBool, validate_call

CREATE_NO_WINDOW = 0x08000000

videoList = Annotated[str, Field(pattern=r'\.mp4$')]
presetList = Literal[
    'ultrafast',
    'superfast',
    'veryfast',
    'faster',
    'fast',
    'medium',
    'slow',
    'slower',
    'veryslow',
    'placebo',
    'p1',
    'p2',
    'p3',
    'p4',
    'p5',
    'p6',
    'p7',
    'balanced',
    'speed',
    'quality'
]

class UserSettings(BaseModel):
    inputVideo:list[videoList] = Field(min_length=1)
    needCaption:list[StrictBool]
    outputVideo:str = Field('./output.mp4', pattern=r'\.mp4$')
    captionMargin:int = Field(50, ge=0)
    captionSize:int = Field(90, ge=0)
    captionColor:str = Field('0xffffff', pattern=r'^0x([0-9a-fA-F]{6}|[0-9a-fA-F]{8})$')
    captionBorderColor:str = Field('0x000000', pattern=r'^0x([0-9a-fA-F]{6}|[0-9a-fA-F]{8})$')
    BorderWidthRatio:float = Field(0.05, ge=0, le=1)
    captionDisplayTime:int = Field(5, ge=0)
    captionFont:Annotated[str | None, Field(pattern=r'\.(ttf|otf|ttc|woff2?)$')] = None
    backgroundColor:str = Field('0xffffff', pattern=r'^0x([0-9a-fA-F]{6}|[0-9a-fA-F]{8})$')
    width:Annotated[int | None, Field(ge=0)] = None
    height:Annotated[int | None, Field(ge=0)] = None
    fps:Annotated[int | None, Field(ge=0)] = None
    sampleRate:Annotated[int | None, Field(ge=0)] = None
    preset:presetList = 'slow'
    HWEncode:bool = False

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

def getResourcePath(relativePath):
    if relativePath.endswith('/'):
        dir = relativePath.rstrip('/').rstrip('\\')
        path = os.path.join(os.path.abspath('./assets/'), dir, '')
        if hasattr(sys, '_MEIPASS'):
            path = os.path.join(sys._MEIPASS, dir, '')
        return path
    else:
        file = re.split(r'[/\\]', relativePath)[-1]
        path = os.path.join(os.path.abspath('./assets/'), file)
        if hasattr(sys, '_MEIPASS'):
            path = os.path.join(sys._MEIPASS, file)
        return path

def getDuration(path):
    cmd = [
        getResourcePath('ffprobe.exe'), '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'json',
        path
    ]

    try:
        result = json.loads(subprocess.run(cmd, capture_output=True, text=True, check=True, creationflags=CREATE_NO_WINDOW).stdout)

        duration = result.get('format', {}).get('duration', None)

        return float(duration)

    except Exception as e:
        print(f'error:{e}')
        return None

@eel.expose
def selectEncoder(codec = 'h264'):
    cpuCodec = 'libx264' if codec == 'h264' else 'libx265'
    try:
        result = subprocess.run([getResourcePath('ffmpeg.exe'), '-hwaccels'], capture_output=True, text=True, check=True, creationflags=CREATE_NO_WINDOW).stdout.splitlines()[1:]
        HWConfigs = [
            {'name': 'cuda', 'encoder': f'{codec}_nvenc'},
            {'name': 'qsv',  'encoder': f'{codec}_qsv'},
            {'name': 'amf',  'encoder': f'{codec}_amf'}
        ]

        selectedHW = None
        for config in HWConfigs:
            if config['name'] in result:
                selectedHW = config
                break
        
        if selectedHW:
            return selectedHW['encoder']
        else:
            return cpuCodec

    except Exception as e:
        print(f'error:{e}')
        return cpuCodec

def hasAudio(path):
    cmd = [
        getResourcePath('ffprobe.exe'), '-v', 'error',
        '-select_streams', 'a',
        '-show_entries', 'stream=index', 
        '-of', 'json',
        path
    ]
    
    try:
        result = json.loads(subprocess.run(cmd, capture_output=True, text=True, check=True, creationflags=CREATE_NO_WINDOW).stdout)
        audio = len(result.get('streams', [])) > 0

        return audio
    except Exception as e:
        print(f'error:{e}')
        return False

def getMediaCreateTime(path):
    cmd = [
        getResourcePath('ffprobe.exe'), '-v', 'error',
        '-show_entries', 'format_tags=creation_time',
        '-of', 'json',
        path
    ]

    try:
        result = json.loads(subprocess.run(cmd, capture_output=True, text=True, check=True, creationflags=CREATE_NO_WINDOW).stdout)
        creationTime = result.get('format', {}).get('tags', {}).get('creation_time')

        if not creationTime:
            return None
        
        utc = datetime.fromisoformat(creationTime.replace('Z', '+00:00'))
        jst = timezone(timedelta(hours=9))
        creationTimeJst = utc.astimezone(jst)

        return creationTimeJst

    except Exception as e:
        print(f'error:{e}')
        return None

def getVideoStreamInfo(path):
    cmd = [
        getResourcePath('ffprobe.exe'), '-v', 'error',
        '-show_entries', 'stream=width,height,r_frame_rate,sample_rate:stream_side_data=rotation',
        '-of', 'json',
        path
    ]

    try:
        result = json.loads(subprocess.run(cmd, capture_output=True, text=True, check=True, creationflags=CREATE_NO_WINDOW).stdout)
        streamData = result.get('streams', {})
        if not streamData:
            return None
        
        streamDataV = next((d for d in streamData if 'width' in d), {})
        streamDataA = next((d for d in streamData if 'sample_rate' in d), {})

        width = streamDataV.get('width', '1920')
        height = streamDataV.get('height', '1080')
        fps = str(float(Fraction(streamDataV.get('r_frame_rate', '60'))))
        sampleRate = streamDataA.get('sample_rate', '48000')

        rotation = 0
        rotationData = next((d for d in streamDataV.get('side_data_list', {}) if 'rotation' in d), {}).get('rotation')
        
        if rotationData is not None:
            rotation = abs(int(rotationData))

        if rotation == 90 or rotation == 270:
            width, height = height, width

        return {'width': width, 'height': height, 'fps': fps, 'sampleRate': sampleRate}

    except Exception as e:
        print(f'error:{e}')
        return None
    
def getDuration(path):
    cmd = [
        getResourcePath('ffprobe.exe'), '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'json',
        path
    ]
    try:
        result = json.loads(subprocess.run(cmd, capture_output=True, text=True, check=True, creationflags=CREATE_NO_WINDOW).stdout)
        return float(result.get('format', {}).get('duration', {}))
    except:
        return 0.0

def createChapter(durations, text):
    chapterText = ''
    nowTime = 0
    for i, _ in enumerate(durations):
        td = str(timedelta(seconds=(nowTime)))
        H, M, S = [str(int(float(s))).zfill(2) for s in td.split(':')]
        ftime = ''
        if int(H) == 0:
            ftime = f'{M}:{S}'
        else:
            ftime = f'{H}:{M}:{S}'
        chapterText += f'{ftime} {text[i]}\n'
        nowTime += durations[i]
    return chapterText.rstrip('\n')

def saveLog(logText):
    LOG_DIR = Path.home() / 'Documents' / 'ricevalley' / 'ToyVideoMixer_Log'
    MAX_FILES = 10

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    filePath = os.path.join(LOG_DIR, f'log_{timestamp}.txt')

    with open(filePath, 'w', encoding='utf-8') as f:
        f.write(logText)
    
    files = sorted(glob.glob(os.path.join(LOG_DIR, 'log_*.txt')), key=os.path.getmtime)
    while len(files) > MAX_FILES:
        oldestFile = files.pop(0)
        os.remove(oldestFile)

process = None
@eel.expose
def generateVideo(userSettings):
    global process

    try:
        inputVideo, needCaption, outputVideo, captionMargin, captionSize, captionColor, captionBorderColor, BorderWidthRatio, captionDisplayTime, captionFont, backgroundColor, width, height, fps, sampleRate, preset, HWEncode = itemgetter(
            'inputVideo', 'needCaption', 'outputVideo', 'captionMargin', 'captionSize', 'captionColor', 'captionBorderColor', 'BorderWidthRatio', 'captionDisplayTime', 'captionFont', 'backgroundColor', 'width', 'height', 'fps', 'sampleRate', 'preset', 'HWEncode'
        )(UserSettings.model_validate(userSettings).model_dump())

        captionBorderWidth = int(captionSize * BorderWidthRatio)

        videoStreamInfo = getVideoStreamInfo(inputVideo[0])
        baseW = width if width is not None else videoStreamInfo.get('width')
        baseH = height if height is not None else videoStreamInfo.get('height')
        baseFps = fps if fps is not None else videoStreamInfo.get('fps')
        baseSampleRate = sampleRate if sampleRate is not None else videoStreamInfo.get('sampleRate')

        captionFont = captionFont if captionFont is not None else getResourcePath('ZenMaruGothic-Medium.ttf')
        captionFont = captionFont.replace('\\', '/').replace(':', '\\:')

        if len(needCaption) != len(inputVideo):
            needCaption = [True] * len(inputVideo)

        inputs = []
        filters = []
        concatLabels = ''

        captionTextList = []
        for i, f in enumerate(inputVideo):
            inputs.extend(['-i', f])
            
            createdTime = getMediaCreateTime(f)
            captionText = createdTime.strftime('%a,%m.%d.%Y\n%H\\:%M\\:%S') if createdTime is not None else ''

            captionTextList.append(captionText.replace('\n', ' ').replace('\\:', ':'))

            vLabel = f'v_{i}'
            Vfilters = (
                f'[{i}:v]fps={baseFps},'
                f'scale={baseW}:{baseH}:force_original_aspect_ratio=decrease,'
                f'pad={baseW}:{baseH}:(ow-iw)/2:(oh-ih)/2:{backgroundColor},setsar=1'
            )
            if needCaption[i]:
                Vfilters += (
                    f",drawtext=text='{captionText}':"
                    f"fontfile='{captionFont}':"
                    f'fontcolor={captionColor}:'
                    f'bordercolor={captionBorderColor}:borderw={captionBorderWidth}:'
                    f'fontsize={captionSize}:'
                    f'x={captionMargin}:y={captionMargin}:'
                    f"enable='between(t,0,{captionDisplayTime})'"
                )
            filters.append(f'{Vfilters}[{vLabel}]')

            aLabel = f'a_{i}'
            if hasAudio(f):
                filters.append(
                    f'[{i}:a]aresample={baseSampleRate}:cutoff=0.95:dither_method=triangular,'
                    f'aformat=sample_fmts=fltp:channel_layouts=stereo[{aLabel}]'
                )
            else:
                duration = getDuration(f)
                filters.append(
                    f'aevalsrc=0:d={duration}:s={baseSampleRate}:c=stereo,'
                    f'aformat=sample_fmts=fltp:channel_layouts=stereo[{aLabel}]'
                )
            
            concatLabels += f'[{vLabel}][{aLabel}]'

        concatFilter = f'{concatLabels}concat=n={len(inputVideo)}:v=1:a=1[outv][outa]'
        filter = '; '.join(filters) + f'; {concatFilter}'

        codec = 'libx264'
        if HWEncode:
            codec = selectEncoder()

        vQuality = []
        if 'nvenc' in codec:
            vQuality = ['-cq', '17']
        elif 'qsv' in codec:
            vQuality = ['-global_quality', '17']
        elif 'libx' in codec:
            vQuality = ['-crf', '17']

        fullDuration = 0
        videosDuration = []
        for v in inputVideo:
            aDuration = getDuration(v)
            videosDuration.append(aDuration)
            fullDuration += (aDuration if aDuration is not None else 0)

        fullDuration = fullDuration * 10 ** 6

        cmd = [
            getResourcePath('ffmpeg.exe'), '-y',
            *inputs,
            '-filter_complex', filter,
            '-map', '[outv]', '-map', '[outa]',
            '-c:v', codec,
            *vQuality,
            '-preset', preset,
            '-c:a', 'aac',
            '-b:a', '320k',
            '-ar', str(baseSampleRate),
            '-fps_mode', 'vfr',
            outputVideo,
            '-progress', '-'
        ]

        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True, 
            encoding='utf-8',
            errors='replace',
            creationflags=CREATE_NO_WINDOW
        )

        def monitorProcess():
            global process
            while True:
                if process is not None:
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        if process.returncode == 0:
                            eel.showProgress(1)
                            eel.addLog('\n----Process finished----')
                            eel.quitProcess('完了')
                            eel.showAlert('処理が完了しました。')
                            eel.addLog('\n\nChapter\n')
                            eel.addLog(createChapter(videosDuration, captionTextList))
                            saveLog(eel.getAllLog()())
                        else:
                            eel.addLog(f'\n----Process error----')
                            eel.quitProcess('エラー')
                            eel.showAlert('エラーが発生しました。')
                        process = None
                        break
                    if line:
                        eel.addLog(line)
                        if 'out_time_us=' in line:
                            nowProgressTime = line.split('=')[-1].strip()
                            if nowProgressTime.isdecimal():
                                progress = float(nowProgressTime) / float(fullDuration)
                                eel.showProgress(float(f'{max(min(progress, 1), 0):.4f}'))
                    eel.sleep(0.01)
                else:
                    break

        eel.spawn(monitorProcess)
    except Exception as e:
        eel.addError(str(e))

@eel.expose
def terminateProcess():
    global process
    if process is not None:
        process.terminate()
        process.wait()
        process = None
        eel.addLog('\n----Process terminated----')
        eel.showAlert('処理を中止しました。')

root = tk.Tk()
icon = tk.PhotoImage(file=getResourcePath('icon-256.png'))
root.iconphoto(True, icon)
root.destroy()

@eel.expose
def selectInputFiles():
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    filePath = filedialog.askopenfilenames(
        title='Select Files',
        filetypes=[('video files', '*.mp4')]
    )
    root.destroy()

    filePath = list(filePath)
    if filePath:
        return filePath
    else:
        return None
    
@eel.expose
def selectOutputFiles():
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    filePath = filedialog.asksaveasfilename(
        title='Select File',
        initialfile = 'video.mp4',
        defaultextension = 'mp4',
        filetypes=[('video file', '*.mp4')]
    )
    root.destroy()

    if filePath:
        return filePath
    else:
        return None

@eel.expose
def selectFontFile():
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    filePath = filedialog.askopenfilename(
        title='Select File',
        filetypes=[('font file', '*.ttf;*.otf;*.ttc;*.woff;*.woff2')]
    )
    root.destroy()

    if filePath:
        return filePath
    else:
        return None
    
@eel.expose
@validate_call
def openFile(path:str = Field(pattern=r'\.mp4$')):
    os.startfile(path)

@eel.expose
@validate_call
def openDir(path:str = Field(pattern=r'[/\\]$')):
    subprocess.run(['explorer', path.replace('/', '\\')], creationflags=CREATE_NO_WINDOW)