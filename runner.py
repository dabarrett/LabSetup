try:
    import pyvisa
    RM_ERROR = None
except ModuleNotFoundError:
    RM_ERROR = 1
    LOAD_01_ERROR = 1
    SUPPLY_ERROR = 1
    
    
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

TEMP_ERROR = None

fontName = "Arial" 

class mainWin(QMainWindow):
    
	def __init__(self):
		super().__init__()
		
		global RM_ERROR
		global LOAD_01_ERROR
		global SUPPLY_ERROR
		global TEMP_ERROR
		
		self.outFile = ''
		
		mainMenu = self.menuBar()
		fileMenu = mainMenu.addMenu('File')
		runMenu = mainMenu.addMenu('Run')
		
		startRunButton = QAction('Start Run',self)
		startRunButton.triggered.connect(self.startRun)
		runMenu.addAction(startRunButton)
		
		pauseRunButton = QAction('Pause Run',self)
		pauseRunButton.triggered.connect(self.pauseRun)
		runMenu.addAction(pauseRunButton)
		
		clearRunButton = QAction('Clear Run',self)
		clearRunButton.triggered.connect(self.clearRun)
		runMenu.addAction(clearRunButton)
		
		saveFileButton = QAction('Save Output to File',self)
		saveFileButton.triggered.connect(self.saveFile)
		fileMenu.addAction(saveFileButton)
		
		exitButton = QAction(QIcon('exit24.png'), 'Exit', self)
		exitButton.setShortcut('Ctrl+Q')
		exitButton.setStatusTip('Exit application')
		exitButton.triggered.connect(self.close)
        
		fileMenu.addAction(exitButton)
		
		self.mm = mainWidget()
		self.mm.supplyVoltUpdateSignal.connect(self.updateVolts)
		self.mm.load01CurrentUpdateSignal.connect(self.updateCurrent01)
		self.mm.supplyToggleActiveSignal.connect(self.toggleSupply)
		self.mm.load01ToggleActiveSignal.connect(self.toggleLoad01)
		
		if RM_ERROR == None:
			rm = pyvisa.ResourceManager()
		#print(rm.list_resources('?*'))
		
			try:
				self.load01 = rm.open_resource(Load01DevName)
				self.load01.write_termination = '\n'
				self.load01.read_termination = '\n'
				LOAD_01_ERROR = None
			
			except ValueError:
				print("Load not connected")
				LOAD_01_ERROR = 1
				
				
			try:
				self.supply01 = rm.open_resource(Supply01DevName)
				self.supply01.write_termination = '\n'
				self.supply01.read_termination = '\n'
				SUPPLY_ERROR = None
				
			except ValueError:
				print("Supply not connected")
				SUPPLY_ERROR = 1
		
		try:
			self.arduino = serial.Serial(port='/dev/ttyACM0', baudrate=9600, timeout=.1)
			TEMP_ERROR = None
			
			
		except serial.serialutil.SerialException:
			print("Arduino not found")
			TEMP_ERROR = 1
		
        
		self.setCentralWidget(self.mm)

		self.startTime = 0
		
		self.listenerThread = threading.Thread(target = self.listener)
		self.listening = True
		self.recording = False
		
		self.listenerThread.start()
		
		
        
		self.show()
        
	def listener(self):
		
		self.startTime = time.time()
		
		
		while self.listening == True:
			t = time.time() - self.startTime
			
			voltData = []
			currentData = []
			tempData = []
			
			if RM_ERROR == None:
				try:
					
					self.supply01.write('*IDN?')
					idstr = self.supply01.read()
					
					self.supply01.write(":OUTPut:STATe? CH1")
					supplyMode = self.supply01.read().lower()
					if "on" in supplyMode:
						self.mm.Supply01CurrentState = True
					else:
						self.mm.Supply01CurrentState = False
						
					self.supply01.write(f":SOURce:VOLTage?")
					voltSet = self.supply01.read()
					voltData.append(voltSet)
						
					self.supply01.write(":MEASure?")
					#print(self.supply01.read())
					supplyVoltNow = float(self.supply01.read())
					voltData.append(supplyVoltNow)
						
					self.supply01.write(":MEASure:CURRent?")
					supplyCurrentNow = float(self.supply01.read())
					currentData.append(supplyCurrentNow)
					
					self.mm.updateSupply(idstr,'None',supplyMode,supplyVoltNow,supplyCurrentNow,voltSet)
					
					
					
				except pyvisa.errors.VisaIOError:
					SUPPLY_ERROR = 1
					self.mm.updateSupply('None','ERROR','None',-999,-999,-99)
				except ValueError:
					SUPPLY_ERROR = 1
					self.mm.updateSupply('None','ERROR','None',-999,-999,-99)
				except AttributeError:
					SUPPLY_ERROR = 1
					self.mm.updateSupply('None','ERROR','None',-999,-999,-99)
				
				try:
					
					self.load01.write('*IDN?')
					idstr = self.load01.read()
					
					self.load01.write(":OUTPut:STATe? CH1")
					loadMode = self.load01.read().lower()
					if "on" in loadMode:
						self.mm.Load01CurrentState = True
					else:
						self.mm.Load01CurrentState = False
					
					
					self.load01.write(f":SOURce:CURRent?")
					currSet = self.load01.read()
					currentData.append(currSet)
					
					self.load01.write(":MEASure:VOLTage?")
					loadVoltNow = float(self.load01.read())
					voltData.append(loadVoltNow)
						
					self.load01.write(":MEASure:CURRent?")
					loadCurrentNow = float(self.load01.read())
					currentData.append(loadCurrentNow)
					
					
					
					self.mm.updateLoad(idstr,'None',loadMode,loadVoltNow,loadCurrentNow,currSet)
					
					
				except pyvisa.errors.VisaIOError:
					LOAD_01_ERROR = 1
					self.mm.updateLoad('None','ERROR','None',-999,-999,-99)
				except ValueError:
					LOAD_01_ERROR = 1
					self.mm.updateLoad('None','ERROR','None',-999,-999,-99)
				except AttributeError:
					LOAD_01_ERROR = 1
					self.mm.updateLoad('None','ERROR','None',-999,-999,-99)
					
			else:
				self.mm.updateLoad('None','ERROR','None',-999,-999,-99)
				self.mm.updateSupply('None','ERROR','None',-999,-999,-99)
				
			if TEMP_ERROR == None:
				self.arduino.write(bytes(":T", 'utf-8'))
				time.sleep(0.05)
				readData = self.arduino.readline().decode('utf-8')
				
				if ":T:" in readData:
					td = readData.split(":T:")
					if len(td) == 2:
						tempData = td[1].split(",")
			
			
			if self.recording == True:
				self.mm.update(t,voltData,currentData,tempData)
				self.updateOutput(t,voltData,currentData,tempData)
			
			time.sleep(timeStep)
			
	def updateVolts(self,tgt):
		
		#print(f":SOURce:VOLTage {tgt}")
		self.supply01.write(f":SOURce:VOLTage {tgt}")
		
	def updateCurrent01(self,tgt):
		
		#print(f":SOURce:VOLTage {tgt}")
		self.load01.write(f":SOURce:CURRent {tgt}")
		
	def toggleSupply(self):
		
		if self.mm.Supply01CurrentState == False:
			self.supply01.write(":OUTPut:STATe CH1,ON")
		else:
			print("Trying to turn off supply")
			self.supply01.write(":OUTPut:STATe CH1,OFF")
			
	def toggleLoad01(self):
		
		if self.mm.Load01CurrentState == False:
			self.load01.write(":OUTPut:STATe CH1,ON")
		else:
			print("Trying to turn off supply")
			self.load01.write(":OUTPut:STATe CH1,OFF")
			
	def updateOutput(self,t,voltData,currentData,tempData):
		
		outline = ''
		outline += f'{t:.2f},'
		
		if SUPPLY_ERROR == None:
			outline += f'{voltData[0]:.2f},'
			outline += f'{voltData[1]:.2f},'
			outline += f'{currentData[1]:.2f},'
		else:
			outline += 'error,'
			outline += 'error,'
			outline += 'error,'
		
		if LOAD_01_ERROR == None:
			outline += f'{currentData[0]:.2f},'
			outline += f'{voltData[2]:.2f},'
			outline += f'{currentData[2]:.2f},'
		else:
			outline += 'error,'
			outline += 'error,'
			outline += 'error,'
			
		if TEMP_ERROR == None:
			outline += f'{tempData[0]:.2f},'
			outline += f'{tempData[1]:.2f}\n'
			
		else:
			outline += 'error,'
			outline += 'error\n'
		
		print(outline)
		
		self.outFile += outline
		
	
	def saveFile(self):
		fname = QFileDialog.getSaveFileName()
		outfname = fname[0].split('.')[0] + '.csv'
		f = open(outfname,'w')
		f.write(self.outFile)
		f.close()
	
		
	def startRun(self):
		
		print('Starting Run')
		self.recording = True
		
		self.outFile = ''
		self.outFile += 'TIME,'
		self.outFile += 'SUPPLY_Volt_Set,'
		self.outFile += 'SUPPLY_Volt_Measure,'
		self.outFile += 'SUPPLY_Current_Measure,'
		self.outFile += 'LOAD01_Current_Set,'
		self.outFile += 'LOAD01_Volt_Measure,'
		self.outFile += 'LOAD01_Current_Measure,'
		self.outFile += 'TEMP_Ambient_F,'
		self.outFile += 'TEMP_Measure_F'
		
		self.outFile += "\n"
		
	def pauseRun(self):
		
		print('Pausing Run')
		self.recording = False
		
	def clearRun(self):
		
		print('Clearing Run')
		self.outFile = ''
		self.startTime = time.time()
		self.mm.TimeData = []
		self.mm.Load01VoltData = []
		self.mm.Load01CurrentData = []
		self.mm.Supply01VoltData = []
		self.mm.Supply01CurrentData = []
		self.mm.TempAmbientFData = []
		self.mm.TempProbeFData = []
        
class mainWidget(QWidget):
	
	supplyVoltUpdateSignal = pyqtSignal(str)
	supplyToggleActiveSignal = pyqtSignal()
	load01CurrentUpdateSignal = pyqtSignal(str)
	load01ToggleActiveSignal = pyqtSignal()
    
	def __init__(self):
        
		super().__init__()
        
		self.w = pg.GraphicsLayoutWidget()
		self.voltControl = manualInputWidget("VOLT",voltMax,voltMin)
		self.voltControl.targetUpdateSignal.connect(self.supplyVoltUpdateSignal)
		self.voltControl.toggleActiveSignal.connect(self.supplyToggleActiveSignal)
		self.currentControl = manualInputWidget("CURRENT",currentMax,currentMin)
		self.currentControl.targetUpdateSignal.connect(self.load01CurrentUpdateSignal)
		self.currentControl.toggleActiveSignal.connect(self.load01ToggleActiveSignal)
		
		controlLayout = QVBoxLayout()
		controlLayout.addWidget(self.voltControl)
		controlLayout.addWidget(self.currentControl)
		
		self.TimeData = []
		self.Load01VoltData = []
		self.Load01CurrentData = []
		self.Load01CurrentState = False
		
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
		
		self.supplyStatus = equipmentStatusWidget('SUPPLY')
		
		self.loadStatus = equipmentStatusWidget('LOAD')
		
		self.tempStatus = tempStatusWidget()
		
		equipmentLayout = QVBoxLayout()
		equipmentLayout.addWidget(self.supplyStatus)
		equipmentLayout.addWidget(self.loadStatus)
		equipmentLayout.addWidget(self.tempStatus)
		
        
		self.mainLayout = QHBoxLayout()
		self.mainLayout.addLayout(controlLayout)
		self.mainLayout.addWidget(self.w)
		self.mainLayout.addLayout(equipmentLayout)
        
        
		self.setLayout(self.mainLayout)
        
	def update(self,t,voltData,currentData,tempData):
		# This is to update the graphing, not the immediate measured displays
		
		self.TimeData.append(t)
		
		if LOAD_01_ERROR == None:
			self.Load01VoltData.append(voltData[1])
			self.Load01CurrentData.append(currentData[1])
			self.Load01VoltLine.setData(self.Load01VoltData)
			self.Load01CurrentLine.setData(self.Load01CurrentData)
			
			
		if SUPPLY_ERROR == None:
			self.Supply01VoltData.append(voltData[2])
			self.Supply01CurrentData.append(currentData[2])
		
			self.Supply01VoltLine.setData(self.Supply01VoltData)
			self.Supply01CurrentLine.setData(self.Supply01CurrentData)
			
		if TEMP_ERROR == None:
			self.TempAmbientFData.append(float(tempData[0]))
			self.TempProbeFData.append(float(tempData[1]))
			self.ambientTempFLine.setData(self.TempAmbientFData)
			self.probeTempFLine.setData(self.TempProbeFData)
			
	def updateSupply(self,idnstr,statestr,funcstr,currfl,voltfl,voltSet):
		
		self.voltControl.updateMeasured(voltSet)
		self.supplyStatus.update(idnstr,statestr,funcstr,currfl,voltfl)
		
	def updateLoad(self,idnstr,statestr,funcstr,currfl,voltfl,currSet):
		self.currentControl.updateMeasured(currSet)
		self.loadStatus.update(idnstr,statestr,funcstr,currfl,voltfl)
			
		
		
class manualInputWidget(QGroupBox):
    
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
        
        measuredLabel = QLabel("SET")
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
        
        
class equipmentStatusWidget(QGroupBox):
    
    def __init__(self,title):
        
        super().__init__()
        
        self.setTitle(title)
        
        titleLabel = QLabel(title)
        titleLabel.setFont(QFont(fontName, 14))
        titleLabel.setAlignment(Qt.AlignCenter)
        
        self.brandLabel = QLabel('')
        self.brandLabel.setFont(QFont(fontName, 8))
        self.modelLabel = QLabel('')
        self.modelLabel.setFont(QFont(fontName, 8))
        self.snLabel = QLabel('')
        self.snLabel.setFont(QFont(fontName, 8))
        self.versionLabel = QLabel('')
        self.versionLabel.setFont(QFont(fontName, 8))
        
        ####### State
        stateTitleLabel = QLabel('State')
        stateTitleLabel.setFont(QFont(fontName, 10))
        
        self.stateValueLabel = QLabel('5.432')
        self.stateValueLabel.setFont(QFont(fontName, 12))
        self.stateValueLabel.setStyleSheet("""
        background-color: white;
        color: black;
        border: 1px solid black;
        """)
        self.stateValueLabel.setAlignment(Qt.AlignCenter)
        self.stateValueLabel.setMinimumSize(100,30)
        self.stateValueLabel.setMaximumSize(100,30)
        
        stateLayout = QHBoxLayout()
        stateLayout.addWidget(stateTitleLabel)
        stateLayout.addWidget(self.stateValueLabel)
        
        ####### Function
        functionTitleLabel = QLabel('Function')
        functionTitleLabel.setFont(QFont(fontName, 10))
        
        self.functionValueLabel = QLabel('5.432')
        self.functionValueLabel.setFont(QFont(fontName, 12))
        self.functionValueLabel.setStyleSheet("""
        background-color: white;
        color: black;
        border: 1px solid black;
        """)
        self.functionValueLabel.setAlignment(Qt.AlignCenter)
        self.functionValueLabel.setMinimumSize(100,30)
        self.functionValueLabel.setMaximumSize(100,30)
        
        functionLayout = QHBoxLayout()
        functionLayout.addWidget(functionTitleLabel)
        functionLayout.addWidget(self.functionValueLabel)
        
        ####### Current
        currentTitleLabel = QLabel('Current')
        currentTitleLabel.setFont(QFont(fontName, 10))
        
        self.currentValueLabel = QLabel('5.432')
        self.currentValueLabel.setFont(QFont(fontName, 12))
        self.currentValueLabel.setStyleSheet("""
        background-color: white;
        color: black;
        border: 1px solid black;
        """)
        self.currentValueLabel.setAlignment(Qt.AlignCenter)
        self.currentValueLabel.setMinimumSize(100,30)
        self.currentValueLabel.setMaximumSize(100,30)
        
        currentLayout = QHBoxLayout()
        currentLayout.addWidget(currentTitleLabel)
        currentLayout.addWidget(self.currentValueLabel)
        
        ####### Voltage
        voltTitleLabel = QLabel('Volt')
        voltTitleLabel.setFont(QFont(fontName, 10))
        
        self.voltValueLabel = QLabel('5.432')
        self.voltValueLabel.setFont(QFont(fontName, 12))
        self.voltValueLabel.setStyleSheet("""
        background-color: white;
        color: black;
        border: 1px solid black;
        """)
        self.voltValueLabel.setAlignment(Qt.AlignCenter)
        self.voltValueLabel.setMinimumSize(100,30)
        self.voltValueLabel.setMaximumSize(100,30)
        
        voltLayout = QHBoxLayout()
        voltLayout.addWidget(voltTitleLabel)
        voltLayout.addWidget(self.voltValueLabel)
        
        
        mainLayout = QVBoxLayout()
        #mainLayout.addWidget(titleLabel)
        mainLayout.addWidget(self.brandLabel)
        mainLayout.addWidget(self.modelLabel)
        mainLayout.addWidget(self.snLabel)
        mainLayout.addWidget(self.versionLabel)
        mainLayout.addLayout(stateLayout)
        mainLayout.addLayout(functionLayout)
        mainLayout.addLayout(currentLayout)
        mainLayout.addLayout(voltLayout)
        
        self.setLayout(mainLayout)
        
    def update(self,idnstr,statestr,funcstr,currfl,voltfl):
		
        self.stateValueLabel.setText(statestr)
        self.functionValueLabel.setText(funcstr)
        self.voltValueLabel.setText(f'{voltfl:.2f}')
        self.currentValueLabel.setText(f'{currfl:.2f}')
        
class tempStatusWidget(QGroupBox):
    
    def __init__(self):
        
        super().__init__()
        
        self.setTitle("TEMP")
        
        
        ####### State
        stateTitleLabel = QLabel('State')
        stateTitleLabel.setFont(QFont(fontName, 10))
        
        self.stateValueLabel = QLabel('5.432')
        self.stateValueLabel.setFont(QFont(fontName, 12))
        self.stateValueLabel.setStyleSheet("""
        background-color: white;
        color: black;
        border: 1px solid black;
        """)
        self.stateValueLabel.setAlignment(Qt.AlignCenter)
        self.stateValueLabel.setMinimumSize(100,30)
        self.stateValueLabel.setMaximumSize(100,30)
        
        stateLayout = QHBoxLayout()
        stateLayout.addWidget(stateTitleLabel)
        stateLayout.addWidget(self.stateValueLabel)
        
        ####### Function
        functionTitleLabel = QLabel('Function')
        functionTitleLabel.setFont(QFont(fontName, 10))
        
        self.functionValueLabel = QLabel('5.432')
        self.functionValueLabel.setFont(QFont(fontName, 12))
        self.functionValueLabel.setStyleSheet("""
        background-color: white;
        color: black;
        border: 1px solid black;
        """)
        self.functionValueLabel.setAlignment(Qt.AlignCenter)
        self.functionValueLabel.setMinimumSize(100,30)
        self.functionValueLabel.setMaximumSize(100,30)
        
        functionLayout = QHBoxLayout()
        functionLayout.addWidget(functionTitleLabel)
        functionLayout.addWidget(self.functionValueLabel)
        
        ####### amb
        ambTitleLabel = QLabel('Ambient')
        ambTitleLabel.setFont(QFont(fontName, 10))
        
        self.ambValueLabel = QLabel('5.432')
        self.ambValueLabel.setFont(QFont(fontName, 12))
        self.ambValueLabel.setStyleSheet("""
        background-color: white;
        color: black;
        border: 1px solid black;
        """)
        self.ambValueLabel.setAlignment(Qt.AlignCenter)
        self.ambValueLabel.setMinimumSize(100,30)
        self.ambValueLabel.setMaximumSize(100,30)
        
        ambLayout = QHBoxLayout()
        ambLayout.addWidget(ambTitleLabel)
        ambLayout.addWidget(self.ambValueLabel)
        
        ####### Voltage
        targetTitleLabel = QLabel('Target')
        targetTitleLabel.setFont(QFont(fontName, 10))
        
        self.targetValueLabel = QLabel('5.432')
        self.targetValueLabel.setFont(QFont(fontName, 12))
        self.targetValueLabel.setStyleSheet("""
        background-color: white;
        color: black;
        border: 1px solid black;
        """)
        self.targetValueLabel.setAlignment(Qt.AlignCenter)
        self.targetValueLabel.setMinimumSize(100,30)
        self.targetValueLabel.setMaximumSize(100,30)
        
        targetLayout = QHBoxLayout()
        targetLayout.addWidget(targetTitleLabel)
        targetLayout.addWidget(self.targetValueLabel)
        
        
        mainLayout = QVBoxLayout()
        #mainLayout.addWidget(titleLabel)

        mainLayout.addLayout(stateLayout)
        mainLayout.addLayout(functionLayout)
        mainLayout.addLayout(ambLayout)
        mainLayout.addLayout(targetLayout)
        
        self.setLayout(mainLayout)


if __name__ == '__main__':
    
    app = QApplication(sys.argv)
    
    
    mw = mainWin()
    
    sys.exit(app.exec_()) 
