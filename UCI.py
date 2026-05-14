# Code authored by Ryan Adam Ashraf under the LGPL v3.0 license.
# Warning! code cannot run properly without datafile.json.

import json
import sys
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
import serial
from PySide6.QtCore import QObject, QRegularExpression, QTimer
from PySide6.QtGui import (
    QColor,
    QFont,
    QGuiApplication,
    QSyntaxHighlighter,
    QTextCharFormat,
)
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QWidget,
)

sp = None
logs = False
log = ""
executor = ThreadPoolExecutor(max_workers=2)

class LuaHighlighter(QSyntaxHighlighter):
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.rules = []
        
        keyword_fmt = self.create_format("#569CD6", bold=True)  # Blue
        comment_fmt = self.create_format("#6A9955", italic=True)  # Green
        string_fmt = self.create_format("#CE9178")  # Orange
        
        keywords = [
            r"\bif\b", r"\belse\b", r"\bdef\b", r"\breturn\b", 
            r"\bfor\b", r"\bwhile\b", r"\b\:\b"
        ]
        
        for word in keywords:
            self.rules.append((QRegularExpression(word), keyword_fmt))
            
        self.rules.append((QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'), string_fmt))
        self.rules.append((QRegularExpression(r"--[^\n]*"), comment_fmt))

    def create_format(self, color, bold=False, italic=False):
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        if bold:
            fmt.setFontWeight(QFont.Weight.Bold)
        if italic:
            fmt.setFontItalic(True)
        return fmt

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                match = it.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)

app = QApplication(sys.argv)
screen = QGuiApplication.primaryScreen()
geometry = screen.geometry()

window = QWidget()
window.setWindowTitle("UART Control Interface")
window.resize(geometry.width(), geometry.height())

box = QTextEdit(window)
highlighter = LuaHighlighter(box.document())
box.setFont(QFont("Courier New", 16))
box.resize(round(geometry.width() / 2), (geometry.height() - 40))
box.move(0, 35)

font = box.font()
font.setPointSize(16)
box.setFont(font)

button = QPushButton("Start", window)
button.setStyleSheet("""
    QPushButton { background-color: green; color: white; border-radius: 5px; padding: 10px; }
    QPushButton:hover { background-color: darkgreen; }
""")
button.setCheckable(True)
button.adjustSize()
tempx = int(geometry.width() / 2)
button.move(tempx - int(button.width()), 0)

button2 = QPushButton("Stop", window)
button2.setStyleSheet("""
    QPushButton { background-color: red; color: white; border-radius: 5px; padding: 10px; }
    QPushButton:hover { background-color: darkred; }
""")
button2.setCheckable(True)
button2.adjustSize()
tempx2 = int(geometry.width() / 2)
button2.move(tempx2 - (int(button.width() * 2)) - 1, 0)
button2.setChecked(True)

start_stop = QButtonGroup()
start_stop.addButton(button)
start_stop.addButton(button2)

def send(bytes_data):
    global sp
    if sp and sp.is_open:
        sp.write(bytes_data)

def read():
    global sp
    if sp and sp.is_open:
        return sp.readline()
    return b""

def log_check():
    global sp, logs, log
    while logs:
        if sp and sp.is_open and sp.in_waiting > 0:
            try:
                incoming = sp.readline().decode('utf-8', errors='ignore')
                log = log + incoming
                QTimer.singleShot(0, lambda: logbox.setText(log))
            except Exception:
                pass

def on_mode_change(buttonp):
    global sp, logs, log
    if buttonp.text() == "Start":
        try:
            sp = serial.Serial(port=portbox.text(), baudrate=int(baudbox.text()), timeout=1)
        except Exception as e:
            logbox.setText(f"Connection error: {e}")
            button2.setChecked(True)
            return
            
        hvar = box.toPlainText()
        exec(hvar)
        box.setEnabled(False)
        baudbox.setEnabled(False)
        portbox.setEnabled(False)
        logs = True
        
        button2.setStyleSheet("""QPushButton { background-color: red; } QPushButton:hover { background-color: darkred }""")
        button.setStyleSheet("""QPushButton { background-color: grey; } QPushButton:hover { background-color: darkgrey }""")
        button.update()
        button2.update()
        
    elif buttonp.text() == "Stop":
        logs = False
        if sp and sp.is_open:
            sp.close()
        log = ""
        box.setEnabled(True)
        baudbox.setEnabled(True)
        portbox.setEnabled(True)
        
        button.setStyleSheet("""QPushButton { background-color: green; } QPushButton:hover { background-color: darkgreen; }""")
        button2.setStyleSheet("""QPushButton { background-color: grey; } QPushButton:hover { background-color: darkgrey }""")
        button2.update()
        button.update()

start_stop.buttonClicked.connect(on_mode_change)

headingbox = QTextEdit("Instruction Code", window)
headingbox.setReadOnly(True)
headingbox.setFont(QFont("Courier New", 16))
headingbox.resize((int(int(geometry.width()) / 4.3) - (button.width() * 2)), 40 - 3)

baudbox = QLineEdit("", window)
baudbox.resize(int((button2.x() - (headingbox.x() + headingbox.width())) / 2), button2.height())
baudbox.move((headingbox.x() + headingbox.width()), button2.y())
baudbox.setPlaceholderText("baud rate")

portbox = QLineEdit("", window)
portbox.resize(int((button2.x() - (headingbox.x() + headingbox.width())) / 2), button2.height())
portbox.move((headingbox.x() + headingbox.width()) + baudbox.width(), button2.y())
portbox.setPlaceholderText("COM port")

logbox = QTextEdit("", window)
logbox.setReadOnly(True)
logbox.setFont(QFont("Courier New", 16))
logbox.resize(int(geometry.width() / 2), geometry.height())
logbox.move(int(round(geometry.width() / 2)), 0)

def logloop():
    try:
        with open(r"data\logs.txt", "r") as f:
            logbox.setText(f.read())
    except FileNotFoundError:
        pass
    QTimer.singleShot(100, logloop)

logloop()
window.show()
sys.exit(app.exec())
