#!/usr/bin/python
import RPi.GPIO as GPIO
import sys
import time
import datetime
import spidev
import smbus
import getopt
import xml.etree.ElementTree as ET
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.payload import BinaryPayloadBuilder
from pymodbus.client.sync import ModbusTcpClient as NetworkClient
from pymodbus.client.sync import ModbusSerialClient as SerialClient
#v1.0.1 CUSTOM TI
#Added Cal_Source_PF			22 May 2019
#Added Cal_Source_Harmonics		23 May 2019
#v1.0.2 CUSTOM TI
#Added Harmonics Support		25 Oct 2019
#Added Cal Source Harmonics PF	25 OCt 2019
#v1.0.3 CUSTOM TI
#Changed Cal Points 			29 Oct 2019
#v1.0.4 CUSTOM TI
#Added individual harmonic frequency control 13 Nov 2019
#V1.0.5
#Separated frequency control for VAux. Added Set_Freq_VAux(fout)
#use x60 to change frequency
#V1.0.6
#Added Cal for Vaux Phase
#Added AEh - Vaux-n Phase Angle in GetHighSpeedReadings
#v1.0.7
#Added Cal for v2,v3,v4  - Cal-PF
#v1.0.8 7 april 2020
#Combine Funda and Harmonic Calibration
#CAL FUNDA then CAL HARMONICS USING vaux/vIms
#Do not calibrate Vaux harmonics/Im Harmonics
#Fixed error in cal ip
#v1.0.9 14 October 2024
#Raspbian Bookworm
#v1.0.10 22 November 2024
#Write user input in the db file

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(27, GPIO.OUT)	#set relay 1 to Set
GPIO.setup(18, GPIO.OUT)	#set relay 1 to Reset
GPIO.setup(22, GPIO.OUT)	#set relay 2 to Set
GPIO.setup(23, GPIO.OUT)	#set relay 2 to Reset
GPIO.setup(24, GPIO.OUT)	#set relay 3 to NC
GPIO.setup(25, GPIO.OUT)	#set relay 4 to NC
GPIO.setup(8, GPIO.OUT)		#set relay 5 to NC
GPIO.setup(7, GPIO.OUT)		#set relay 6 to NC

#communication bus registers
bus = smbus.SMBus(1) # 1 = /dev/i2c-1 (port I2C1)
spi = spidev.SpiDev()
input_parameter = ''
MCLK = 1000000
#spi mode must be set to 2 in order for the spi clk to be idle high and the data to be read on the falling edge for the waveform chips
#the spi mode must be set to 0 in order to talk to the digital pot chip
#need to send a dummy output to make sure spi clk line is synced accordingly to get correct ouput on chips
spi.open(0,0)
spi.max_speed_hz = 4000000

#parse data in the arguments (all strings) and assign to each according variable
try:
	opts, args = getopt.getopt(sys.argv[1:],"hi:")
except getopt.GetoptError as err:
	print ('One of the arguments entered was invalid. Consult the help menu by using argument -h to see all available arguments.')
	print (err)
	sys.exit(2)
for opt, arg in opts:
	if (opt == '-h'):
		print('wave_test.py -i <input parameter>')
		print('wave_test.py -h <help>')
		sys.exit()
	elif (opt == "-i"):
		input_parameter = arg
##########################################################
# i2c addresses of the PCA9557 chips for different phases:
# Va and Ia = 0x1C
# Vb and Ib = 0x1D
# Vc and Vc = 0x1E
# Vn and In = 0x1F
##########################################################
#ALL OF THIS CODE COMMENTED OUT IS NOW HANDLED IN THE WAVE_INIT.SH FILE WHICH INITIALIZES THE SYSTEM
#GPIO COMMANDS FOR CLOCK PIN 7
#gpio -g mode 4 clock
#gpio -g clock 4 1000000 #this sets clock freq to 1 MHz
#print "setting up GPIO"
#GPIO.setmode(GPIO.BOARD)
#GPIO.setwarnings(False)
#set pin 11 to output and set the output high so the pca9557 chips are not in reset mode.
#GPIO.setup(11,GPIO.OUT)
#GPIO.output(11,GPIO.HIGH)
#print "seting up PCA9557 GPIO"
#Write a single register one at a time
#bus.write_byte_data(0x1C, 0x01, 0xFF) #set all pca9557 output gpio to low
#bus.write_byte_data(0x1C, 0x02, 0x00) #set all pca9557 gpio ploarity to zero
#bus.write_byte_data(0x1C, 0x03, 0x00) #set all pca9557 gpio to output mode
#write block of registers
#bus.write_i2c_block_data(DEVICE_ADDRESS, DEVICE_REG_LEDOUT0, values)
#bus.write_i2c_block_data(0x1C, 0x01, (0xFF, 0x00, 0x00) )

#Calculating Freq Register: (AD9833)
def Set_Freq(fout):
	#check if the frequency is between 10hz and 100khz
	if (fout >= 10 and fout <= 100000):

		spi.mode = 2 #set spi to mode 2 so SCLK is idle high and read data on the falling edge
		r = spi.xfer([0x00]) #send dummy command to make sure spi is in correct setting
		#max fout is MCLK/2
		freq_reg = (fout/MCLK) * 2**28
		#Check to make sure the freq_reg is less than or equal to 2^28 - 1 
		LSB = int(freq_reg) & 0x3FFF
		MSB = (int(freq_reg) & 0xFFFC000) >> 14
		#if freq0 selected:
		LSB = LSB | 0x4000
		MSB = MSB | 0x4000

		#split up each word into 2 bytes so it can be sent with the spi.xfer2 command
		freqLSB_MSB = (LSB & 0xFF00) >> 8
		freqLSB_LSB = (LSB & 0x00FF)
		freqMSB_MSB = (MSB & 0xFF00) >> 8
		freqMSB_LSB = (MSB & 0x00FF)            
		#send the frequency data to all of the AD9833 chips on all phase outputs
		bus.write_byte_data(0x1C, 0x01, 0x5F)
		bus.write_byte_data(0x1D, 0x01, 0x5F)
		bus.write_byte_data(0x1E, 0x01, 0x5F)
		bus.write_byte_data(0x1F, 0x01, 0x5F)

		spi.xfer2([0x20, 0x00]) #control word 
		print("111")
		#return


		spi.xfer2([freqLSB_MSB, freqLSB_LSB]) #send LSB freq data to freq register 0.
		spi.xfer2([freqMSB_MSB, freqMSB_LSB]) #send MSB freq data to freq register 0.   
		bus.write_byte_data(0x1C, 0x01, 0xFF)
		bus.write_byte_data(0x1D, 0x01, 0xFF)
		bus.write_byte_data(0x1E, 0x01, 0xFF)
		bus.write_byte_data(0x1F, 0x01, 0xFF)           
		Write_Global_Status(xmltree, root, "frequency", fout)
		Synchronize(root, 0x5F, 0x5F, 0x5F, 0x5F)
		
def Set_Freq_VAux(fout):
	#check if the frequency is between 10hz and 100khz
	if (fout >= 10 and fout <= 100000):
		spi.mode = 2 #set spi to mode 2 so SCLK is idle high and read data on the falling edge
		r = spi.xfer([0x00]) #send dummy command to make sure spi is in correct setting
		#max fout is MCLK/2
		freq_reg = (fout/MCLK) * 2**28
		#Check to make sure the freq_reg is less than or equal to 2^28 - 1 
		LSB = int(freq_reg) & 0x3FFF
		MSB = (int(freq_reg) & 0xFFFC000) >> 14
		#if freq0 selected:
		LSB = LSB | 0x4000
		MSB = MSB | 0x4000
		#split up each word into 2 bytes so it can be sent with the spi.xfer2 command
		freqLSB_MSB = (LSB & 0xFF00) >> 8
		freqLSB_LSB = (LSB & 0x00FF)
		freqMSB_MSB = (MSB & 0xFF00) >> 8
		freqMSB_LSB = (MSB & 0x00FF)            
		#send the frequency data to all of the AD9833 chips on all phase outputs
		bus.write_byte_data(0x1F, 0x01, 0x7F)
		spi.xfer2([0x20, 0x00]) #control word 
		spi.xfer2([freqLSB_MSB, freqLSB_LSB]) #send LSB freq data to freq register 0.
		spi.xfer2([freqMSB_MSB, freqMSB_LSB]) #send MSB freq data to freq register 0.   
		bus.write_byte_data(0x1F, 0x01, 0xFF)           
		#Write_Global_Status(xmltree, root, "frequency", fout)
		#Synchronize(root, 0xFF, 0xFF, 0xFF, 0x7F)        
        
def Set_Freq_Harmonics(fout, chip_select, i2c_chip_address):
	#check if the frequency is between 8hz and 100khz - Flicker 8.8Hz
	if (fout >= 8 and fout <= 100000):
		spi.mode = 2 #set spi to mode 2 so SCLK is idle high and read data on the falling edge
		r = spi.xfer([0x00]) #send dummy command to make sure spi is in correct setting
		#max fout is MCLK/2
		freq_reg = (fout/MCLK) * 2**28
		#Check to make sure the freq_reg is less than or equal to 2^28 - 1 
		LSB = int(freq_reg) & 0x3FFF
		MSB = (int(freq_reg) & 0xFFFC000) >> 14
		#if freq0 selected:
		LSB = LSB | 0x4000
		MSB = MSB | 0x4000
		#split up each word into 2 bytes so it can be sent with the spi.xfer2 command
		freqLSB_MSB = (LSB & 0xFF00) >> 8
		freqLSB_LSB = (LSB & 0x00FF)
		freqMSB_MSB = (MSB & 0xFF00) >> 8
		freqMSB_LSB = (MSB & 0x00FF)            
		#send the frequency data to all of the AD9833 chips on all phase outputs
		bus.write_byte_data(i2c_chip_address, 0x01, chip_select)
		spi.xfer2([0x20, 0x00]) #control word 
		spi.xfer2([freqLSB_MSB, freqLSB_LSB]) #send LSB freq data to freq register 0.
		spi.xfer2([freqMSB_MSB, freqMSB_LSB]) #send MSB freq data to freq register 0.   
		bus.write_byte_data(i2c_chip_address, 0x01, 0xFF)           
		#Write_Global_Status(xmltree, root, "frequency", fout)
		#Synchronize(root, 0x5F, 0x5F, 0x5F, 0x5F)

#Calculating phase_angle Register: (AD9833)
def Set_phase_angle(phase_shift, chip_select, i2c_chip_address):
	#check if the phase shift is between 0 and 360 degrees
	if (phase_shift >= 0 and phase_shift <= 360):
		spi.mode = 2 #set spi to mode 2 so SCLK is idle high and read data on the falling edge
		r = spi.xfer([0x00]) #send dummy command to make sure spi is in correct setting
		#Add the -1 constant here since the REV_C boards have the voltage transformers reversed so we use the -1 to make the phase angles lagging.
		phase_radians = phase_shift * -1 * 3.1415926535897932384626433832795 / 180 
		phase_reg = phase_radians * 4096 / (2 * 3.1415926535897932384626433832795)
		#where 0 < delta_phase < 4095
		#Check to make sure the phase_reg is less than or equal to 4095
		phase_reg = int(phase_reg) & 0xFFF
		#if phase0 selected:
		phase_data = phase_reg | 0xC000 #add the control bits at the beginning of the word to send phase data to phase register 0
		#if phase1 selected:
		#       phase_data = phase_reg | 0xE000
		#split up the word into 2 bytes so it can be sent with the spi.xfer2 command
		phaseMSB = (phase_data & 0xFF00) >> 8
		phaseLSB = (phase_data & 0x00FF)
		#send the phase data
		bus.write_byte_data(i2c_chip_address, 0x01, chip_select)
		spi.xfer2([phaseMSB, phaseLSB])
		bus.write_byte_data(i2c_chip_address, 0x01, 0xFF)
	
#Set Output Waveform (AD9833)
def Set_Output_Waveform(wave_type, chip_select, i2c_chip_address):      
	spi.mode = 2 #set spi to mode 2 so SCLK is idle high and read data on the falling edge
	r = spi.xfer([0x00]) #send dummy command to make sure spi is in correct setting
	if (wave_type == "sine"):
		#set freq0 to output a sine wave
		bus.write_byte_data(i2c_chip_address, 0x01, chip_select)        
		r = spi.xfer2([0x00, 0x00])
		bus.write_byte_data(i2c_chip_address, 0x01, 0xFF)
	elif (wave_type == "tri"):
		#set freq0 to output a triangular wave
		bus.write_byte_data(i2c_chip_address, 0x01, chip_select)
		r = spi.xfer2([0x00, 0x02])
		bus.write_byte_data(i2c_chip_address, 0x01, 0xFF)
	#elif (wave_type == "squ"):
	#	#set freq0 to output square wave
	#	bus.write_byte_data(i2c_chip_address, 0x01, chip_select)
	#	r = spi.xfer2([0x00, 0x20])
	#	bus.write_byte_data(i2c_chip_address, 0x01, 0xFF)

#Send Magnitude (AD5160)
def Set_Magnitude(mag, curr_mag, chip_select, i2c_chip_address):
	#check if the magnitude is between 0 and 255 since that is the resolutio of the digital pot chip
	if (mag >= 0 and mag <= 255):
		print(mag)
		spi.mode = 0 #set spi to mode 0 so SCLK is idle low and read data on the rising edge
		spi.xfer([0x00]) #send dummy command to put spi in correct mode         
		#create a function that will calculate the difference between the current mag setting and the desired setting and ramp there in steps. we only need to ramp if the magnitude is a difference of 2 or greater. If the desired mag is still a difference of greater than 50 then we will ramp another incrememnt of 1 until the desired mag is less than 2 away from the current mag, then we will set the output to the desired mag.
		stepsize = 1
		while (abs(mag - curr_mag) >= stepsize):
			if ((mag - curr_mag) < 0):
				curr_mag = curr_mag - stepsize
			else:
				curr_mag = curr_mag + stepsize
			bus.write_byte_data(i2c_chip_address, 0x01, chip_select)
			spi.xfer([mag])
			bus.write_byte_data(i2c_chip_address, 0x01, 0xFF)       
			time.sleep(0.001)               
		
#reset ouputs to default state
def Reset(rootdir):
	values_string = ["v1","v2","v3","v4","c1","c2","c3","c4", "v1h","v2h","v3h","v4h","c1h","c2h","c3h","c4h"]
	i2c_values = [0x1C, 0x1D, 0x1E, 0x1F, 0x1C, 0x1D, 0x1E, 0x1F, 0x1C, 0x1D, 0x1E, 0x1F, 0x1C, 0x1D, 0x1E, 0x1F]
	mag_chip_values = [0xBF, 0xBF, 0xBF, 0xBF, 0xEF, 0xEF, 0xEF, 0xEF, 0xFB, 0xFB, 0xFB, 0xFB, 0xFE, 0xFE, 0xFE, 0xFE]
	freq_chip_values = [0x7F, 0x7F, 0x7F, 0x7F, 0xDF,  0xDF, 0xDF, 0xDF, 0xF7, 0xF7, 0xF7, 0xF7, 0xFD, 0xFD, 0xFD, 0xFD]
	phase_angle_values = [0, 120, 240, 0, 0, 120, 240, 0, 0, 120, 240, 0, 0, 120, 240, 0] 
	Set_Freq(60.0) #Set the frequency to 60Hz
	#set all phase to 0 mag, 60hz, default wye phase angles, and the output state off
	for x in range(0,16):
		current_value = int(Read_One_Parameter(rootdir, values_string[x], "magnitude"))
		Set_phase_angle(phase_angle_values[x], freq_chip_values[x], i2c_values[x])      
		Set_Magnitude(0, current_value, mag_chip_values[x], i2c_values[x])
		Output_Channel_Off(freq_chip_values[x], i2c_values[x])
		Write_Status(xmltree, rootdir, values_string[x], "magnitude", 0)
		Write_Status(xmltree, rootdir, values_string[x], "phase", phase_angle_values[x])
		Write_Status(xmltree, rootdir, values_string[x], "state", "OFF")
	
def Synchronize(rootdir, A_phase_output, B_phase_output, C_phase_output, X_phase_output):
	spi.mode = 2 #set spi to mode 2 so SCLK is idle high and read data on the falling edge
	r = spi.xfer([0x00]) #send dummy command to make sure spi is in correct setting 
	#Toggle the chip select for all of the AD9833 chips
	bus.write_byte_data(0x1C, 0x01, 0x55)
	bus.write_byte_data(0x1D, 0x01, 0x55)
	bus.write_byte_data(0x1E, 0x01, 0x55)
	bus.write_byte_data(0x1F, 0x01, 0x55)
	spi.xfer2([0x01, 0x00]) #send reset control word to all AD9833 chips
	bus.write_byte_data(0x1C, 0x01, 0xFF)
	bus.write_byte_data(0x1D, 0x01, 0xFF)
	bus.write_byte_data(0x1E, 0x01, 0xFF)
	bus.write_byte_data(0x1F, 0x01, 0xFF)
	time.sleep(0.1)
	#Toggle the chip select for all of the selected AD9833 chips leaving all unselected ones in reset mode
	bus.write_byte_data(0x1C, 0x01, A_phase_output)
	bus.write_byte_data(0x1D, 0x01, B_phase_output)
	bus.write_byte_data(0x1E, 0x01, C_phase_output)
	bus.write_byte_data(0x1F, 0x01, X_phase_output)
	spi.xfer2([0x00, 0x00]) #send control word to selected AD9833 chips to take them out of reset mode
	bus.write_byte_data(0x1C, 0x01, 0xFF)
	bus.write_byte_data(0x1D, 0x01, 0xFF)
	bus.write_byte_data(0x1E, 0x01, 0xFF)
	bus.write_byte_data(0x1F, 0x01, 0xFF)
		
#put selected frequency generator chip into reset mode to turn it's output off (AD9833)
def Output_Channel_Off(chip_select, i2c_chip_address):
	spi.mode = 2 #set spi to mode 2 so SCLK is idle high and read data on the falling edge
	r = spi.xfer([0x00]) #send dummy command to make sure spi is in correct setting
	bus.write_byte_data(i2c_chip_address, 0x01, chip_select)        
	spi.xfer2([0x01, 0x00]) #send reset control word to ad9833 chip 
	bus.write_byte_data(i2c_chip_address, 0x01, 0xFF)
	
#take the selected frequency generator chip out of reset mode to turn it's output on (AD9833)
def Output_Channel_On(chip_select, i2c_chip_address):
	spi.mode = 2 #set spi to mode 2 so SCLK is idle high and read data on the falling edge
	r = spi.xfer([0x00]) #send dummy command to make sure spi is in correct setting
	bus.write_byte_data(i2c_chip_address, 0x01, chip_select)
	spi.xfer2([0x00, 0x00]) #send reset control word to ad9833 chip to take it out of reset mode
	bus.write_byte_data(i2c_chip_address, 0x01, 0xFF)
	
#read the current source settings from the TestDeptSourceParameters.xml and save it all in a list that is returned to the program
def Read_Last_Sent(rootdir):
	for subdir in rootdir:          
		channel = subdir.tag
		if (channel == "version" or channel == "serial_number" or channel == "cal_date" or channel == "freq_offset" or channel == "frequency"):
			value = subdir.text
			print ("%s: %s") %(channel, value)
		else:
			slope = subdir.findtext("avg_slope")
			mag = subdir.findtext("magnitude")
			phase = subdir.findtext("phase")
			phaseoff = subdir.findtext("phase_offset")
			shape = subdir.findtext("wave_shape")
			state = subdir.findtext("state")
			print ("%s: slope=%s, mag=%s, angle=%s, angle_offset=%s, wave=%s, state=%s") %(channel, slope, mag, phase, phaseoff, shape, state)
		
def Read_One_Parameter(rootdir, outputphase, outputparameter):
	channel = rootdir.find(outputphase)
	value = channel.findtext(outputparameter)
	return value

def Read_Global_Parameter(rootdir, parameter):
	return rootdir.findtext(parameter)
	
#write the current source settings to the TestDeptSourceParameters.xml file from the editted list in the program
def Write_Status(elementtree, rootdir, outputphase, outputparameter, value):
	phasedir = rootdir.find(outputphase)
	parameterdir = phasedir.find(outputparameter)
	parameterdir.text = str(value)
	elementtree.write('/home/pi/TestDeptSourceParameters.xml')

def Write_Global_Status(elementtree, rootdir, parameter, value):
	phasedir = rootdir.find(parameter)
	phasedir.text = str(value)
	elementtree.write('/home/pi/TestDeptSourceParameters.xml')
	
def SetAllZeroes():
	spi.mode = 0 #set spi to mode 0 so SCLK is idle low and read data on the rising edge
	spi.xfer([0x00]) #send dummy command to put spi in correct mode         
	bus.write_byte_data(0x1C, 0x01, 0xAA)
	bus.write_byte_data(0x1D, 0x01, 0xAA)
	bus.write_byte_data(0x1E, 0x01, 0xAA)
	bus.write_byte_data(0x1F, 0x01, 0xAA)
	spi.xfer([0x00])
	bus.write_byte_data(0x1C, 0x01, 0xFF)
	bus.write_byte_data(0x1D, 0x01, 0xFF)
	bus.write_byte_data(0x1E, 0x01, 0xFF)
	bus.write_byte_data(0x1F, 0x01, 0xFF)   
		
def Cal_Source(elementtree, rootdir, full_cal_option):
	#if the full_cal_option is True then the cal go up to mag 255 if it is false it will only go up to mag 100
	calpoints = [0,15,30,45,60,75]
	calstrings = ["mag0","mag50","mag100","mag150","mag200","mag255"]
	if (full_cal_option == True):
		endpoint = 6
	else:
		endpoint = 3 
	Reset(rootdir) #Send the Reset() command to make sure that all phases are in default state
	Synchronize(rootdir, 0x5F, 0x5F, 0x5F, 0x5F) #Send the Synchronize command to make sure the phases are on and synced    
	ourmeter = FeedBackMeter("172.20.90.241", 502, "RTU", 1)
	if (ourmeter.MeterConnected == False):
		print ("Could not connect to the meter so the Calibration could not be performed.")
	else:
		VanArray = []
		VbnArray = []
		VcnArray = []
		VxnArray = []
		IaArray = []
		IbArray = []
		IcArray = []
		InArray = []
		FreqArray = []
		VapArray = []
		VbpArray = []
		VcpArray = []
		VauxpArray = []
		IapArray = []
		IbpArray = []
		IcpArray = []
		curr_mag_v1 = int(Read_One_Parameter(rootdir, "v1", "magnitude"))
		curr_mag_v2 = int(Read_One_Parameter(rootdir, "v2", "magnitude"))
		curr_mag_v3 = int(Read_One_Parameter(rootdir, "v3", "magnitude"))
		curr_mag_v4 = int(Read_One_Parameter(rootdir, "v4", "magnitude"))
		curr_mag_c1 = int(Read_One_Parameter(rootdir, "c1", "magnitude"))
		curr_mag_c2 = int(Read_One_Parameter(rootdir, "c2", "magnitude"))
		curr_mag_c3 = int(Read_One_Parameter(rootdir, "c3", "magnitude"))
		curr_mag_c4 = int(Read_One_Parameter(rootdir, "c4", "magnitude"))
		for x in range(0,endpoint): #Set output to the cal magnitude on all voltage and current channels, then poll readings 10 times and take average. Repeat for magnitudes 50, and 100 (150, 200 and 255 are optional: since this might cause outputs too high for some meters we don't want to always go this high)
			print ("sending mag " + str(calpoints[x]))
			Set_Magnitude(calpoints[x], curr_mag_v1, 0xBF, 0x1C) #set mag for v1
			Set_Magnitude(calpoints[x], curr_mag_v2, 0xBF, 0x1D) #set mag for v2
			Set_Magnitude(calpoints[x], curr_mag_v3, 0xBF, 0x1E) #set mag for v3
			Set_Magnitude(calpoints[x], curr_mag_v4, 0xBF, 0x1F) #set mag for v4
			Set_Magnitude(calpoints[x], curr_mag_c1, 0xEF, 0x1C) #set mag for c1
			Set_Magnitude(calpoints[x], curr_mag_c2, 0xEF, 0x1D) #set mag for c2
			Set_Magnitude(calpoints[x], curr_mag_c3, 0xEF, 0x1E) #set mag for c3
			Set_Magnitude(calpoints[x], curr_mag_c4, 0xEF, 0x1F) #set mag for c4
			curr_mag_v1 = calpoints[x] #set the current mag variable to current cal point mag
			curr_mag_v2 = calpoints[x]
			curr_mag_v3 = calpoints[x]
			curr_mag_v4 = calpoints[x]
			curr_mag_c1 = calpoints[x]
			curr_mag_c2 = calpoints[x]
			curr_mag_c3 = calpoints[x]
			curr_mag_c4 = calpoints[x]
			time.sleep(5)
			voltA = 0.0
			voltB = 0.0
			voltC = 0.0
			voltX = 0.0
			currA = 0.0
			currB = 0.0
			currC = 0.0
			currN = 0.0
			freqavg = 0.0
			vap = 0.0
			vbp = 0.0
			vcp = 0.0
			vauxp = 0.0
			iap = 0.0
			ibp = 0.0
			icp = 0.0
			for y in range(0,10):
				ourmeter.GetHighSpeedReadings()
				if ourmeter.PollingSuccess == True:
					voltA += ourmeter.Van
					voltB += ourmeter.Vbn
					voltC += ourmeter.Vcn
					voltX += ourmeter.Vxn
					currA += ourmeter.Ia
					currB += ourmeter.Ib
					currC += ourmeter.Ic
					currN += ourmeter.In
					freqavg += ourmeter.Freq
					vap += ourmeter.VanP
					vbp += ourmeter.VbnP
					vcp += ourmeter.VcnP
					vauxp += ourmeter.VauxP
					iap += ourmeter.IaP
					ibp += ourmeter.IbP
					icp += ourmeter.IcP
				else:
					print ('Meter could not poll the one second readings correctly. Power Factor Calibration did not complete. Check reference meter and again.')
					break
			voltA = voltA / 10.0
			voltB = voltB / 10.0
			voltC = voltC / 10.0
			voltX = voltX / 10.0
			currA = currA / 10.0
			currB = currB / 10.0
			currC = currC / 10.0
			currN = currN / 10.0
			freqavg = freqavg / 10.0
			vap = vap / 10.0
			vbp = vbp / 10.0
			vcp = vcp / 10.0
			vauxp = vauxp / 10.0
			iap = iap / 10.0
			ibp = ibp / 10.0
			icp = icp / 10.0
			#Store the this average in the mag# spot in the xml for all channels    
			Write_Status(elementtree, rootdir, "v1", calstrings[x], voltA)
			Write_Status(elementtree, rootdir, "v2", calstrings[x], voltB)
			Write_Status(elementtree, rootdir, "v3", calstrings[x], voltC)
			Write_Status(elementtree, rootdir, "v4", calstrings[x], voltX)
			Write_Status(elementtree, rootdir, "c1", calstrings[x], currA)
			Write_Status(elementtree, rootdir, "c2", calstrings[x], currB)
			Write_Status(elementtree, rootdir, "c3", calstrings[x], currC)
			Write_Status(elementtree, rootdir, "c4", calstrings[x], currN)
			VanArray.append(voltA)
			VbnArray.append(voltB)
			VcnArray.append(voltC)
			VxnArray.append(voltX)
			IaArray.append(currA)
			IbArray.append(currB)
			IcArray.append(currC)
			InArray.append(currN)
			FreqArray.append(freqavg)
			VapArray.append(vap)
			VbpArray.append(vbp)
			VcpArray.append(vcp)
			VauxpArray.append(vauxp)
			IapArray.append(iap)
			IbpArray.append(ibp)
			IcpArray.append(icp)
		#Calculate slopes from 0 to 50, 50 to 100, 100 to 150, 150 to 200, 200 to 255
		VaSlope = 0.0
		VbSlope = 0.0
		VcSlope = 0.0
		VxSlope = 0.0
		IaSlope = 0.0
		IbSlope = 0.0
		IcSlope = 0.0
		InSlope = 0.0
		FreqOffset = 0.0
		VapOffset = 0.0
		VbpOffset = 0.0
		VcpOffset = 0.0
		VauxpOffset = 0.0
		IapOffset = 0.0
		IbpOffset = 0.0
		IcpOffset = 0.0
		for x in range(0, (endpoint - 1)):
			VaSlope += (VanArray[x+1]-VanArray[x])/(calpoints[x+1]-calpoints[x])
			VbSlope += (VbnArray[x+1]-VbnArray[x])/(calpoints[x+1]-calpoints[x])
			VcSlope += (VcnArray[x+1]-VcnArray[x])/(calpoints[x+1]-calpoints[x])
			VxSlope += (VxnArray[x+1]-VxnArray[x])/(calpoints[x+1]-calpoints[x])
			IaSlope += (IaArray[x+1]-IaArray[x])/(calpoints[x+1]-calpoints[x])
			IbSlope += (IbArray[x+1]-IbArray[x])/(calpoints[x+1]-calpoints[x])
			IcSlope += (IcArray[x+1]-IcArray[x])/(calpoints[x+1]-calpoints[x])
			InSlope += (InArray[x+1]-InArray[x])/(calpoints[x+1]-calpoints[x])
			FreqOffset += FreqArray[x+1]
			VapOffset += VapArray[x+1]
			VbpOffset += VbpArray[x+1]
			VcpOffset += VcpArray[x+1]
			VauxpOffset += VauxpArray[x+1]
			IapOffset += IapArray[x+1]
			IbpOffset += IbpArray[x+1]
			IcpOffset += IcpArray[x+1]
		##Average all of these slope and offset values and then store the average in the avg_slope spot in the xml for all channels
		VaSlope = VaSlope / (endpoint - 1)
		VbSlope = VbSlope / (endpoint - 1)
		VcSlope = VcSlope / (endpoint - 1)
		VxSlope = VxSlope / (endpoint - 1)
		IaSlope = IaSlope / (endpoint - 1)
		IbSlope = IbSlope / (endpoint - 1)
		IcSlope = IcSlope / (endpoint - 1)
		InSlope = InSlope / (endpoint - 1)
		freqavg = FreqOffset / (endpoint - 1)
		FreqOffset = (freqavg - 60.0) / 60.0 
		VapOffset = VapOffset / (endpoint - 1)
		VbpOffset = (VbpOffset / (endpoint - 1)) - 120.0
		VcpOffset = (VcpOffset / (endpoint - 1)) + 120.0
		VauxpOffset = VauxpOffset / (endpoint - 1)
		IapOffset = IapOffset / (endpoint - 1)
		IbpOffset = (IbpOffset / (endpoint - 1)) - 120.0
		IcpOffset = (IcpOffset / (endpoint - 1)) + 120.0
		Write_Status(elementtree, rootdir, "v1", "avg_slope", VaSlope)
		Write_Status(elementtree, rootdir, "v2", "avg_slope", VbSlope)
		Write_Status(elementtree, rootdir, "v3", "avg_slope", VcSlope)
		Write_Status(elementtree, rootdir, "v4", "avg_slope", VxSlope)
		Write_Status(elementtree, rootdir, "c1", "avg_slope", IaSlope)
		Write_Status(elementtree, rootdir, "c2", "avg_slope", IbSlope)
		Write_Status(elementtree, rootdir, "c3", "avg_slope", IcSlope)
		Write_Status(elementtree, rootdir, "c4", "avg_slope", InSlope)
		Write_Global_Status(elementtree, rootdir, "freq_offset", FreqOffset)
		Write_Status(elementtree, rootdir, "v1", "phase_offset", VapOffset)
		Write_Status(elementtree, rootdir, "v2", "phase_offset", VbpOffset)
		Write_Status(elementtree, rootdir, "v3", "phase_offset", VcpOffset)
		Write_Status(elementtree, rootdir, "v4", "phase_offset", VauxpOffset)
		Write_Status(elementtree, rootdir, "c1", "phase_offset", IapOffset)
		Write_Status(elementtree, rootdir, "c2", "phase_offset", IbpOffset)
		Write_Status(elementtree, rootdir, "c3", "phase_offset", IcpOffset)     
		#print (VaSlope, VbSlope, VcSlope, VxSlope, IaSlope, IbSlope, IcSlope, InSlope, FreqOffset, VapOffset, VbpOffset, VcpOffset, IapOffset, IbpOffset, IcpOffset)
		#turn the output to the smallest value
		#Set_Magnitude(0, curr_mag_v1, 0xBF, 0x1C) #set mag for v1
		#Set_Magnitude(0, curr_mag_v2, 0xBF, 0x1D) #set mag for v2
		#Set_Magnitude(0, curr_mag_v3, 0xBF, 0x1E) #set mag for v3
		#Set_Magnitude(0, curr_mag_v4, 0xBF, 0x1F) #set mag for v4
		#Set_Magnitude(0, curr_mag_c1, 0xEF, 0x1C) #set mag for c1
		#Set_Magnitude(0, curr_mag_c2, 0xEF, 0x1D) #set mag for c2
		#Set_Magnitude(0, curr_mag_c3, 0xEF, 0x1E) #set mag for c3
		#Set_Magnitude(0, curr_mag_c4, 0xEF, 0x1F) #set mag for c4
		time.sleep(0.1)
		Output_Channel_Off(0x00, 0x1C)
		Output_Channel_Off(0x00, 0x1D)
		Output_Channel_Off(0x00, 0x1E)
		Output_Channel_Off(0x00, 0x1F)
		#Update the XML values with the current status of all of the outputs
		Write_Status(elementtree, rootdir, "v1", "magnitude", "0")
		Write_Status(elementtree, rootdir, "v2", "magnitude", "0")
		Write_Status(elementtree, rootdir, "v3", "magnitude", "0")
		Write_Status(elementtree, rootdir, "v4", "magnitude", "0")
		Write_Status(elementtree, rootdir, "c1", "magnitude", "0")
		Write_Status(elementtree, rootdir, "c2", "magnitude", "0")
		Write_Status(elementtree, rootdir, "c3", "magnitude", "0")
		Write_Status(elementtree, rootdir, "c4", "magnitude", "0")
		Write_Status(elementtree, rootdir, "v1", "state", "OFF")
		Write_Status(elementtree, rootdir, "v2", "state", "OFF")
		Write_Status(elementtree, rootdir, "v3", "state", "OFF")
		Write_Status(elementtree, rootdir, "v4", "state", "OFF")
		Write_Status(elementtree, rootdir, "c1", "state", "OFF")
		Write_Status(elementtree, rootdir, "c2", "state", "OFF")
		Write_Status(elementtree, rootdir, "c3", "state", "OFF")
		Write_Status(elementtree, rootdir, "c4", "state", "OFF")
		Write_Global_Status(elementtree, rootdir, "frequency", freqavg)
		#Write the current time of the raspberry pi to record when the cal occurred
		caltime = datetime.datetime.now()
		Write_Global_Status(elementtree, rootdir, "cal_date", caltime)
		ourmeter.Close()
		#Done
	
#ADD CAL Harmonics Cal_Source_Harmonics
def Cal_Source_Harmonics(elementtree, rootdir, full_cal_option):
	#if the full_cal_option is True then the cal go up to mag 255 if it is false it will only go up to mag 100
	calpoints = [0,5,10,15,20,25]
	calstrings = ["mag0","mag50","mag100","mag150","mag200","mag255"]
	if (full_cal_option == True):
		endpoint = 6
	else:
		endpoint = 4 
	Reset(rootdir) #Send the Reset() command to make sure that all phases are in default state
	Synchronize(rootdir, 0xF5, 0xF5, 0xF5, 0xF5) #Send the Synchronize command to make sure the phases are on and synced    
	ourmeter = FeedBackMeter("172.20.90.241", 502, "RTU", 1)
	if (ourmeter.MeterConnected == False):
		print ("Could not connect to the meter so the Calibration could not be performed.")
	else:
		VanArray = []
		VbnArray = []
		VcnArray = []
		VxnArray = []
		IaArray = []
		IbArray = []
		IcArray = []
		InArray = []
		FreqArray = []
		VapArray = []
		VbpArray = []
		VcpArray = []
		IapArray = []
		IbpArray = []
		IcpArray = []
		curr_mag_v1h = int(Read_One_Parameter(rootdir, "v1h", "magnitude"))
		curr_mag_v2h = int(Read_One_Parameter(rootdir, "v2h", "magnitude"))
		curr_mag_v3h = int(Read_One_Parameter(rootdir, "v3h", "magnitude"))
		curr_mag_v4h = int(Read_One_Parameter(rootdir, "v4h", "magnitude"))
		curr_mag_c1h = int(Read_One_Parameter(rootdir, "c1h", "magnitude"))
		curr_mag_c2h = int(Read_One_Parameter(rootdir, "c2h", "magnitude"))
		curr_mag_c3h = int(Read_One_Parameter(rootdir, "c3h", "magnitude"))
		curr_mag_c4h = int(Read_One_Parameter(rootdir, "c4h", "magnitude"))
		for x in range(0,endpoint): #Set output to the cal magnitude on all voltage and current channels, then poll readings 10 times and take average. Repeat for magnitudes 50, and 100 (150, 200 and 255 are optional: since this might cause outputs too high for some meters we don't want to always go this high)
			print ("sending mag " + str(calpoints[x]))
			Set_Magnitude(calpoints[x], curr_mag_v1h, 0xFB, 0x1C) #set mag for v1h
			Set_Magnitude(calpoints[x], curr_mag_v2h, 0xFB, 0x1D) #set mag for v2h
			Set_Magnitude(calpoints[x], curr_mag_v3h, 0xFB, 0x1E) #set mag for v3h
			Set_Magnitude(calpoints[x], curr_mag_v4h, 0xFB, 0x1F) #set mag for v4h
			Set_Magnitude(calpoints[x], curr_mag_c1h, 0xFE, 0x1C) #set mag for c1h
			Set_Magnitude(calpoints[x], curr_mag_c2h, 0xFE, 0x1D) #set mag for c2h
			Set_Magnitude(calpoints[x], curr_mag_c3h, 0xFE, 0x1E) #set mag for c3h
			Set_Magnitude(calpoints[x], curr_mag_c4h, 0xFE, 0x1F) #set mag for c4h
			curr_mag_v1h = calpoints[x] #set the current mag variable to current cal point mag
			curr_mag_v2h = calpoints[x]
			curr_mag_v3h = calpoints[x]
			curr_mag_v4h = calpoints[x]
			curr_mag_c1h = calpoints[x]
			curr_mag_c2h = calpoints[x]
			curr_mag_c3h = calpoints[x]
			curr_mag_c4h = calpoints[x]
			time.sleep(5)
			voltA = 0.0
			voltB = 0.0
			voltC = 0.0
			voltX = 0.0
			currA = 0.0
			currB = 0.0
			currC = 0.0
			currN = 0.0
			freqavg = 0.0
			vap = 0.0
			vbp = 0.0
			vcp = 0.0
			iap = 0.0
			ibp = 0.0
			icp = 0.0
			for y in range(0,10):
				ourmeter.GetHighSpeedReadings()
				if ourmeter.PollingSuccess == True:
					voltA += ourmeter.Van
					voltB += ourmeter.Vbn
					voltC += ourmeter.Vcn
					voltX += ourmeter.Vxn
					currA += ourmeter.Ia
					currB += ourmeter.Ib
					currC += ourmeter.Ic
					currN += ourmeter.In
					freqavg += ourmeter.Freq
					vap += ourmeter.VanP
					vbp += ourmeter.VbnP
					vcp += ourmeter.VcnP
					iap += ourmeter.IaP
					ibp += ourmeter.IbP
					icp += ourmeter.IcP
				else:
					print ('Meter could not poll the one second readings correctly. Calibration did not complete. Check serial connection to 1500 and then calibrate again.')
					break
			voltA = voltA / 10.0
			voltB = voltB / 10.0
			voltC = voltC / 10.0
			voltX = voltX / 10.0
			currA = currA / 10.0
			currB = currB / 10.0
			currC = currC / 10.0
			currN = currN / 10.0
			freqavg = freqavg / 10.0
			vap = vap / 10.0
			vbp = vbp / 10.0
			vcp = vcp / 10.0
			iap = iap / 10.0
			ibp = ibp / 10.0
			icp = icp / 10.0
			#Store the this average in the mag# spot in the xml for all channels    
			Write_Status(elementtree, rootdir, "v1h", calstrings[x], voltA)
			Write_Status(elementtree, rootdir, "v2h", calstrings[x], voltB)
			Write_Status(elementtree, rootdir, "v3h", calstrings[x], voltC)
			Write_Status(elementtree, rootdir, "v4h", calstrings[x], voltX)
			Write_Status(elementtree, rootdir, "c1h", calstrings[x], currA)
			Write_Status(elementtree, rootdir, "c2h", calstrings[x], currB)
			Write_Status(elementtree, rootdir, "c3h", calstrings[x], currC)
			Write_Status(elementtree, rootdir, "c4h", calstrings[x], currN)
			VanArray.append(voltA)
			VbnArray.append(voltB)
			VcnArray.append(voltC)
			VxnArray.append(voltX)
			IaArray.append(currA)
			IbArray.append(currB)
			IcArray.append(currC)
			InArray.append(currN)
			FreqArray.append(freqavg)
			VapArray.append(vap)
			VbpArray.append(vbp)
			VcpArray.append(vcp)
			IapArray.append(iap)
			IbpArray.append(ibp)
			IcpArray.append(icp)
		#Calculate slopes from 0 to 50, 50 to 100, 100 to 150, 150 to 200, 200 to 255
		VaSlope = 0.0
		VbSlope = 0.0
		VcSlope = 0.0
		VxSlope = 0.0
		IaSlope = 0.0
		IbSlope = 0.0
		IcSlope = 0.0
		InSlope = 0.0
		FreqOffset = 0.0
		VapOffset = 0.0
		VbpOffset = 0.0
		VcpOffset = 0.0
		IapOffset = 0.0
		IbpOffset = 0.0
		IcpOffset = 0.0
		for x in range(0, (endpoint - 1)):
			VaSlope += (VanArray[x+1]-VanArray[x])/(calpoints[x+1]-calpoints[x])
			VbSlope += (VbnArray[x+1]-VbnArray[x])/(calpoints[x+1]-calpoints[x])
			VcSlope += (VcnArray[x+1]-VcnArray[x])/(calpoints[x+1]-calpoints[x])
			VxSlope += (VxnArray[x+1]-VxnArray[x])/(calpoints[x+1]-calpoints[x])
			IaSlope += (IaArray[x+1]-IaArray[x])/(calpoints[x+1]-calpoints[x])
			IbSlope += (IbArray[x+1]-IbArray[x])/(calpoints[x+1]-calpoints[x])
			IcSlope += (IcArray[x+1]-IcArray[x])/(calpoints[x+1]-calpoints[x])
			InSlope += (InArray[x+1]-InArray[x])/(calpoints[x+1]-calpoints[x])
			FreqOffset += FreqArray[x+1]
			VapOffset += VapArray[x+1]
			VbpOffset += VbpArray[x+1]
			VcpOffset += VcpArray[x+1]
			IapOffset += IapArray[x+1]
			IbpOffset += IbpArray[x+1]
			IcpOffset += IcpArray[x+1]
		##Average all of these slope and offset values and then store the average in the avg_slope spot in the xml for all channels
		VaSlope = VaSlope / (endpoint - 1)
		VbSlope = VbSlope / (endpoint - 1)
		VcSlope = VcSlope / (endpoint - 1)
		VxSlope = VxSlope / (endpoint - 1)
		IaSlope = IaSlope / (endpoint - 1)
		IbSlope = IbSlope / (endpoint - 1)
		IcSlope = IcSlope / (endpoint - 1)
		InSlope = InSlope / (endpoint - 1)
		freqavg = FreqOffset / (endpoint - 1)
		FreqOffset = (freqavg - 60.0) / 60.0 
		VapOffset = VapOffset / (endpoint - 1)
		VbpOffset = (VbpOffset / (endpoint - 1)) - 120.0
		VcpOffset = (VcpOffset / (endpoint - 1)) + 120.0
		IapOffset = IapOffset / (endpoint - 1)
		IbpOffset = (IbpOffset / (endpoint - 1)) - 120.0
		IcpOffset = (IcpOffset / (endpoint - 1)) + 120.0
		Write_Status(elementtree, rootdir, "v1h", "avg_slope", VaSlope)
		Write_Status(elementtree, rootdir, "v2h", "avg_slope", VbSlope)
		Write_Status(elementtree, rootdir, "v3h", "avg_slope", VcSlope)
		Write_Status(elementtree, rootdir, "v4h", "avg_slope", VxSlope)
		Write_Status(elementtree, rootdir, "c1h", "avg_slope", IaSlope)
		Write_Status(elementtree, rootdir, "c2h", "avg_slope", IbSlope)
		Write_Status(elementtree, rootdir, "c3h", "avg_slope", IcSlope)
		Write_Status(elementtree, rootdir, "c4h", "avg_slope", InSlope)
		#Write_Global_Status(elementtree, rootdir, "freq_offset", FreqOffset)
		Write_Status(elementtree, rootdir, "v1h", "phase_offset", VapOffset)
		Write_Status(elementtree, rootdir, "v2h", "phase_offset", VbpOffset)
		Write_Status(elementtree, rootdir, "v3h", "phase_offset", VcpOffset)
		Write_Status(elementtree, rootdir, "c1h", "phase_offset", IapOffset)
		Write_Status(elementtree, rootdir, "c2h", "phase_offset", IbpOffset)
		Write_Status(elementtree, rootdir, "c3h", "phase_offset", IcpOffset)     
		#print (VaSlope, VbSlope, VcSlope, VxSlope, IaSlope, IbSlope, IcSlope, InSlope, FreqOffset, VapOffset, VbpOffset, VcpOffset, IapOffset, IbpOffset, IcpOffset)
		#turn the output to the smallest value
		Set_Magnitude(0, curr_mag_v1h, 0xFB, 0x1C) #set mag for v1h
		Set_Magnitude(0, curr_mag_v2h, 0xFB, 0x1D) #set mag for v2h
		Set_Magnitude(0, curr_mag_v3h, 0xFB, 0x1E) #set mag for v3h
		Set_Magnitude(0, curr_mag_v4h, 0xFB, 0x1F) #set mag for v4h
		Set_Magnitude(0, curr_mag_c1h, 0xFE, 0x1C) #set mag for c1h
		Set_Magnitude(0, curr_mag_c2h, 0xFE, 0x1D) #set mag for c2h
		Set_Magnitude(0, curr_mag_c3h, 0xFE, 0x1E) #set mag for c3h
		Set_Magnitude(0, curr_mag_c4h, 0xFE, 0x1F) #set mag for c4h
		time.sleep(0.1)
		Output_Channel_Off(0x55, 0x1C)
		Output_Channel_Off(0x55, 0x1D)
		Output_Channel_Off(0x55, 0x1E)
		Output_Channel_Off(0x55, 0x1F)
		#Update the XML values with the current status of all of the outputs
		Write_Status(elementtree, rootdir, "v1h", "magnitude", "0")
		Write_Status(elementtree, rootdir, "v2h", "magnitude", "0")
		Write_Status(elementtree, rootdir, "v3h", "magnitude", "0")
		Write_Status(elementtree, rootdir, "v4h", "magnitude", "0")
		Write_Status(elementtree, rootdir, "c1h", "magnitude", "0")
		Write_Status(elementtree, rootdir, "c2h", "magnitude", "0")
		Write_Status(elementtree, rootdir, "c3h", "magnitude", "0")
		Write_Status(elementtree, rootdir, "c4h", "magnitude", "0")
		Write_Status(elementtree, rootdir, "v1h", "state", "OFF")
		Write_Status(elementtree, rootdir, "v2h", "state", "OFF")
		Write_Status(elementtree, rootdir, "v3h", "state", "OFF")
		Write_Status(elementtree, rootdir, "v4h", "state", "OFF")
		Write_Status(elementtree, rootdir, "c1h", "state", "OFF")
		Write_Status(elementtree, rootdir, "c2h", "state", "OFF")
		Write_Status(elementtree, rootdir, "c3h", "state", "OFF")
		Write_Status(elementtree, rootdir, "c4h", "state", "OFF")
		#Write_Global_Status(elementtree, rootdir, "frequency", freqavg)
		#Write the current time of the raspberry pi to record when the cal occurred
		caltime = datetime.datetime.now()
		Write_Global_Status(elementtree, rootdir, "cal_date", caltime)
		ourmeter.Close()
		#Done 

#Cal PF -Clean and Optimize
def Cal_Source_PF():
	ourmeter = FeedBackMeter("172.20.90.241", 502, "RTU", 1)
	if (ourmeter.MeterConnected == False):
		print ("Could not connect to the meter so the Calibration could not be performed.")
	else:
		ourmeter.GetHighSpeedReadings()
		if ourmeter.PollingSuccess == True:

			vbp = ourmeter.VbnP
			vcp = ourmeter.VcnP	
			vauxp = ourmeter.VauxP	

			iap = ourmeter.IaP
			ibp = ourmeter.IbP
			icp = ourmeter.IcP

			#set v120c1<45 in Test Software WAI 10 seconds
			#run cal_PF
			#set v120c1<45 in Test Software

			old_offset = float(Read_One_Parameter(root, "v2", "phase_offset")) 
			offset = float(vbp) - 120
			print("v2")
			print(old_offset)
			print(offset)
			new_offset = old_offset + offset
			print(new_offset)     
			Write_Status(xmltree, root, "v2", "phase_offset", new_offset)

			old_offset = float(Read_One_Parameter(root, "v3", "phase_offset")) 
			offset = float(vcp) - 240
			print("v3")
			print(old_offset)
			print(offset)
			new_offset = old_offset + offset
			print(new_offset)     
			Write_Status(xmltree, root, "v3", "phase_offset", new_offset)

			old_offset = float(Read_One_Parameter(root, "v4", "phase_offset")) 
			offset = float(vauxp) - 45
			print("v4")
			print(old_offset)
			print(offset)
			new_offset = old_offset + offset
			print(new_offset)     
			Write_Status(xmltree, root, "v4", "phase_offset", new_offset)

			old_offset = float(Read_One_Parameter(root, "c1", "phase_offset"))	#Read c1 phase_offset from xml file
			offset = float(iap) - 45											#Subtract 45 deg to get offset
			print("C1")								
			print(old_offset)
			print(offset)
			new_offset = old_offset + offset
			print(new_offset)     
			Write_Status(xmltree, root, "c1", "phase_offset", new_offset)		#Write new offset to xml file

			old_offset = float(Read_One_Parameter(root, "c2", "phase_offset")) 
			offset = float(ibp) - 45 - vbp
			print("C2")
			print(old_offset)			
			print(offset)
			new_offset = old_offset + offset
			print(new_offset)     
			Write_Status(xmltree, root, "c2", "phase_offset", new_offset)

			old_offset = float(Read_One_Parameter(root, "c3", "phase_offset")) 
			offset = float(icp) + 75 - 120 - vcp 
			print("C3")
			print(old_offset)
			print(offset)
			new_offset = old_offset + offset
			print(new_offset)     
			Write_Status(xmltree, root, "c3", "phase_offset", new_offset)

		else:
			print ('Meter could not poll the one second readings correctly. Power Factor Calibration did not complete. Check reference meter and again.')
	
def Cal_Source_PF_Harmonics():
	ourmeter = FeedBackMeter("172.20.90.241", 502, "RTU", 1)
	if (ourmeter.MeterConnected == False):
		print ("Could not connect to the meter so the Calibration could not be performed.")
	else:
		ourmeter.GetHighSpeedReadings()
		if ourmeter.PollingSuccess == True:
		
			vap = ourmeter.VanP
			vbp = ourmeter.VbnP
			vcp = ourmeter.VcnP	
			vauxp = ourmeter.VauxP	

			iap = ourmeter.IaP
			ibp = ourmeter.IbP
			icp = ourmeter.IcP

			#set v120c1<45 in Test Software WAI 10 seconds
			#set v
			#run cal_PF
			#set v120c1<45 in Test Software

			old_offset = float(Read_One_Parameter(root, "v1h", "phase_offset")) 
			offset = float(abp) - vauxp
			print("v1h")
			print(old_offset)
			print(offset)
			new_offset = old_offset + offset
			print(new_offset)     
			Write_Status(xmltree, root, "v1h", "phase_offset", new_offset)
			
			old_offset = float(Read_One_Parameter(root, "v2h", "phase_offset")) 
			offset = float(vbp) - 120 - vauxp
			print("v2h")
			print(old_offset)
			print(offset)
			new_offset = old_offset + offset
			print(new_offset)     
			Write_Status(xmltree, root, "v2h", "phase_offset", new_offset)

			old_offset = float(Read_One_Parameter(root, "v3h", "phase_offset")) 
			offset = float(vcp) - 240 - vauxp
			print("v3h")
			print(old_offset)
			print(offset)
			new_offset = old_offset + offset
			print(new_offset)     
			Write_Status(xmltree, root, "v3h", "phase_offset", new_offset)

			old_offset = float(Read_One_Parameter(root, "v4", "phase_offset")) 
			offset = float(vauxp) - 45
			print("v4h")
			print(old_offset)
			print(offset)
			new_offset = old_offset + offset
			print(new_offset)     
			Write_Status(xmltree, root, "v4", "phase_offset", new_offset)

			old_offset = float(Read_One_Parameter(root, "c1h", "phase_offset"))	#Read c1 phase_offset from xml file
			offset = float(iap) - 45 - vauxp											#Subtract 45 deg to get offset
			print("C1h")								
			print(old_offset)
			print(offset)
			new_offset = old_offset + offset
			print(new_offset)     
			Write_Status(xmltree, root, "c1h", "phase_offset", new_offset)		#Write new offset to xml file

			old_offset = float(Read_One_Parameter(root, "c2h", "phase_offset")) 
			offset = float(ibp) - 45 - vbp - vauxp
			print("C2h")
			print(old_offset)			
			print(offset)
			new_offset = old_offset + offset
			print(new_offset)     
			Write_Status(xmltree, root, "c2h", "phase_offset", new_offset)

			old_offset = float(Read_One_Parameter(root, "c3h", "phase_offset")) 
			offset = float(icp) + 75 - 120 - vcp  - vauxp
			print("C3h")
			print(old_offset)
			print(offset)
			new_offset = old_offset + offset
			print(new_offset)     
			Write_Status(xmltree, root, "c3h", "phase_offset", new_offset)
		
		else:
			print ('Meter could not poll the one second readings correctly. Power Factor Calibration did not complete. Check reference meter and again.')
		
def Cal_Flicker():
	ourmeter = FeedBackMeter("172.20.90.241", 502, "RTU", 1)
	if (ourmeter.MeterConnected == False):
		print ("Could not connect to the meter so the Calibration could not be performed.")
	else:
		ourmeter.GetHighSpeedReadings()
		if ourmeter.PollingSuccess == True:
		
			vap = ourmeter.VanP
			vbp = ourmeter.VbnP
			vcp = ourmeter.VcnP	
			vauxp = ourmeter.VauxP	
			
			#set v1h,v2h,v3h,v4 to unity
			#slope = float(Read_One_Parameter(root, sourceparameterstring, "avg_slope"))
			#magnitude = int(round(float(parameter_string[1:])/slope)) - 1
			#if (magnitude < 0):
			#	magnitude = 0
			#if (magnitude > 255):
			#	magnitude = 255                                                         
			#Set_Magnitude(magnitude, current_mag, mag_channel, output_phase)
			#Write_Status(xmltree, root, sourceparameterstring, "magnitude", magnitude)
			
			#v1h
			old_offset = float(Read_One_Parameter(root, "v1h", "phase_offset")) 
			offset = float(vap) - vauxp
			print("v1h")
			new_offset = old_offset + offset
			print("New Offset: " + new_offset)     
			Write_Status(xmltree, root, "v1h", "phase_offset", new_offset)
			
			#v2h
			old_offset = float(Read_One_Parameter(root, "v2h", "phase_offset")) 
			offset = float(vbp) - vauxp -120
			print("v2h")
			new_offset = old_offset + offset
			print("New Offset: " + new_offset)     
			Write_Status(xmltree, root, "v2h", "phase_offset", new_offset)
				
			#v3h
			old_offset = float(Read_One_Parameter(root, "v3h", "phase_offset")) 
			offset = float(vcp) - vauxp - 240
			print("v3h")
			new_offset = old_offset + offset
			print("New Offset: " + new_offset)     
			Write_Status(xmltree, root, "v3h", "phase_offset", new_offset)
		
		else:
			print ('Meter could not poll the one second readings correctly. Power Factor Calibration did not complete. Check reference meter and again.')
			
class FeedBackMeter():
	
	def __init__(self, IPAddress, ModbusPort, Protocol, DeviceAddress):
		self.IPAddress = IPAddress
		self.ModbusPort = ModbusPort
		self.Protocol = Protocol
		self.DeviceAddress = DeviceAddress
		self.onesecondreadings = []
		self.highspeedreadings = []
		self.onecyclereadings = []
		self.MeterConnected = False
		self.PollingSuccess = False
		# declare the individual parameters to be stored after getting and converting the readings
		self.Van = 0
		self.Vbn = 0
		self.Vcn = 0
		self.Vxn = 0
		self.Ia = 0
		self.Ib = 0
		self.Ic = 0
		self.In = 0
		self.Vab = 0
		self.Vbc = 0
		self.Vca = 0
		self.VAa = 0
		self.VAb = 0
		self.VAc = 0
		self.VAt = 0
		self.VARa = 0
		self.VARb = 0
		self.VARc = 0
		self.VARt = 0
		self.Wa = 0
		self.Wb = 0
		self.Wc = 0
		self.Wt = 0
		self.Freq = 0
		self.PFa = 0
		self.PFb = 0
		self.PFc = 0
		self.PFt = 0
		self.VImb = 0
		self.IImb = 0
		self.VanP = 0
		self.VbnP = 0
		self.VcnP = 0
		self.VauxP = 0
		self.IaP = 0
		self.IbP = 0
		self.IcP = 0
		self.VabP = 0
		self.VbcP = 0
		self.VcaP = 0           
		self.Connect()
		
	def Connect(self):      
#               print "Connecting to meter through " + self.Protocol
		try:
			if (self.Protocol == "TCP"):
				self.client = NetworkClient(self.IPAddress, port=self.ModbusPort)
			elif (self.Protocol == "ASCII"):                
				self.client = SerialClient(method = "ascii", port="/dev/ttyUSB0",stopbits = 1, bytesize = 8, parity = 'N', baudrate= 57600, timeout=0.25)
			elif (self.Protocol == "RTU"):          
				self.client = SerialClient(method = "rtu", port="/dev/ttyUSB0",stopbits = 1, bytesize = 8, parity = 'N', baudrate=115200, timeout=0.25)
			self.client.connect()           
			result  = self.client.read_holding_registers(0x00, 16,  unit=self.DeviceAddress)
			if (len(result.registers) == 16):
				decoder = BinaryPayloadDecoder.fromRegisters(result.registers, byteorder=Endian.Big)
				metername = decoder.decode_string(16)
				if (metername.decode() != "0154 Nexus 1500+" and metername.decode() != "0154 Nexus 1500\0" and metername.decode() != "0171 Nexus 1450\0"):
					print ("Did not connect to the correct meter!")
					self.MeterConnected = False
				else:
					print ("Successfully connected to Feedback Meter.")
					self.MeterConnected = True      
		except:
			print ("Could not connect to the meter. Check the serial connection between the PI and the Reference Meter and then try again.")
			#self.Reconnect()
		
	def GetOneSecondReadings(self):
		self.onesecondreadings = []
		readings_start_address = 0xB3
		readings_num_of_registers = 56
		phase_start_address = 0xA22
		phase_num_of_registers = 9
		try:    
			readingresult  = self.client.read_holding_registers(readings_start_address, readings_num_of_registers,  unit=self.DeviceAddress)
			phaseresult = self.client.read_holding_registers(0xA22, 9,  unit=self.DeviceAddress)                            
			if (len(readingresult.registers) == readings_num_of_registers and len(phaseresult.registers) == phase_num_of_registers):
				#print "we received valid readings"             
				for x in range(0,50,2): 
					decoder = BinaryPayloadDecoder.fromRegisters(readingresult.registers[x:x+2], byteorder=Endian.Big)
					self.onesecondreadings.append(decoder.decode_32bit_int() / 65536.00)
				for x in range(50,54):
					self.onesecondreadings.append(readingresult.registers[x] * 0.001)
				for x in range(54,56):
					decoder = BinaryPayloadDecoder.fromRegisters(readingresult.registers[x:x+1], byteorder=Endian.Big)
					self.onesecondreadings.append(decoder.decode_16bit_int() * 0.01)
				for x in range(0,9):
					decoder = BinaryPayloadDecoder.fromRegisters(phaseresult.registers[x:x+1], byteorder=Endian.Big)
					self.onesecondreadings.append(decoder.decode_16bit_int() * 0.01)        
				#print self.onesecondreadings
				self.PollingSuccess = True
				self.Van = self.onesecondreadings[0]
				self.Vbn = self.onesecondreadings[1]
				self.Vcn = self.onesecondreadings[2]
				self.Vxn = self.onesecondreadings[3]
				self.Ia = self.onesecondreadings[4]
				self.Ib = self.onesecondreadings[5]
				self.Ic = self.onesecondreadings[6]
				self.In = self.onesecondreadings[7]
				self.Vab = self.onesecondreadings[9]
				self.Vbc = self.onesecondreadings[10]
				self.Vca = self.onesecondreadings[11]
				self.VAa = self.onesecondreadings[12]
				self.VAb = self.onesecondreadings[13]
				self.VAc = self.onesecondreadings[14]
				self.VAt = self.onesecondreadings[15]
				self.VARa = self.onesecondreadings[16]
				self.VARb = self.onesecondreadings[17]
				self.VARc = self.onesecondreadings[18]
				self.VARt = self.onesecondreadings[19]
				self.Wa = self.onesecondreadings[20]
				self.Wb = self.onesecondreadings[21]
				self.Wc = self.onesecondreadings[22]
				self.Wt = self.onesecondreadings[23]
				self.Freq = self.onesecondreadings[24]
				self.PFa = self.onesecondreadings[25]
				self.PFb = self.onesecondreadings[26]
				self.PFc = self.onesecondreadings[27]
				self.PFt = self.onesecondreadings[28]
				self.VImb = self.onesecondreadings[29]
				self.IImb = self.onesecondreadings[30]
				self.VanP = self.onesecondreadings[31]
				self.VbnP = self.onesecondreadings[32]
				self.VcnP = self.onesecondreadings[33]
				self.IaP = self.onesecondreadings[34]
				self.IbP = self.onesecondreadings[35]
				self.IcP = self.onesecondreadings[36]
				self.VabP = self.onesecondreadings[37]
				self.VbcP = self.onesecondreadings[38]
				self.VcaP = self.onesecondreadings[39]
				self.Report()
			else:
				self.PollingSuccess = False
				#print ('Meter did not return the expected length for the One Second Readings response.')
				#self.Reconnect()
		except:
			self.PollingSuccess = False
			print ("Exception occurred when trying to retrieve One Second Readings.")
			#self.Reconnect()

	def GetHighSpeedReadings(self):
		self.highspeedreadings = []
		readings_start_address = 0x7A
		readings_num_of_registers = 52
		phase_start_address = 0xA22
		phase_num_of_registers = 9
		phaseaux_start_address = 0xAE
		phaseaux_num_of_registers = 1
		try:            
			readingresult  = self.client.read_holding_registers(readings_start_address, readings_num_of_registers,  unit=self.DeviceAddress)
			phaseresult = self.client.read_holding_registers(0xA22, 9,  unit=self.DeviceAddress)
			phaseauxresult = self.client.read_holding_registers(0xAE, 1,  unit=self.DeviceAddress)             
			if (len(readingresult.registers) == readings_num_of_registers and len(phaseresult.registers) == phase_num_of_registers and len(phaseauxresult.registers) == phaseaux_num_of_registers):
				#print "we received valid readings"             
				for x in range(0,48,2): 
					decoder = BinaryPayloadDecoder.fromRegisters(readingresult.registers[x:x+2], byteorder=Endian.Big)
					self.highspeedreadings.append(decoder.decode_32bit_int() / 65536.00)
				for x in range(48,52):
					self.highspeedreadings.append(readingresult.registers[x] * 0.001)
				for x in range(0,9):
					decoder = BinaryPayloadDecoder.fromRegisters(phaseresult.registers[x:x+1], byteorder=Endian.Big)
					self.highspeedreadings.append(decoder.decode_16bit_int() * 0.01)   
				for x in range(0,1):
					decoder = BinaryPayloadDecoder.fromRegisters(phaseauxresult.registers[x:x+1], byteorder=Endian.Big)
					self.highspeedreadings.append(decoder.decode_16bit_int() * 0.01)                     
				#print self.highspeedreadings
				self.PollingSuccess = True
				self.Van = self.highspeedreadings[0]
				self.Vbn = self.highspeedreadings[1]
				self.Vcn = self.highspeedreadings[2]
				self.Vxn = self.highspeedreadings[3]
				self.Ia = self.highspeedreadings[4]
				self.Ib = self.highspeedreadings[5]
				self.Ic = self.highspeedreadings[6]
				self.In = self.highspeedreadings[7]
				self.Vab = self.highspeedreadings[8]
				self.Vbc = self.highspeedreadings[9]
				self.Vca = self.highspeedreadings[10]
				self.VAa = self.highspeedreadings[11]
				self.VAb = self.highspeedreadings[12]
				self.VAc = self.highspeedreadings[13]
				self.VAt = self.highspeedreadings[14]
				self.VARa = self.highspeedreadings[15]
				self.VARb = self.highspeedreadings[16]
				self.VARc = self.highspeedreadings[17]
				self.VARt = self.highspeedreadings[18]
				self.Wa = self.highspeedreadings[19]
				self.Wb = self.highspeedreadings[20]
				self.Wc = self.highspeedreadings[21]
				self.Wt = self.highspeedreadings[22]
				self.Freq = self.highspeedreadings[23]
				self.PFa = self.highspeedreadings[24]
				self.PFb = self.highspeedreadings[25]
				self.PFc = self.highspeedreadings[26]
				self.PFt = self.highspeedreadings[27]
				self.VanP = self.highspeedreadings[28]
				self.VbnP = self.highspeedreadings[29]
				self.VcnP = self.highspeedreadings[30]
				self.IaP = self.highspeedreadings[31]
				self.IbP = self.highspeedreadings[32]
				self.IcP = self.highspeedreadings[33]
				self.VabP = self.highspeedreadings[34]
				self.VbcP = self.highspeedreadings[35]
				self.VcaP = self.highspeedreadings[36]
				self.VauxP = self.highspeedreadings[37] 
				self.Report()
			else:
				self.PollingSuccess = False
				print ("Meter did not return the expected length for the High Speed Readings response.")
				#self.Reconnect()
		except:
			self.PollingSuccess = False
			print ("Exception occurred when trying to retrieve High Speed Readings.")
			#self.Reconnect()
			
	def GetOneCycleReadings(self):
		self.onecyclereadings = []
		readings_start_address = 0x5D
		readings_num_of_registers = 24
		phase_start_address = 0xA22
		phase_num_of_registers = 9
		try:            
			readingresult  = self.client.read_holding_registers(readings_start_address, readings_num_of_registers,  unit=self.DeviceAddress)
			phaseresult = self.client.read_holding_registers(0xA22, 9,  unit=self.DeviceAddress)            
			if (len(readingresult.registers) == readings_num_of_registers and len(phaseresult.registers) == phase_num_of_registers):
				#print "we received valid readings"             
				for x in range(0,24,2): 
					decoder = BinaryPayloadDecoder.fromRegisters(readingresult.registers[x:x+2], byteorder=Endian.Big)
					self.onecyclereadings.append(decoder.decode_32bit_int() / 65536.00)
				for x in range(0,9):
					decoder = BinaryPayloadDecoder.fromRegisters(phaseresult.registers[x:x+1], byteorder=Endian.Big)
					self.onecyclereadings.append(decoder.decode_16bit_int() * 0.01) 
				#print self.onecyclereadings
				self.PollingSuccess = True
				self.Van = self.onecyclereadings[0]
				self.Vbn = self.onecyclereadings[1]
				self.Vcn = self.onecyclereadings[2]
				self.Vxn = self.onecyclereadings[3]
				self.Ia = self.onecyclereadings[4]
				self.Ib = self.onecyclereadings[5]
				self.Ic = self.onecyclereadings[6]
				self.In = self.onecyclereadings[7]
				self.Vab = self.onecyclereadings[9]
				self.Vbc = self.onecyclereadings[10]
				self.Vca = self.onecyclereadings[11]
				self.VanP = self.onecyclereadings[12]
				self.VbnP = self.onecyclereadings[13]
				self.VcnP = self.onecyclereadings[14]
				self.IaP = self.onecyclereadings[15]
				self.IbP = self.onecyclereadings[16]
				self.IcP = self.onecyclereadings[17]
				self.VabP = self.onecyclereadings[18]
				self.VbcP = self.onecyclereadings[19]
				self.VcaP = self.onecyclereadings[20]
				self.Report()
			else:
				self.PollingSuccess = False
				print ("Meter did not return the expected length for the One Cycle Readings response.")
				#self.Reconnect()               
		except:
			self.PollingSuccess = False
			print ("Exception occurred when trying to retrieve One Cycle Readings.")
			#self.Reconnect()
			
	def Close(self):
#               print "Closing Modbus connection"
		self.client.close()
	
	def Reconnect(self):
		self.Close()
		time.sleep(1)
		self.Connect()
		
	def Report(self):
		print ("Van: " + str(self.Van)) 
		print ("Vbn: " + str(self.Vbn))
		print ("Vcn: " + str(self.Vcn)) 
		print ("Ia: " + str(self.Ia))
		print ("Ib: " + str(self.Ib))
		print ("Ic: " + str(self.Ic))
		print ("VanP: " + str(self.VanP))
		print ("VbnP: " + str(self.VbnP))
		print ("VcnP: " + str(self.VcnP))
		print ("IaP: " + str(self.IaP))
		print ("IbP: " + str(self.IbP))
		print ("IcP: " + str(self.IcP))
		print ("Freq: " + str(self.Freq))               
		print ("Vxn: " + str(self.Vxn))
		print ("In: " + str(self.In))
		print ("Vab: " + str(self.Vab))         
		print ("Vbc: " + str(self.Vbc))
		print ("Vca: " + str(self.Vca))
		print ("VAa: " + str(self.VAa))
		print ("VAb: " + str(self.VAb))
		print ("VAc: " + str(self.VAc))
		print ("VAt: " + str(self.VAt))
		print ("VARa: " + str(self.VARa))
		print ("VARb: " + str(self.VARb))
		print ("VARc: " + str(self.VARc))
		print ("VARt: " + str(self.VARt))
		print ("Wa: " + str(self.Wa))
		print ("Wb: " + str(self.Wb))
		print ("Wc: " + str(self.Wc))
		print ("Wt: " + str(self.Wt))           
		print ("PFa: " + str(self.PFa))
		print ("PFb: " + str(self.PFb))
		print ("PFc: " + str(self.PFc))
		print ("PFt: " + str(self.PFt))
		print ("VImb: " + str(self.VImb))
		print ("IImb: " + str(self.IImb))               
		print ("VabP: " + str(self.VabP))
		print ("VbcP: " + str(self.VbcP))
		print ("VcaP: " + str(self.VcaP))
		print ("VauxP: " + str(self.VauxP))
	
# main code to parse the input argument and perform the desired actions from those arguments
if (input_parameter.endswith(';')):
	commands_array = input_parameter.split(';') #split input argument around the ";"
	command_string = "" 
	parameter_string = ""
	for command_string in commands_array: #loop through each command in the command strings array
		#input registers
		freq_channel = 0xFF
		mag_channel = 0xFF
		frequency = -1
		phase_angle = -1
		output_waveform = ''
		magnitude = -1
		output_phase = 0xFF
		sourcelistindex = 0
		sourceparameterstring = ''
				
		if (command_string == ""): #when we reach an empty string this is the end of the command array and we can exit the for loop
			break #exit the for loop 
		else:
			xmltree = ET.parse('/home/pi/TestDeptSourceParameters.xml', ET.XMLParser(encoding='utf-8'))
			root = xmltree.getroot()                
			
			parameters_array = command_string.split(',') #separate the command string into an array of individual parameters 
			for parameter_string in parameters_array: #loop through each parameter in the parameter array                                                   
				if (parameter_string.startswith('v')):   #check if first character is a 'v' for voltage phase
					sourceparameterstring = parameter_string
					if (parameter_string == "v1"):
						freq_channel = 0x7F #this is the byte to be written to the PCA9557 gpio expander to set the chip select for the fundamental voltage A AD9833 (freq, phase, waveform) to low
						mag_channel = 0xBF  #this is the byte to be written to the PCA9557 gpio expander to set the chip select for the fundamental voltage A AD5160 (magnitude) to low
						output_phase = 0x1C #this is the i2c address for the PCA9557 gpio expander assigned to the phase A voltage and current
					elif (parameter_string == "v1h"):
						freq_channel = 0xF7 #this is the byte to be written to the PCA9557 gpio expander to set the chip select for the harmonic voltage A AD9833 (freq, phase, waveform) to low
						mag_channel = 0xFB  #this is the byte to be written to the PCA9557 gpio expander to set the chip select for the harmonic voltage A AD5160 (magnitude) to low
						output_phase = 0x1C #this is the i2c address for the PCA9557 gpio expander assigned to the phase A voltage and current
					elif (parameter_string == "v2"):
						freq_channel = 0x7F #this is the byte to be written to the PCA9557 gpio expander to set the chip select for the fundamental voltage B AD9833 (freq, phase, waveform) to low
						mag_channel = 0xBF  #this is the byte to be written to the PCA9557 gpio expander to set the chip select for the fundamental voltage B AD5160 (magnitude) to low
						output_phase = 0x1D #this is the i2c address for the PCA9557 gpio expander assigned to the phase B voltage and current
					elif (parameter_string == "v2h"):
						freq_channel = 0xF7 #this is the byte to be written to the PCA9557 gpio expander to set the chip select for the harmonic voltage A AD9833 (freq, phase, waveform) to low
						mag_channel = 0xFB  #this is the byte to be written to the PCA9557 gpio expander to set the chip select for the harmonic voltage A AD5160 (magnitude) to low
						output_phase = 0x1D #this is the i2c address for the PCA9557 gpio expander assigned to the phase A voltage and current
					elif (parameter_string == "v3"):
						freq_channel = 0x7F #this is the byte to be written to the PCA9557 gpio expander to set the chip select for the fundamental voltage A AD9833 (freq, phase, waveform) to low
						mag_channel = 0xBF  #this is the byte to be written to the PCA9557 gpio expander to set the chip select for the fundamental voltage A AD5160 (magnitude) to low
						output_phase = 0x1E #this is the i2c address for the PCA9557 gpio expander assigned to the phase A voltage and current
					elif (parameter_string == "v3h"):
						freq_channel = 0xF7 #this is the byte to be written to the PCA9557 gpio expander to set the chip select for the harmonic voltage A AD9833 (freq, phase, waveform) to low
						mag_channel = 0xFB  #this is the byte to be written to the PCA9557 gpio expander to set the chip select for the harmonic voltage A AD5160 (magnitude) to low
						output_phase = 0x1E #this is the i2c address for the PCA9557 gpio expander assigned to the phase A voltage and current
					elif (parameter_string == "v4"):
						freq_channel = 0x7F #this is the byte to be written to the PCA9557 gpio expander to set the chip select for the fundamental voltage A AD9833 (freq, phase, waveform) to low
						mag_channel = 0xBF  #this is the byte to be written to the PCA9557 gpio expander to set the chip select for the fundamental voltage A AD5160 (magnitude) to low
						output_phase = 0x1F #this is the i2c address for the PCA9557 gpio expander assigned to the phase A voltage and current
					elif (parameter_string == "v4h"):
						freq_channel = 0xF7 #this is the byte to be written to the PCA9557 gpio expander to set the chip select for the harmonic voltage A AD9833 (freq, phase, waveform) to low
						mag_channel = 0xFB  #this is the byte to be written to the PCA9557 gpio expander to set the chip select for the harmonic voltage A AD5160 (magnitude) to low
						output_phase = 0x1F #this is the i2c address for the PCA9557 gpio expander assigned to the phase A voltage and current
					#elif parameter_string == "v0":                                 
					#elif parameter_string == "v0h":
					else:
						print ("invalid parameter given %s" % (parameter_string))
							
				elif (parameter_string.startswith('c')): #check if first character is a 'c' for current phase
					sourceparameterstring = parameter_string
					if (parameter_string == "c1"):
						freq_channel = 0xDF #this is the byte to be written to the PCA9557 gpio expander to set the chip select for the fundamental current A AD9833 (freq, phase, waveform) to low
						mag_channel = 0xEF  #this is the byte to be written to the PCA9557 gpio expander to set the chip select for the fundamental current A AD5160 (magnitude) to low
						output_phase = 0x1C #this is the i2c address for the PCA9557 gpio expander assigned to the phase A voltage and current
					elif (parameter_string == "c1h"):
						freq_channel = 0xFD #this is the byte to be written to the PCA9557 gpio expander to set the chip select for the harmonic current A AD9833 (freq, phase, waveform) to low
						mag_channel = 0xFE      #this is the byte to be written to the PCA9557 gpio expander to set the chip select for the harmonic current A AD5160 (magnitude) to low
						output_phase = 0x1C     #this is the i2c address for the PCA9557 gpio expander assigned to the phase A voltage and current              
					elif (parameter_string == "c2"):
						freq_channel = 0xDF #this is the byte to be written to the PCA9557 gpio expander to set the chip select for the fundamental current A AD9833 (freq, phase, waveform) to low
						mag_channel = 0xEF  #this is the byte to be written to the PCA9557 gpio expander to set the chip select for the fundamental current A AD5160 (magnitude) to low
						output_phase = 0x1D #this is the i2c address for the PCA9557 gpio expander assigned to the phase A voltage and current
					elif (parameter_string == "c2h"):
						freq_channel = 0xFD #this is the byte to be written to the PCA9557 gpio expander to set the chip select for the harmonic current A AD9833 (freq, phase, waveform) to low
						mag_channel = 0xFE      #this is the byte to be written to the PCA9557 gpio expander to set the chip select for the harmonic current A AD5160 (magnitude) to low
						output_phase = 0x1D     #this is the i2c address for the PCA9557 gpio expander assigned to the phase A voltage and current      
					elif (parameter_string == "c3"):
						freq_channel = 0xDF #this is the byte to be written to the PCA9557 gpio expander to set the chip select for the fundamental current A AD9833 (freq, phase, waveform) to low
						mag_channel = 0xEF  #this is the byte to be written to the PCA9557 gpio expander to set the chip select for the fundamental current A AD5160 (magnitude) to low
						output_phase = 0x1E #this is the i2c address for the PCA9557 gpio expander assigned to the phase A voltage and current
					elif (parameter_string == "c3h"):
						freq_channel = 0xFD #this is the byte to be written to the PCA9557 gpio expander to set the chip select for the harmonic current A AD9833 (freq, phase, waveform) to low
						mag_channel = 0xFE      #this is the byte to be written to the PCA9557 gpio expander to set the chip select for the harmonic current A AD5160 (magnitude) to low
						output_phase = 0x1E     #this is the i2c address for the PCA9557 gpio expander assigned to the phase A voltage and current      
					elif (parameter_string == "c4"):
						freq_channel = 0xDF #this is the byte to be written to the PCA9557 gpio expander to set the chip select for the fundamental current A AD9833 (freq, phase, waveform) to low
						mag_channel = 0xEF  #this is the byte to be written to the PCA9557 gpio expander to set the chip select for the fundamental current A AD5160 (magnitude) to low
						output_phase = 0x1F #this is the i2c address for the PCA9557 gpio expander assigned to the phase A voltage and current
					elif (parameter_string == "c4h"):
						freq_channel = 0xFD #this is the byte to be written to the PCA9557 gpio expander to set the chip select for the harmonic current A AD9833 (freq, phase, waveform) to low
						mag_channel = 0xFE      #this is the byte to be written to the PCA9557 gpio expander to set the chip select for the harmonic current A AD5160 (magnitude) to low
						output_phase = 0x1F     #this is the i2c address for the PCA9557 gpio expander assigned to the phase A voltage and current                      
					#elif parameter_string == "c0":
					#elif parameter_string == "c0h":                                                        
					else:
						print ("invalid parameter given %s" % (parameter_string))
						
				elif (parameter_string.startswith('f')): #check if first character is a 'f' for frequency
					try:                                            
						freqoffset = float(Read_Global_Parameter(root, "freq_offset")) #get the frequency offset value from the TestDeptSourceParameters.xml file and covert it to a float
						setfreq = float(parameter_string[1:]) * (1 - freqoffset) + 0.008 #remove the first character of the string to get rid of the 'f' and convert it to a float for the Set_Freq function convert value to a float then adjust with the freq offset and fudge factor (0.008)
						Set_Freq(setfreq)
						Write_Global_Status(xmltree, root, "freqU", float(parameter_string[1:])) 
					except ValueError:
							print ("invalid parameter given %s" % (parameter_string))
				elif (parameter_string.startswith('x')): #check if first character is a 'f' for frequency
					try:                                            
						freqoffset = float(Read_Global_Parameter(root, "freq_offset")) #get the frequency offset value from the TestDeptSourceParameters.xml file and covert it to a float
						setfreq = float(parameter_string[1:]) * (1 - freqoffset) + 0.008 #remove the first character of the string to get rid of the 'f' and convert it to a float for the Set_Freq function convert value to a float then adjust with the freq offset and fudge factor (0.008)
						Set_Freq_VAux(setfreq) 
					except ValueError:
							print ("invalid parameter given %s" % (parameter_string))            
					
				elif (parameter_string.startswith('h')): #check if first character is a 'f' for frequency
					try:                                            
						freqoffset = float(Read_Global_Parameter(root, "freq_offset")) #get the frequency offset value from the TestDeptSourceParameters.xml file and covert it to a float
						setfreq = float(parameter_string[1:]) * (1 - freqoffset) + 0.008 #remove the first character of the string to get rid of the 'f' and convert it to a float for the Set_Freq function convert value to a float then adjust with the freq offset and fudge factor (0.008)
						Set_Freq_Harmonics(setfreq, freq_channel, output_phase) 
					except ValueError:
							print ("invalid parameter given %s" % (parameter_string))				

				elif (parameter_string.startswith('p')): #check if first character is a 'p' for phase angle
					if (freq_channel != 0xFF):
						try:
							phase_check_string = parameter_string[1:]
							current_phase = float(Read_One_Parameter(root, sourceparameterstring, "phase"))
							if (phase_check_string == "INC"):                                               
									phase_angle = current_phase + 1.0 #increment the phase angle by 1 degree
							elif (phase_check_string == "DEC"):
									phase_angle = current_phase - 1.0 #decrement the phase angle by 1 degree
							else:
								phaseoffset = float(Read_One_Parameter(root, sourceparameterstring, "phase_offset"))
								#remove the first character of the string to get rid of the 'p' and convert value to a float and subtract phase offset
								phase_angle = float(phase_check_string) - phaseoffset
							if (phase_angle >= 360.0): #check if the incremented phase angle is greater than 360, if so subtract 360
								phase_angle = phase_angle - 360.0
							elif (phase_angle < 0.0): #check if the decremented phase angle is less than 0, if so add 360
								phase_angle = phase_angle + 360.0       
							Set_phase_angle(phase_angle, freq_channel, output_phase)
							#Additional for feedback
							if phase_check_string != "INC" and phase_check_string != "DEC":
								print("Write done")
								Write_Status(xmltree, root, sourceparameterstring, "phaseU", float(parameter_string[1:]))
							Write_Status(xmltree, root, sourceparameterstring, "phase", phase_angle)
						except ValueError:
							print ("invalid parameter given %s" % (parameter_string))
							
				elif (parameter_string.startswith('a')): #check if first character is a 'a' for amplitude
					if (mag_channel != 0xFF):
						try:
							mag_check_string = parameter_string[1:]
							current_mag = int(Read_One_Parameter(root, sourceparameterstring, "magnitude"))
							if (mag_check_string == "INC"): #increment the current magnitude
								if (current_mag < 255): #check if the current value is at its max               
									magnitude = current_mag + 1 
							elif (mag_check_string == "DEC"): # decrement the current magnitude
								if (current_mag > 0): #check if the current value is at its min
									magnitude = current_mag - 1
							else:                                                                   
								slope = float(Read_One_Parameter(root, sourceparameterstring, "avg_slope"))                                                                     
								#remove the first character of the string to get rid of the 'a' and convert value to an float. Needed to add the -1 so that the code will adjust to the output of the digital pot starts at 0.
								magnitude = int(round(float(parameter_string[1:])/slope)) - 1
								#if the magnitude calculates to be lower than the 0 set the magnitude = 0 and if it is higher than 255 set the magnitude = 255
								if (magnitude < 0):
									magnitude = 0
								if (magnitude > 255):
									magnitude = 255                                                         
							Set_Magnitude(magnitude, current_mag, mag_channel, output_phase)
							Write_Status(xmltree, root, sourceparameterstring, "magU", float(parameter_string[1:]) )
							Write_Status(xmltree, root, sourceparameterstring, "magnitude", magnitude)
						except ValueError:
							print ("invalid parameter given %s" % (parameter_string))
														
				elif (parameter_string.startswith('w')): #check if first character is a 'w' for waveform shape
					if (freq_channel != 0xFF):
						output_waveform = parameter_string[1:]
						if(output_waveform == "sine" or output_waveform == "tri" or output_waveform == "squ"):
							Set_Output_Waveform(output_waveform, freq_channel, output_phase)
							Write_Status(xmltree, root, sourceparameterstring, "wave_shape", output_waveform)
						else:
							print ("invalid parameter given %s" % (parameter_string))
							
				elif (parameter_string.startswith('W')): #check if first characters are 'WAIC' for the wait cycles command
					wait_string1 = parameter_string[0:4]                                                    
					wait_string2 = parameter_string[0:3]
					if (wait_string1 == "WAIC"):                                    
						wait_freq = float(Read_Global_Parameter(root, "frequency"))
						wait_time = float(parameter_string[4:]) * (1/wait_freq)
						time.sleep(wait_time)                   
					elif (wait_string2 == "WAI"):
						wait_time = float(parameter_string[3:]) * 0.001
						time.sleep(wait_time)   
					else:
						print ("invalid parameter given %s" % (parameter_string))

				elif (parameter_string.startswith('o')): #check if first character is a 'o' for output state on/off
					if (freq_channel != 0xFF):
						if (parameter_string == "on"):
							Output_Channel_On(freq_channel, output_phase)
							Write_Status(xmltree, root, sourceparameterstring, "state", "ON")
						elif (parameter_string == "off"):       
							Output_Channel_Off(freq_channel, output_phase)
							Write_Status(xmltree, root, sourceparameterstring, "state", "OFF")
						else:
							print ("invalid parameter given %s" % (parameter_string))
							
				elif (parameter_string == "Reset"):      #check if the Reset command is selected
					Reset(root)
				
				elif (parameter_string == "Cal-PF"):      #check if the Reset command is selected
					#Test software inject 45 deg WYE
					Cal_Source_PF()
					#Test Software inject 45 deg WYE
					
				elif (parameter_string == "Cal-Flicker"):      #check if the Reset command is selected
					Cal_Flicker()

				elif (parameter_string == "Cal-PF-Harmonics"):      #check if the Reset command is selected
					#Test software inject 45 deg WYE
					Cal_Source_PF_Harmonics()
					#Test Software inject 45 deg WYE
						
				elif (parameter_string == "Sync"):       #check if the Sync command is selected
					Synchronize(root, 0x5F, 0x5F, 0x5F, 0x5F)
				
				elif (parameter_string == "Status"):     #check if the Status command is selected
					ourmeter = FeedBackMeter("172.20.90.241", 502, "RTU", 1)       
					ourmeter.GetHighSpeedReadings()
					ourmeter.Close()
					
				elif (parameter_string == "Last-Sent"):  #check if the Last-Sent command is selected
					Read_Last_Sent(root)
					
				elif (parameter_string == "Cal"):                #check if the Cal command is selected
					Cal_Source(xmltree, root, False)			
					
				elif (parameter_string == "Cal-Full"):   #check if the Cal-Full command is selected
					Cal_Source(xmltree, root, True) 
					
				elif (parameter_string == "Cal-Harmonics"):                #check if the Cal command is selected
					Cal_Source_Harmonics(xmltree, root, True)			
				
				elif (parameter_string == "Time"):               #check if the Time command is selected
					print (datetime.datetime.now())
				
				elif (parameter_string == "Cal-Time"):   #check if the Cal-Time command is selected
					print (Read_Global_Parameter(root, "cal_date"))
					
				elif (parameter_string == "Zero-Out"):   #check if the Zero-Out command is selected     
					SetAllZeroes()
										
				elif (parameter_string == "Power-On"):   #check if the Power-On command is selected    
					GPIO.output(24, GPIO.LOW)	     #this will change the KYZ output of Relay3 to turn on the 12V wired to the SSR which will turn on the power to the top outlet on the case
					print ("Auxiliary Power turned ON.")
								
				elif (parameter_string == "Power-Off"):   #check if the Power-Off command is selected    
					GPIO.output(24, GPIO.HIGH)	     #this will change the KYZ output of Relay3 to turn off the 12V wired to the SSR which will turn off the power to the top outlet on the case
					print ("Auxiliary Power turned OFF.")

				elif (parameter_string == "XX-On"):	#Add SSR Module in the Hardware side
					GPIO.output(25, GPIO.HIGH)

				elif (parameter_string == "XX-Off"): #Add SSR Module in the Hardware side
					GPIO.output(25,GPIO.LOW)

				else:                                                                   #invalid command
					print ("invalid parameter given %s" % (parameter_string))
				time.sleep(0.001)
			##end of second for loop                                                                
	#end of first for loop
else:
	print ("Input argument is invalid. All commands must end with a ';'")
