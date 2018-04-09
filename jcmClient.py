# Use Python 3 for this, NOT Python 2.

import socket
from threading import Thread, Lock

#for unbuffered stdin raw mode
import tty
import sys
import termios
import select

import os
import signal

HOST = '169.254.131.150'
PORT = 3490
MAXPACKETSIZE = 1024
PROMPT = '<jcm> '
GENERICSUCCESSRESPONSE = '.'
ENCODING = 'utf-8'

PACKET_TYPE_TEXT = 1
PACKET_TYPE_BINARY = 2


# this is the socket object
s = None
readyToSend = True

print_script_commands = False
print_to_log = False
print_to_screen = True

is_header_packet = True
next_response_is_text = False

log_filename = 'jcm.log'

packets_left_in_response = 0

class ExitCommand(Exception):
	pass

def signal_handler(signal, frame):
	raise ExitCommand()


def doClientCommand(command):
	global print_script_commands, print_to_log, log_filename
	command_args = command.lower().split(' ')

	if command_args[0] == ".script" or command_args[0] == ".s":
		if len(command_args) != 2:
			print("Error in script arguments")
			return command
		filename = command_args[1]
		runScript(filename)
		return command
	elif command_args[0] == ".options" or command_args[0] == ".o":
		if len(command_args) < 3:
			print("Error in script arguments")
			return command
		if command_args[1] == "printscript":
			if command_args[2] == "on":
				print_script_commands = True
				print('Script command printing ON')
			elif command_args[2] == "off":
				print_script_commands = False
				print('Script command printing OFF')
		elif command_args[1] == "log":
			if command_args[2] == "on":
				print_to_log = True
				print('Printing to log file ON')
			elif command_args[2] == "off":
				print_to_log = False
				print('Printing to log file OFF')
		elif command_args[1] == "logfilename":
			log_filename = command_args[2]
			print('Now printing to', log_filename)
			print_to_log = True
			print('Printing to log file ON')
		else:
			print('Error in options arguments')
		return command

	print("Unknown client command")
	return command


def sendCommand(command = None):
	global readyToSend
	while not readyToSend:
		pass

	#if no command is given, the user must input it
	if command is None:
		command = input(PROMPT)
	if command is "":
		return command

	#commands starting with '.' are for the client, and are not sent to the server
	if command.startswith('.'):
		doClientCommand(command)
		return command

	s.sendall(command.encode('utf-8'))
	readyToSend = False
	return command


def runScript(filename):
	global print_script_commands
	commands = None
	try:
		with open(filename, "r") as f:
			commands = f.readlines()
			commands = [x.strip() for x in commands]
	except FileNotFoundError:
		print('File not found')
		return

		# #save normal stdin state
		# original_stdin_settings = termios.tcgetattr(sys.stdin)
		# #change stdin to be unbuffered (to detect keyboard presses)
		# tty.setraw(sys.stdin)

	for command in commands:
		# ready = select.select([sys.stdin], [], [], 0)[0]
		# if not ready:
			#skip comments and empty lines
		if command is None or command == "" or command.startswith('#') or command.startswith("//"):
			continue
		if print_script_commands:
			print("Sending '" + command + "'")
		sendCommand(command) # sends commands one at a time, as if the user entered them
			#
			# x=sys.stdin.read(1)[0]
			# if x == chr(27):
			# 	# 	raise KeyboardInterrupt
			# else:
			# 	raise KeyboardInterrupt
	# except KeyboardInterrupt:
	# 	print("Script halted.")
	# finally:
	# 	termios.tcsetattr(sys.stdin, termios.TCSADRAIN, original_stdin_settings)


def receiver(lock):
	global readyToSend, is_header_packet, next_response_is_text, packets_left_in_response
	while 1:
		response = s.recv(MAXPACKETSIZE)

		#if server has disconnected, the response is 0
		if len(response) == 0:
			print("\nConnection with server has been lost")
			os.kill(os.getpid(), signal.SIGUSR1)
			break

		if is_header_packet:
			if response[0] == PACKET_TYPE_TEXT:
				next_response_is_text = True
			elif response[0] == PACKET_TYPE_BINARY:
				next_response_is_text = False
			else:
				print("Error: Invalid header:", response[0], ", length: ", len(response))
			packets_left_in_response = response[1]

			#print("Packets to send:", packets_left_in_response)
			is_header_packet = False
			continue


		if next_response_is_text:
			print(response.decode(ENCODING))
		else:
			print(format(int.from_bytes(response, byteorder='big', signed=False), '08x'))


		if packets_left_in_response > 0:
			packets_left_in_response -= 1
		if packets_left_in_response == 0:
			is_header_packet = True
			readyToSend = True
		#else:
		#	print("Packets left:", packets_left_in_response)


		#stop here for now
		continue

		# don't output generic success responses
		if response.decode(ENCODING) == GENERICSUCCESSRESPONSE:
			readyToSend = True
			continue

		if print_to_screen:
			print(response.decode(ENCODING))
		if print_to_log:
			try:
				with open(log_filename, 'a') as log:
					log.write(response.decode(ENCODING) + '\n')
			# if file was not created yet, then create it
			except IOError:
				with open(log_filename, 'w') as log:
					log.write(response.decode(ENCODING) + '\n')
		readyToSend = True
		is_header_packet = True


def sender(lock):
	command = ""
	while command != "exit":
		command = sendCommand()
	# gets here if user types "exit"
	os.kill(os.getpid(), signal.SIGUSR1)


def connectToServer():
	global s, readyToSend

	for res in socket.getaddrinfo(HOST, PORT, socket.AF_UNSPEC, socket.SOCK_STREAM):
		af, socktype, proto, canonname, sa = res
		try:
			s = socket.socket(af, socktype, proto)
		except socket.error as msg:
			s = None
			continue
		try:
			s.connect(sa)
		except socket.error as msg:
			s.close()
			s = None
			continue
		break
	if s is None:
		print('Failed to connect to server. Check if 1) the server is running and 2) you are connected to the '
			  'right IP address and port')
		sys.exit(1)


def start():
	global s, readyToSend

	signal.signal(signal.SIGUSR1, signal_handler)

	try:
		connectToServer()

		print('Connected to the JCM server at ' + HOST + '.')

		lock = Lock()
		threads = []

		senderThr = Thread(target=sender, args=(lock,))
		senderThr.daemon = True
		senderThr.start()
		receiverTh = Thread(target=receiver, args=(lock,))
		receiverTh.daemon = True
		receiverTh.start()

		threads.append(senderThr)
		threads.append(receiverTh)


		# wait here until all threads are finished
		for t in threads:
			t.join()

	except (KeyboardInterrupt, ExitCommand) as e:
		s.close()
		print('Exiting...')
		sys.exit(0)

	s.close()
	print('Exiting...')


if __name__ == "__main__":
	start()