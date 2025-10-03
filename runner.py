try:
    import pyvisa
    RM_ERROR = None
    LOAD_01_ERROR = None
    SUPPLY_ERROR = None
    
except ModuleNotFoundError:
    RM_ERROR = 1
    LOAD_01_ERROR = 1
    SUPPLY_ERROR = 1
    
SET_IND = 0
SUPPLY_IND = 1
CONV_IND = 2
LOAD_IND = 3

ELEC_DATA_LEN = 4

TEMP_AMB_IND = 0
TEMP_MEASURE_IND = 1
TEMP_SENSE_IND =2

TEMP_DATA_LEN = 3


    
    
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
			print(rm.list_resources('?*'))
		
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
		
		global RM_ERROR
		global LOAD_01_ERROR
		global SUPPLY_ERROR
		global TEMP_ERROR
		
		self.startTime = time.time()
		
		
		while self.listening == True:
			t = time.time() - self.startTime
			
			voltData = [None]*ELEC_DATA_LEN
			# [SET_IND] is the Supply Volt setting, as read from the supply
			# [SUPPLY_IND] is the Supply Volt measurement, as read from the supply
			# [CONV_IND] is the power converter voltage, measured after the converter, by the INA260
			# [LOAD_IND] is the Load voltage, as measured by the load generator
			
			currentData = [None]*ELEC_DATA_LEN
			# [SET_IND] is the Load Current setting, as read from the load
			# [SUPPLY_IND] is the Supply Current measurement, as read from the supply
			# [CONV_IND] is the power converter current, measured after the converter, by the INA260
			# [LOAD_IND] is the Load current, as measured by the load generator
			
			tempData = [None]*3
			# [TEMP_AMB_IND] is the ambient temperature
			# [TEMP_MEASURE_IND] is the measured temperature
			# [TEMP_SENSE_IND] is the sensed temperatature at the power converter
			
			powerData = [None]*ELEC_DATA_LEN
			# [SET_IND] is not used, for now
			# [SUPPLY_IND] is the Supply power measurement, as read from the supply
			# [CONV_IND] is the power converter power, measured after the converter, by the INA260
			# [LOAD_IND] is the Load power, as measured by the load generator
			
			
			
			if RM_ERROR == None:
				
				#print("Loading Supply\n")
				
				try:
					
					self.supply01.write('*IDN?')
					idstr = self.supply01.read()
					
					
					self.supply01.write(":OUTPut:STATe? CH1")
					supplyMode = self.supply01.read().lower()
					#print(supplyMode)
					if "on" in supplyMode:
						self.mm.Supply01CurrentState = True
					else:
						self.mm.Supply01CurrentState = False
						
					self.supply01.write(f":SOURce:VOLTage?")
					voltSet = float(self.supply01.read())
					voltData[SET_IND] = voltSet
						
					self.supply01.write(":MEASure?")
					#print(self.supply01.read())
					supplyVoltNow = float(self.supply01.read())
					voltData[1] = supplyVoltNow
						
					self.supply01.write(":MEASure:CURRent?")
					supplyCurrentNow = float(self.supply01.read())
					currentData[1] = supplyCurrentNow
					
					self.supply01.write(":MEASure:POWEr? CH1")
					supplyPowerNow = float(self.supply01.read())
					powerData[0] = supplyPowerNow
					
					self.mm.updateSupply(idstr,'None',supplyMode,currentData[SUPPLY_IND],voltData[SUPPLY_IND],voltData[SET_IND],powerData[SUPPLY_IND])
					
					
					
				except pyvisa.errors.VisaIOError:
					print("\t\tpyvisa error")
					SUPPLY_ERROR = 1
					self.mm.updateSupply('None','ERROR','None',currentData[SUPPLY_IND],voltData[SUPPLY_IND],voltData[SET_IND],powerData[SUPPLY_IND])
				except ValueError:
					print("\t\tvalue error")
					SUPPLY_ERROR = 1
					self.mm.updateSupply('None','ERROR','None',currentData[SUPPLY_IND],voltData[SUPPLY_IND],voltData[SET_IND],powerData[SUPPLY_IND])
				except AttributeError:
					print("\t\tattribute error")
					SUPPLY_ERROR = 1
					self.mm.updateSupply('None','ERROR','None',currentData[SUPPLY_IND],voltData[SUPPLY_IND],voltData[SET_IND],powerData[SUPPLY_IND])
					
				#print("\tSupply Errors " + str(SUPPLY_ERROR) + "\n")
				
				#print("Loading Load\n")
				
				try:
					
					self.load01.write('*IDN?')
					idstr = self.load01.read()
					#print(idstr)
					
					self.load01.write(":SOUR:INP:STAT? ")
					loadMode = int(self.load01.read())
					if loadMode == 1:
						self.mm.Load01CurrentState = True
					else:
						self.mm.Load01CurrentState = False
					
					#print(loadMode)
					
					self.load01.write(f":SOURce:CURRent?")
					currSet = float(self.load01.read())
					currentData[0] = currSet
					
					self.load01.write(":MEASure:VOLTage?")
					loadVoltNow = float(self.load01.read())
					voltData[3] = loadVoltNow
						
					self.load01.write(":MEASure:CURRent?")
					loadCurrentNow = float(self.load01.read())
					currentData[3] = loadCurrentNow
					
					self.load01.write(":MEASure:POWer[:DC]?")
					loadPowerNow = float(self.load01.read())
					powerData[2] = loadPowerNow
					
					
					self.mm.updateLoad(idstr,'None',loadMode,currentData[LOAD_IND],voltData[LOAD_IND],currentData[SET_IND],powerData[LOAD_IND])
					
					
				except pyvisa.errors.VisaIOError:
					print("\t\tpyvisa error")
					LOAD_01_ERROR = 1
					self.mm.updateLoad('None','ERROR','None',currentData[LOAD_IND],voltData[LOAD_IND],currentData[SET_IND],powerData[LOAD_IND])
				except ValueError:
					print("\t\tvalue error")
					LOAD_01_ERROR = 1
					self.mm.updateLoad('None','ERROR','None',currentData[LOAD_IND],voltData[LOAD_IND],currentData[SET_IND],powerData[LOAD_IND])
				except AttributeError:
					print("\t\tattribute error")
					LOAD_01_ERROR = 1
					self.mm.updateLoad('None','ERROR','None',currentData[LOAD_IND],voltData[LOAD_IND],currentData[SET_IND],powerData[LOAD_IND])
					
				#print("\tLoad Errors " + str(LOAD_01_ERROR) + "\n")
					
			else:
				self.mm.updateLoad('None','ERROR','None',currentData[LOAD_IND],voltData[LOAD_IND],currentData[SET_IND],powerData[LOAD_IND])
				self.mm.updateSupply('None','ERROR','None',currentData[SUPPLY_IND],voltData[SUPPLY_IND],voltData[SET_IND],powerData[SUPPLY_IND])
				
			if TEMP_ERROR == None:
				self.arduino.write(bytes(":T", 'utf-8'))
				time.sleep(0.05)
				readData = self.arduino.readline().decode('utf-8')
				
				if ":T:" in readData:
					td = readData.split(":T:")
					if len(td) == 2:
						d = td[1].split(",")
						tempData[0] = d[0]
						tempData[1] = d[1]
						
						self.mm.updateTemp('None',tempData)
					else:
						self.mm.updateTemp('Error',['-999','-999'])
				elif ":M:" in readData:
					td = readData.split(":M:")
					
					if len(td) == 4:
						inData = td[1].split(",")

						tempData[TEMP_AMB_IND] = inData[0]
						tempData[TEMP_MEAUSRE_IND] = inData[1]
						tempData[TEMP_SENSE_IND] = inData[2]
						voltData[CONV_IND] = inData[3]
						currentData[CONV_IND] = inData[4]
						powerData[CONV_IND] = inData[5]
						
						self.mm.updateTemp('None',tempData)
						self.mm.updateConv('None',[voltData[CONV_IND],currentData[CONV_IND],powerData[CONV_IND]],supplyPowerNow)
					else:
						self.mm.updateTemp('Error',tempData)
						self.mm.updateConv('Error',[voltData[CONV_IND],currentData[CONV_IND],powerData[CONV_IND]],-99)
						
					
			else:
				self.mm.updateTemp('Error',tempData)
				self.mm.updateConv('Error',[voltData[CONV_IND],currentData[CONV_IND],powerData[CONV_IND]],-99)
			
			
			if self.recording == True:
				self.mm.update(t,voltData,currentData,tempData)
				self.updateOutput(t,voltData,currentData,tempData,powerData)
			
			
			#print("Moving to next time step")
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
			self.load01.write(":SOUR:INP:STAT 1")
		else:
			print("Trying to turn off supply")
			self.load01.write(":SOUR:INP:STAT 0")
			
	def updateOutput(self,t,voltData,currentData,tempData,powerData):
		
		outline = ''
		outline += f'{t:.2f},'
		
		for d in voltData:
			
			if d != None:
				outline += f'{d:.2f},'
			else:
				outline += ','
				
		for d in currentData:
			
			if d != None:
				outline += f'{d:.2f},'
				
			else:
				outline += ','
				
		for d in powerData:
			
			if d != None:
				outline += f'{d:.2f},'
				
			else:
				outline += ','
				
		for d in tempData:
			
			if d != None:
				outline += f'{d:.2f},'
				
			else:
				outline += ','
		
		outline += '\n'
		
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
		
		voltLabels = ["NULL"]*ELEC_DATA_LEN
		voltLabels[SET_IND] = "SUPPLY_VOLT_SET"
		voltLabels[SUPPLY_IND] = "SUPPLY_VOLT_MEASURE"
		voltLabels[CONV_IND] = "CONV_VOLT_MEASURE"
		voltLabels[LOAD_IND] = "LOAD_VOLT_MEASURE"
		
		self.outFile += (',').join(voltLabels)
		self.outFile += ','
		
		currentLabels = ["NULL"]*ELEC_DATA_LEN
		currentLabels[SET_IND] = "SUPPLY_CURRENT_SET"
		currentLabels[SUPPLY_IND] = "SUPPLY_CURRENT_MEASURE"
		currentLabels[CONV_IND] = "CONV_CURRENT_MEASURE"
		currentLabels[LOAD_IND] = "LOAD_CURRENT_MEASURE"
		
		self.outFile += (',').join(currentLabels)
		self.outFile += ','
		
		powerLabels = ["NULL"]*ELEC_DATA_LEN
		powerLabels[SET_IND] = "SUPPLY_POWER_SET"
		powerLabels[SUPPLY_IND] = "SUPPLY_POWER_MEASURE"
		powerLabels[CONV_IND] = "CONV_POWER_MEASURE"
		powerLabels[LOAD_IND] = "LOAD_POWER_MEASURE"
		
		self.outFile += (',').join(powerLabels)
		self.outFile += ','
		
		tempLabels = ["NULL"]*TEMP_DATA_LEN
		tempLabels[SET_IND] = "TEMP_AMB"
		tempLabels[SUPPLY_IND] = "TEMP_MEASURE"
		tempLabels[CONV_IND] = "TEMP_SENSE"
		
		self.outFile += (',').join(tempLabels)
		self.outFile += ',PAD'
		
		
		self.outFile += "\n"
		
		print(self.outFile)
		
	def pauseRun(self):
		
		print('Pausing Run')
		self.recording = False
		
	def clearRun(self):
		
		print('Clearing Run')
		self.outFile = ''
		self.startTime = time.time()
		self.mm.TimeData = []
		
		self.mm.voltTimeHistory = [[]]*ELEC_DATA_LEN
		self.mm.currentTimeHistory = [[]]*ELEC_DATA_LEN
		self.mm.tempTimeHistory [[]]*TIME_DATA_LEN
		
        
class mainWidget(QWidget):
	
	supplyVoltUpdateSignal = pyqtSignal(str)
	supplyToggleActiveSignal = pyqtSignal()
	load01CurrentUpdateSignal = pyqtSignal(str)
	load01ToggleActiveSignal = pyqtSignal()
    
	def __init__(self):
        
		super().__init__()
		
		supplyPen = QPen()
		supplyPen.setWidth(2)
		supplyPen.setColor(Qt.blue)
		
		convPen = QPen()
		convPen.setWidth(2)
		convPen.setColor(Qt.green)
		
		loadPen = QPen()
		loadPen.setWidth(2)
		loadPen.setColor(Qt.white)
		
		setPen = QPen()
		setPen.setWidth(2)
		setPen.setColor(Qt.red)
		setPen.setStyle(Qt.DashDotLine)
		
		ambPen = QPen()
		ambPen.setWidth(2)
		ambPen.setColor(Qt.blue)
		
		probePen = QPen()
		probePen.setWidth(2)
		probePen.setColor(Qt.white)
        
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
		self.voltTimeHistory = [[]]*ELEC_DATA_LEN
		self.currentTimeHistory = [[]]*ELEC_DATA_LEN
		self.tempTimeHistory = [[]]*TEMP_DATA_LEN
		
		self.Load01CurrentState = False
		self.Supply01CurrentState = False
        
		self.volts = self.w.addPlot(row=0, col=0)
		self.volts.setTitle("Volts")
		self.volts.setYRange(0,15)
		self.Load01VoltLine = self.volts.plot(x = self.TimeData,y = self.voltTimeHistory[LOAD_IND],pen = loadPen)
		self.Supply01VoltLine = self.volts.plot(x = self.TimeData,y = self.voltTimeHistory[SUPPLY_IND], pen = supplyPen)
		self.ConvVoltLine = self.volts.plot(x = self.TimeData,y = self.voltTimeHistory[CONV_IND], pen = convPen)
		self.setVoltLine = self.volts.plot(x = self.TimeData,y = self.voltTimeHistory[SET_IND], pen = setPen)
		
		
		self.current = self.w.addPlot(row=1, col=0)
		self.current.setTitle("Current")
		self.current.setYRange(-5,5)
		self.Load01CurrentLine = self.current.plot(x = self.TimeData,y = self.currentTimeHistory[LOAD_IND],pen = loadPen)
		self.Supply01CurrentLine = self.current.plot(x = self.TimeData,y = self.currentTimeHistory[SUPPLY_IND], pen = supplyPen)
		self.ConvCurrentLine = self.current.plot(x = self.TimeData,y = self.currentTimeHistory[CONV_IND], pen = convPen)
		self.setCurrentLine = self.current.plot(x = self.TimeData,y = self.currentTimeHistory[SET_IND], pen = setPen)
		
		elecLegend = self.current.addLegend()
		elecLegend.addItem(name = "Supply",item = self.Supply01CurrentLine)
		elecLegend.addItem(name = "Conv",item = self.ConvCurrentLine)
		elecLegend.addItem(name = "Load",item = self.Load01CurrentLine)
		elecLegend.addItem(name = "Set",item = self.setCurrentLine)
		
		self.temperature = self.w.addPlot(row=2, col=0)
		self.temperature.setTitle("Temp (F)")
		self.temperature.setYRange(0,150)
		
		self.ambientTempFLine = self.temperature.plot(x = self.TimeData,y = self.tempTimeHistory[TEMP_AMB_IND], pen = ambPen)
		self.probeTempFLine = self.temperature.plot(x = self.TimeData,y = self.tempTimeHistory[TEMP_MEASURE_IND], pen = probePen)
		self.convTempFLine = self.temperature.plot(x = self.TimeData,y = self.tempTimeHistory[TEMP_SENSE_IND], pen = convPen)
		
		tempLegend = self.temperature.addLegend()
		tempLegend.addItem(name = "Amb",item = self.ambientTempFLine)
		tempLegend.addItem(name = "Prob",item = self.probeTempFLine)
		tempLegend.addItem(name = "Conv",item = self.convTempFLine)
		
		self.supplyStatus = equipmentStatusWidget('SUPPLY')
		
		self.loadStatus = equipmentStatusWidget('LOAD')
		
		self.tempStatus = tempStatusWidget()
		
		self.converterStatus = converterStatusWidget()
		
		equipmentLayout = QVBoxLayout()
		equipmentLayout.addWidget(self.supplyStatus)
		equipmentLayout.addWidget(self.loadStatus)
		equipmentLayout.addWidget(self.tempStatus)
		equipmentLayout.addWidget(self.converterStatus)
        
		self.mainLayout = QHBoxLayout()
		self.mainLayout.addLayout(controlLayout)
		self.mainLayout.addWidget(self.w)
		self.mainLayout.addLayout(equipmentLayout)
        
        
		self.setLayout(self.mainLayout)
        
	def update(self,t,voltData,currentData,tempData):
		# This is to update the graphing, not the immediate measured displays
		
		self.TimeData.append(t)
		
		if LOAD_01_ERROR == None:
			self.voltTimeHistory[LOAD_IND].append(voltData[LOAD_IND])
			self.currentTimeHistory[LOAD_IND].append(currentData[LOAD_IND])
			self.currentTimeHistory[SET_IND].append(currentData[SET_IND])
			
			self.Load01VoltLine.setData(self.voltTimeHistory[LOAD_IND])
			self.Load01CurrentLine.setData(self.currentTimeHistory[LOAD_IND])
			self.setVoltLine.setData(self.currentTimeHistory[SET_IND])
			
			
		if SUPPLY_ERROR == None:
			self.voltTimeHistory[SUPPLY_IND].append(voltData[SUPPLY_IND])
			self.voltTimeHistory[SET_IND].append(voltData[SET_IND])
			self.currentTimeHistory[SUPPLY_IND].append(currentData[SUPPLY_IND])
		
			self.Supply01VoltLine.setData(self.voltTimeHistory[SUPPLY_IND])
			self.setCurrentLine.setData(self.voltTimeHistory[SET_IND])
			self.Supply01CurrentLine.setData(self.currentTimeHistory[SUPPLY_IND])
			
		if TEMP_ERROR == None:
			self.tempTimeHistory[TEMP_AMB_IND].append(float(tempData[TEMP_AMB_IND]))
			self.tempTimeHistory[TEMP_MEASURE_IND].append(float(tempData[TEMP_MEASURE_IND]))
			self.tempTimeHistory[TEMP_SENSE_IND].append(float(tempData[TEMP_SENSE_IND]))
			
			self.ambientTempFLine.setData(self.tempTimeHistory[TEMP_AMB_IND])
			self.probeTempFLine.setData(self.tempTimeHistory[TEMP_MEASURE_IND])
			self.convTempFLine.setData(self.tempTimeHistory[TEMP_SENSE_IND])
			
			self.voltTimeHistory[CONV_IND].append(voltData[CONV_IND])
			self.currentTimeHistory[CONV_IND].append(currentData[CONV_IND])
			
			self.ConvVoltLine.setData(self.voltTimeHistory[CONV_IND])
			self.ConvCurrentLine.setData(self.currentTimeHistory[CONV_IND])
			
	def updateSupply(self,idnstr,statestr,funcstr,currfl,voltfl,voltSet,powerfl):
		
		self.voltControl.updateMeasured(voltSet)
		self.supplyStatus.update(idnstr,statestr,funcstr,currfl,voltfl,powerfl)
		
	def updateLoad(self,idnstr,statestr,funcstr,currfl,voltfl,currSet,powerfl):
		self.currentControl.updateMeasured(currSet)
		self.loadStatus.update(idnstr,statestr,funcstr,currfl,voltfl,powerfl)
		
	def updateTemp(self,stateVal,tempValues):
		
		self.tempStatus.update(stateVal,tempValues)
		
	def updateConv(self,stateVal,convValues,inPower):
		
		self.converterStatus.update(stateVal,convValues,inPower)
			
		
		
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
        

        #outstr = f'{value:.4f}'
        self.measuredDisp.setText(str(value))
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
        
        labelFont = 8
        valueFont = 10
        valueLabelWidth = 80
        valueLabelHeight = 20
        
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
        stateTitleLabel.setFont(QFont(fontName, labelFont))
        
        self.stateValueLabel = QLabel('5.432')
        self.stateValueLabel.setFont(QFont(fontName, valueFont))
        self.stateValueLabel.setStyleSheet("""
        background-color: white;
        color: black;
        border: 1px solid black;
        """)
        self.stateValueLabel.setAlignment(Qt.AlignCenter)
        self.stateValueLabel.setMinimumSize(valueLabelWidth,valueLabelHeight)
        self.stateValueLabel.setMaximumSize(valueLabelWidth,valueLabelHeight)
        
        stateLayout = QHBoxLayout()
        stateLayout.addWidget(stateTitleLabel)
        stateLayout.addWidget(self.stateValueLabel)
        
        ####### Function
        functionTitleLabel = QLabel('Function')
        functionTitleLabel.setFont(QFont(fontName, labelFont))
        
        self.functionValueLabel = QLabel('5.432')
        self.functionValueLabel.setFont(QFont(fontName, valueFont))
        self.functionValueLabel.setStyleSheet("""
        background-color: white;
        color: black;
        border: 1px solid black;
        """)
        self.functionValueLabel.setAlignment(Qt.AlignCenter)
        self.functionValueLabel.setMinimumSize(valueLabelWidth,valueLabelHeight)
        self.functionValueLabel.setMaximumSize(valueLabelWidth,valueLabelHeight)
        
        functionLayout = QHBoxLayout()
        functionLayout.addWidget(functionTitleLabel)
        functionLayout.addWidget(self.functionValueLabel)
        
        ####### Current
        currentTitleLabel = QLabel('Current')
        currentTitleLabel.setFont(QFont(fontName, labelFont))
        
        self.currentValueLabel = QLabel('5.432')
        self.currentValueLabel.setFont(QFont(fontName, valueFont))
        self.currentValueLabel.setStyleSheet("""
        background-color: white;
        color: black;
        border: 1px solid black;
        """)
        self.currentValueLabel.setAlignment(Qt.AlignCenter)
        self.currentValueLabel.setMinimumSize(valueLabelWidth,valueLabelHeight)
        self.currentValueLabel.setMaximumSize(valueLabelWidth,valueLabelHeight)
        
        currentLayout = QHBoxLayout()
        currentLayout.addWidget(currentTitleLabel)
        currentLayout.addWidget(self.currentValueLabel)
        
        ####### Voltage
        voltTitleLabel = QLabel('Volt')
        voltTitleLabel.setFont(QFont(fontName, labelFont))
        
        self.voltValueLabel = QLabel('5.432')
        self.voltValueLabel.setFont(QFont(fontName, valueFont))
        self.voltValueLabel.setStyleSheet("""
        background-color: white;
        color: black;
        border: 1px solid black;
        """)
        self.voltValueLabel.setAlignment(Qt.AlignCenter)
        self.voltValueLabel.setMinimumSize(valueLabelWidth,valueLabelHeight)
        self.voltValueLabel.setMaximumSize(valueLabelWidth,valueLabelHeight)
        
        voltLayout = QHBoxLayout()
        voltLayout.addWidget(voltTitleLabel)
        voltLayout.addWidget(self.voltValueLabel)
        
        ####### Power
        powerTitleLabel = QLabel('Power')
        powerTitleLabel.setFont(QFont(fontName, labelFont))
        
        self.powerValueLabel = QLabel('5.432')
        self.powerValueLabel.setFont(QFont(fontName, valueFont))
        self.powerValueLabel.setStyleSheet("""
        background-color: white;
        color: black;
        border: 1px solid black;
        """)
        self.powerValueLabel.setAlignment(Qt.AlignCenter)
        self.powerValueLabel.setMinimumSize(valueLabelWidth,valueLabelHeight)
        self.powerValueLabel.setMaximumSize(valueLabelWidth,valueLabelHeight)
        
        powerLayout = QHBoxLayout()
        powerLayout.addWidget(powerTitleLabel)
        powerLayout.addWidget(self.powerValueLabel)
        
        
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
        mainLayout.addLayout(powerLayout)
        
        self.setLayout(mainLayout)
        
    def update(self,idnstr,statestr,funcstr,currfl,voltfl,powerfl):
		
        #print(idnstr)
        idlist = idnstr.split(',')
        #print(idlist[0])
        self.stateValueLabel.setText(statestr)
        self.functionValueLabel.setText(str(funcstr))
        if voltfl != None:
            self.voltValueLabel.setText(f'{voltfl:.2f}')
        else:
            self.voltValueLabel.setText('')
        if currfl != None:
            self.currentValueLabel.setText(f'{currfl:.2f}')
        else:
            self.currentValueLabel.setText('')
        if powerfl != None:
            self.powerValueLabel.setText(f'{powerfl:.2f}')
        else:
            self.powerValueLabel.setText('')
        
class tempStatusWidget(QGroupBox):
    
    def __init__(self):
        
        super().__init__()
        
        self.setTitle("TEMP")
        
        labelFont = 8
        valueFont = 10
        valueLabelWidth = 80
        valueLabelHeight = 20
        
        
        ####### State
        stateTitleLabel = QLabel('State')
        stateTitleLabel.setFont(QFont(fontName, labelFont))
        
        self.stateValueLabel = QLabel('5.432')
        self.stateValueLabel.setFont(QFont(fontName, valueFont))
        self.stateValueLabel.setStyleSheet("""
        background-color: white;
        color: black;
        border: 1px solid black;
        """)
        self.stateValueLabel.setAlignment(Qt.AlignCenter)
        self.stateValueLabel.setMinimumSize(valueLabelWidth,valueLabelHeight)
        self.stateValueLabel.setMaximumSize(valueLabelWidth,valueLabelHeight)
        
        stateLayout = QHBoxLayout()
        stateLayout.addWidget(stateTitleLabel)
        stateLayout.addWidget(self.stateValueLabel)
        
        ####### amb
        ambTitleLabel = QLabel('Ambient')
        ambTitleLabel.setFont(QFont(fontName, labelFont))
        
        self.ambValueLabel = QLabel('5.432')
        self.ambValueLabel.setFont(QFont(fontName, valueFont))
        self.ambValueLabel.setStyleSheet("""
        background-color: white;
        color: black;
        border: 1px solid black;
        """)
        self.ambValueLabel.setAlignment(Qt.AlignCenter)
        self.ambValueLabel.setMinimumSize(valueLabelWidth,valueLabelHeight)
        self.ambValueLabel.setMaximumSize(valueLabelWidth,valueLabelHeight)
        
        ambLayout = QHBoxLayout()
        ambLayout.addWidget(ambTitleLabel)
        ambLayout.addWidget(self.ambValueLabel)
        
        ####### Voltage
        targetTitleLabel = QLabel('Measured')
        targetTitleLabel.setFont(QFont(fontName, labelFont))
        
        self.targetValueLabel = QLabel('5.432')
        self.targetValueLabel.setFont(QFont(fontName, valueFont))
        self.targetValueLabel.setStyleSheet("""
        background-color: white;
        color: black;
        border: 1px solid black;
        """)
        self.targetValueLabel.setAlignment(Qt.AlignCenter)
        self.targetValueLabel.setMinimumSize(valueLabelWidth,valueLabelHeight)
        self.targetValueLabel.setMaximumSize(valueLabelWidth,valueLabelHeight)
        
        targetLayout = QHBoxLayout()
        targetLayout.addWidget(targetTitleLabel)
        targetLayout.addWidget(self.targetValueLabel)
        
        ####### Voltage
        sensedTitleLabel = QLabel('Sensed')
        sensedTitleLabel.setFont(QFont(fontName, labelFont))
        
        self.sensedValueLabel = QLabel('5.432')
        self.sensedValueLabel.setFont(QFont(fontName, valueFont))
        self.sensedValueLabel.setStyleSheet("""
        background-color: white;
        color: black;
        border: 1px solid black;
        """)
        self.sensedValueLabel.setAlignment(Qt.AlignCenter)
        self.sensedValueLabel.setMinimumSize(valueLabelWidth,valueLabelHeight)
        self.sensedValueLabel.setMaximumSize(valueLabelWidth,valueLabelHeight)
        
        sensedLayout = QHBoxLayout()
        sensedLayout.addWidget(sensedTitleLabel)
        sensedLayout.addWidget(self.sensedValueLabel)
        
        mainLayout = QVBoxLayout()
        #mainLayout.addWidget(titleLabel)

        mainLayout.addLayout(stateLayout)
        mainLayout.addLayout(ambLayout)
        mainLayout.addLayout(targetLayout)
        mainLayout.addLayout(sensedLayout)
        
        self.setLayout(mainLayout)
        
    def update(self,stateVal,tempValues):
        self.stateValueLabel.setText(stateVal)
        self.ambValueLabel.setText(tempValues[0])
        self.targetValueLabel.setText(tempValues[1])
        self.sensedValueLabel.setText(tempValues[2])
        
class converterStatusWidget(QGroupBox):
    
    def __init__(self):
        
        super().__init__()
        
        self.setTitle("CONVERTER")
        
        labelFont = 8
        valueFont = 10
        valueLabelWidth = 80
        valueLabelHeight = 20
        
        ####### State
        stateTitleLabel = QLabel('State')
        stateTitleLabel.setFont(QFont(fontName, labelFont))
        
        self.stateValueLabel = QLabel('5.432')
        self.stateValueLabel.setFont(QFont(fontName, valueFont))
        self.stateValueLabel.setStyleSheet("""
        background-color: white;
        color: black;
        border: 1px solid black;
        """)
        self.stateValueLabel.setAlignment(Qt.AlignCenter)
        self.stateValueLabel.setMinimumSize(valueLabelWidth,valueLabelHeight)
        self.stateValueLabel.setMaximumSize(valueLabelWidth,valueLabelHeight)
        
        stateLayout = QHBoxLayout()
        stateLayout.addWidget(stateTitleLabel)
        stateLayout.addWidget(self.stateValueLabel)
        
        ####### amb
        voltTitleLabel = QLabel('Voltage')
        voltTitleLabel.setFont(QFont(fontName, labelFont))
        
        self.voltValueLabel = QLabel('5.432')
        self.voltValueLabel.setFont(QFont(fontName, valueFont))
        self.voltValueLabel.setStyleSheet("""
        background-color: white;
        color: black;
        border: 1px solid black;
        """)
        self.voltValueLabel.setAlignment(Qt.AlignCenter)
        self.voltValueLabel.setMinimumSize(valueLabelWidth,valueLabelHeight)
        self.voltValueLabel.setMaximumSize(valueLabelWidth,valueLabelHeight)
        
        voltLayout = QHBoxLayout()
        voltLayout.addWidget(voltTitleLabel)
        voltLayout.addWidget(self.voltValueLabel)
        
        ####### Voltage
        currTitleLabel = QLabel('Current')
        currTitleLabel.setFont(QFont(fontName, labelFont))
        
        self.currValueLabel = QLabel('5.432')
        self.currValueLabel.setFont(QFont(fontName, valueFont))
        self.currValueLabel.setStyleSheet("""
        background-color: white;
        color: black;
        border: 1px solid black;
        """)
        self.currValueLabel.setAlignment(Qt.AlignCenter)
        self.currValueLabel.setMinimumSize(valueLabelWidth,valueLabelHeight)
        self.currValueLabel.setMaximumSize(valueLabelWidth,valueLabelHeight)
        
        currLayout = QHBoxLayout()
        currLayout.addWidget(currTitleLabel)
        currLayout.addWidget(self.currValueLabel)
        
        ####### Voltage
        powerTitleLabel = QLabel('Power')
        powerTitleLabel.setFont(QFont(fontName, labelFont))
        
        self.powerValueLabel = QLabel('5.432')
        self.powerValueLabel.setFont(QFont(fontName, valueFont))
        self.powerValueLabel.setStyleSheet("""
        background-color: white;
        color: black;
        border: 1px solid black;
        """)
        self.powerValueLabel.setAlignment(Qt.AlignCenter)
        self.powerValueLabel.setMinimumSize(valueLabelWidth,valueLabelHeight)
        self.powerValueLabel.setMaximumSize(valueLabelWidth,valueLabelHeight)
        
        powerLayout = QHBoxLayout()
        powerLayout.addWidget(powerTitleLabel)
        powerLayout.addWidget(self.powerValueLabel)
        
        ####### Voltage
        effTitleLabel = QLabel('Efficiency')
        effTitleLabel.setFont(QFont(fontName, labelFont))
        
        self.effValueLabel = QLabel('5.432')
        self.effValueLabel.setFont(QFont(fontName, valueFont))
        self.effValueLabel.setStyleSheet("""
        background-color: white;
        color: black;
        border: 1px solid black;
        """)
        self.effValueLabel.setAlignment(Qt.AlignCenter)
        self.effValueLabel.setMinimumSize(valueLabelWidth,valueLabelHeight)
        self.effValueLabel.setMaximumSize(valueLabelWidth,valueLabelHeight)
        
        effLayout = QHBoxLayout()
        effLayout.addWidget(effTitleLabel)
        effLayout.addWidget(self.effValueLabel)
        
        
        mainLayout = QVBoxLayout()
        #mainLayout.addWidget(titleLabel)

        mainLayout.addLayout(stateLayout)
        mainLayout.addLayout(voltLayout)
        mainLayout.addLayout(currLayout)
        mainLayout.addLayout(powerLayout)
        mainLayout.addLayout(effLayout)
        
        self.setLayout(mainLayout)
        
    def update(self,stateVal,convValues,inPower):
        self.stateValueLabel.setText(stateVal)
        self.voltValueLabel.setText(convValues[0])
        self.currValueLabel.setText(convValues[1])
        self.powerValueLabel.setText(convValues[2])
        
        try:
            eff = float(convValues[2])/inPower
            outStr = f'{eff:3.2f}'
        except:
            outStr = "Error"
        self.effValueLabel.setText(outStr)



if __name__ == '__main__':
    
    app = QApplication(sys.argv)
    
    
    mw = mainWin()
    
    sys.exit(app.exec_()) 
