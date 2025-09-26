import pyvisa
import time
import sys
import threading
import serial

from PyQt5.QtCore import Qt,QTimer,pyqtSignal, QRectF,QRect,QPointF
from PyQt5.QtWidgets import (QMainWindow, QAction, QWidget, QLabel,
                             QApplication, QHBoxLayout, QVBoxLayout,
                             QTableWidget, QTableWidgetItem,QSlider,
                             QTreeWidget,QTreeWidgetItem,QMenu,QDialog,
                             QLineEdit,QPushButton,QComboBox,QFileDialog,
                             QMessageBox,QHeaderView,QPlainTextEdit,
                             QGroupBox,QStackedWidget,QGridLayout)

from PyQt5.QtGui import (QIcon,QColor,QFont,QFontMetricsF,QTextCursor, QPainter, QPen, QPolygonF, QPixmap, QImage,QKeyEvent)

import pyqtgraph as pg

timeStep = 0.2

Supply01DevName = 'ASRL/dev/ttyUSB1::INSTR'
Load01DevName = 'USB0::6833::3601::DL3A26CM00343::0::INSTR'

currentMax = 3
currentMin = 0
voltMax = 16
voltMin = 0


fontName = "Arial" 

class mainWin(QMainWindow):
    
	def __init__(self):
		super().__init__()
		self.mm = mainWidget()
		self.mm.voltUpdateSignal.connect(self.updateVolts)
		self.mm.voltToggleActiveSignal.connect(self.toggleVolts)
		rm = pyvisa.ResourceManager()
		#print(rm.list_resources('?*'))
		
		try:
			self.load01 = rm.open_resource(Load01DevName)
			self.load01.write_termination = '\n'
			self.load01.read_termination = '\n'
			self.mm.load01_errors = None
		
		except ValueError:
			print("Load not connected")
			self.mm.load01_errors = 1
			
			
		try:
			self.supply01 = rm.open_resource(Supply01DevName)
			self.supply01.write_termination = '\n'
			self.supply01.read_termination = '\n'
			self.mm.supply01_errors = None
			
		except ValueError:
			print("Supply not connected")
			self.mm.supply01_errors = 1
		
		self.arduino = serial.Serial(port='/dev/ttyACM0', baudrate=9600, timeout=.1)
		
        
		self.setCentralWidget(self.mm)

		self.startTime = 0
		
		self.listenerThread = threading.Thread(target = self.listener)
		self.listening = True
		
		self.listenerThread.start()
		
		
        
		self.show()
        
	def listener(self):
		
		self.startTime = time.time()
		
		while self.listening == True:
			t = time.time() - self.startTime
			
			voltData = []
			currentData = []
			tempData = []
			
			try:
				self.supply01.write(":OUTPut:STATe? CH1")
				supplyMode = self.supply01.read().lower()
				if "on" in supplyMode:
					self.mm.Supply01CurrentState = True
				else:
					self.mm.Supply01CurrentState = False
					
				self.supply01.write(":MEASure?")
				#print(self.supply01.read())
				voltData.append(float(self.supply01.read()))
				
				self.supply01.write(":MEASure:CURRent?")
				currentData.append(float(self.supply01.read()))
				
			except pyvisa.errors.VisaIOError:
				self.mm.supply01_errors = 1
			except ValueError:
				self.mm.supply01_errors = 1
			except AttributeError:
				self.mm.supply01_errors = 1
			
			try:
				self.load01.write(":MEASure:VOLTage?")
				voltData.append(float(self.load01.read()))
			
				self.load01.write(":MEASure:CURRent?")
				currentData.append(float(self.load01.read()))
			
			except pyvisa.errors.VisaIOError:
				self.mm.load01_errors = 1
			except ValueError:
				self.mm.load01_errors = 1
			except AttributeError:
				self.mm.load01_errors = 1
				
			self.arduino.write(bytes(":T", 'utf-8'))
			time.sleep(0.05)
			readData = self.arduino.readline().decode('utf-8')
			
			if ":T:" in readData:
				td = readData.split(":T:")
				if len(td) == 2:
					tempData = td[1].split(",")
			
			
			self.mm.update(t,voltData,currentData,tempData)
			
			time.sleep(timeStep)
			
	def updateVolts(self,tgt):
		
		#print(f":SOURce:VOLTage {tgt}")
		self.supply01.write(f":SOURce:VOLTage {tgt}")
		
	def toggleVolts(self):
		
		if self.mm.Supply01CurrentState == False:
			self.supply01.write(":OUTPut:STATe CH1,ON")
		else:
			print("Trying to turn off supply")
			self.supply01.write(":OUTPut:STATe CH1,OFF")

        
class mainWidget(QWidget):
	
	voltUpdateSignal = pyqtSignal(str)
	voltToggleActiveSignal = pyqtSignal()
	currentUpdateSignal = pyqtSignal(str)
    
    
    
	def __init__(self):
        
		super().__init__()
        
		self.w = pg.GraphicsLayoutWidget()
		self.voltControl = manualInputWidget("VOLT",voltMax,voltMin)
		self.voltControl.targetUpdateSignal.connect(self.voltUpdateSignal)
		self.voltControl.toggleActiveSignal.connect(self.voltToggleActiveSignal)
		self.currentControl = manualInputWidget("CURRENT",currentMax,currentMin)
		
		
		controlLayout = QVBoxLayout()
		controlLayout.addWidget(self.voltControl)
		controlLayout.addWidget(self.currentControl)
		
		self.TimeData = []
		self.Load01VoltData = []
		self.Load01CurrentData = []
		
		self.Supply01VoltData = []
		self.Supply01CurrentData = []
		self.Supply01CurrentState = False
		
		self.TempAmbientFData = []
		self.TempProbeFData = []
        
        
		self.volts = self.w.addPlot(row=0, col=0)
		self.volts.setTitle("Volts")
		self.volts.setYRange(0,15)
		self.Load01VoltLine = self.volts.plot(x = self.TimeData,y = self.Load01VoltData)
		self.Supply01VoltLine = self.volts.plot(x = self.TimeData,y = self.Supply01VoltData)
		
		
		self.current = self.w.addPlot(row=1, col=0)
		self.current.setTitle("Current")
		self.current.setYRange(-5,5)
		self.Load01CurrentLine = self.current.plot(x = self.TimeData,y = self.Load01CurrentData)
		self.Supply01CurrentLine = self.current.plot(x = self.TimeData,y = self.Supply01CurrentData)
		
		self.temperature = self.w.addPlot(row=2, col=0)
		self.temperature.setTitle("Temp (F)")
		self.temperature.setYRange(0,150)
		self.ambientTempFLine = self.temperature.plot(x = self.TimeData,y = self.TempAmbientFData)
		self.probeTempFLine = self.temperature.plot(x = self.TimeData,y = self.TempProbeFData)
		
        
		self.mainLayout = QHBoxLayout()
		self.mainLayout.addLayout(controlLayout)
		self.mainLayout.addWidget(self.w)
        
        
		self.setLayout(self.mainLayout)
        
	def update(self,t,voltData,currentData,tempData):
		
		self.TimeData.append(t)
		
		if self.load01_errors == None:
			self.Load01VoltData.append(voltData[0])
			self.Load01CurrentData.append(currentData[0])
			self.Load01VoltLine.setData(self.Load01VoltData)
			self.Load01CurrentLine.setData(self.Load01CurrentData)
			
			
		if self.supply01_errors == None:
			self.Supply01VoltData.append(voltData[1])
		
			self.voltControl.updateMeasured(voltData[1])
			self.Supply01CurrentData.append(currentData[1])
		
			self.Supply01VoltLine.setData(self.Supply01VoltData)
			self.Supply01CurrentLine.setData(self.Supply01CurrentData)
			
		self.TempAmbientFData.append(float(tempData[0]))
		self.TempProbeFData.append(float(tempData[1]))
		self.ambientTempFLine.setData(self.TempAmbientFData)
		self.probeTempFLine.setData(self.TempProbeFData)
			
			
		
		
class manualInputWidget(QWidget):
    
    targetUpdateSignal = pyqtSignal(str)
    toggleActiveSignal = pyqtSignal()
    
    
    def __init__(self,title,maxValue,minValue):
        
        super().__init__()
        
        buttonSize = 75
        self.targetValue = 0
        self.maxValue = maxValue
        self.minValue = minValue
        
        self.modeButton = QPushButton("MODE")
        self.modeButton.clicked.connect(self.toggleActiveSignal)
        self.modeButton.setMinimumSize(buttonSize,buttonSize)
        self.modeButton.setMaximumSize(buttonSize,buttonSize)
        
        
        self.upLargeButton = QPushButton('++')
        self.upLargeButton.setStyleSheet(
            "QPushButton {"
            "border: 3px solid green;"  # 3px solid red border
            "border-radius: 20px;"       # Rounded corners
            "padding: 5px;"              # Add some padding
            "}"
        )
        self.upLargeButton.setFont(QFont(fontName, 14))
        self.upLargeButton.clicked.connect(self.largeIncrease)
        self.upLargeButton.setMinimumSize(buttonSize,buttonSize)
        self.upLargeButton.setMaximumSize(buttonSize,buttonSize)
        
        self.upSmallButton = QPushButton('+')
        self.upSmallButton.setStyleSheet(
            "QPushButton {"
            "border: 3px solid green;"  # 3px solid red border
            "border-radius: 20px;"       # Rounded corners
            "padding: 5px;"              # Add some padding
            "}"
        )
        self.upSmallButton.setFont(QFont(fontName, 14))
        self.upSmallButton.clicked.connect(self.smallIncrease)
        self.upSmallButton.setMinimumSize(buttonSize,buttonSize)
        self.upSmallButton.setMaximumSize(buttonSize,buttonSize)
        
        self.downLargeButton = QPushButton('--')
        self.downLargeButton.setStyleSheet(
            "QPushButton {"
            "border: 3px solid #FF0000;"  # 3px solid red border
            "border-radius: 20px;"       # Rounded corners
            "padding: 5px;"              # Add some padding
            "}"
        )
        self.downLargeButton.setFont(QFont(fontName, 14))
        self.downLargeButton.clicked.connect(self.largeDecrease)
        self.downLargeButton.setMinimumSize(buttonSize,buttonSize)
        self.downLargeButton.setMaximumSize(buttonSize,buttonSize)
        
        self.downSmallButton = QPushButton('-')
        self.downSmallButton.setStyleSheet(
            "QPushButton {"
            "border: 3px solid #FF0000;"  # 3px solid red border
            "border-radius: 20px;"       # Rounded corners
            "padding: 5px;"              # Add some padding
            "}"
        )
        self.downSmallButton.setFont(QFont(fontName, 14))
        self.downSmallButton.clicked.connect(self.smallDecrease)
        self.downSmallButton.setMinimumSize(buttonSize,buttonSize)
        self.downSmallButton.setMaximumSize(buttonSize,buttonSize)
        
        smallButtonLayout = QVBoxLayout()
        smallButtonLayout.addWidget(self.upSmallButton)
        smallButtonLayout.addWidget(self.downSmallButton)
        
        largeButtonLayout = QVBoxLayout()
        largeButtonLayout.addWidget(self.upLargeButton)
        largeButtonLayout.addWidget(self.downLargeButton)
        
        titleLabel = QLabel(title)
        titleLabel.setAlignment(Qt.AlignCenter)
        titleLabel.setFont(QFont(fontName, 14))
        
        topLayout = QHBoxLayout()
        topLayout.addWidget(self.modeButton)
        topLayout.addWidget(titleLabel)
        
        measuredLabel = QLabel("MEASURED")
        measuredLabel.setAlignment(Qt.AlignCenter)
        self.measuredDisp = QLabel("-")
        self.measuredDisp.setFont(QFont(fontName, 14))
        self.measuredDisp.setStyleSheet("""
        background-color: #262626;
        color: #FFFFFF;
        """)
        self.measuredDisp.setAlignment(Qt.AlignCenter)
        self.measuredDisp.setMinimumSize(100,50)
        self.measuredDisp.setMaximumSize(100,50)
        
        tgtLabel = QLabel("TARGET")
        tgtLabel.setAlignment(Qt.AlignCenter)
        self.tgtDisp = QLabel("-")
        self.tgtDisp.setFont(QFont(fontName, 14))
        self.tgtDisp.setStyleSheet("""
        background-color: #262626;
        color: #FFFFFF;
        """)
        self.tgtDisp.setAlignment(Qt.AlignCenter)
        self.tgtDisp.setMinimumSize(100,50)
        self.tgtDisp.setMaximumSize(100,50)

        
        displayLayout = QVBoxLayout()

        displayLayout.addWidget(measuredLabel)
        displayLayout.addWidget(self.measuredDisp)
        displayLayout.addWidget(tgtLabel)
        displayLayout.addWidget(self.tgtDisp)
        
        
        
        middleLayout = QHBoxLayout()
        middleLayout.addLayout(smallButtonLayout)
        middleLayout.addLayout(displayLayout)
        middleLayout.addLayout(largeButtonLayout)
        
        mainLayout = QVBoxLayout()
        mainLayout.addLayout(topLayout)
        mainLayout.addLayout(middleLayout)
        
        self.updateTarget()
        
        self.setLayout(mainLayout)
        
        
    def updateTarget(self):
        
        if self.targetValue > self.maxValue:
            self.targetValue = self.maxValue
        elif self.targetValue < self.minValue:
            self.targetValue = self.minValue
            
        outstr = f"{self.targetValue:.2f}"
        self.tgtDisp.setText(outstr)
        self.targetUpdateSignal.emit(outstr)
        
    def updateMeasured(self,value):
        

        outstr = f"{value:.4f}"
        self.measuredDisp.setText(outstr)
        
    def smallIncrease(self):
        
        self.targetValue += 0.1
        self.updateTarget()
        
    def smallDecrease(self):
        
        self.targetValue -= 0.1
        self.updateTarget()
        
    def largeIncrease(self):
        
        self.targetValue += 1
        self.updateTarget()
        
    def largeDecrease(self):
        
        self.targetValue -= 1
        self.updateTarget()
        
        



if __name__ == '__main__':
    
    app = QApplication(sys.argv)
    
    
    mw = mainWin()
    
    sys.exit(app.exec_()) 
