import socket
from threading import Thread, Lock
import sys
import os
import signal

import struct

class Connector:

    MAXPACKETSIZE = 1024
    GENERICSUCCESSRESPONSE = '.'
    ENCODING = 'utf-8'
    PACKET_TYPE_TEXT = 1
    PACKET_TYPE_BINARY = 2

    def __init__(self):
        # The socket connection
        self.s = None
        self.readyToSend = True

        self.print_script_commands = False
        self.print_to_log = False
        self.print_to_screen = True

        self.is_header_packet = True
        self.next_response_is_text = False

        self.log_filename = 'jcm.log'

        self.data_recv_buffer = []

        self.packets_left_in_response = 0

    class ExitCommand(Exception):
        pass

    def _signal_handler(self, signal, frame):
        raise self.ExitCommand()

    def _do_client_command(self, command):
        command_args = command.lower().split(' ')

        # if command_args[0] == ".script" or command_args[0] == ".s":
        #     if len(command_args) != 2:
        #         print("Error in script arguments")
        #         return command
        #     filename = command_args[1]
        #     runScript(filename)
        #     return command
        if command_args[0] == ".options" or command_args[0] == ".o":
            if len(command_args) < 3:
                print("Error in script arguments")
                return command
            if command_args[1] == "printscript":
                if command_args[2] == "on":
                    self.print_script_commands = True
                    print('Script command printing ON')
                elif command_args[2] == "off":
                    self.print_script_commands = False
                    print('Script command printing OFF')
            elif command_args[1] == "log":
                if command_args[2] == "on":
                    self.print_to_log = True
                    print('Printing to log file ON')
                elif command_args[2] == "off":
                    self.print_to_log = False
                    print('Printing to log file OFF')
            elif command_args[1] == "logfilename":
                self.log_filename = command_args[2]
                print('Now printing to', log_filename)
                self.print_to_log = True
                print('Printing to log file ON')
            else:
                print('Error in options arguments')
            return command

        print("Unknown client command")
        return command

    def _send_command(self, command=""):
        while not self.readyToSend:
            pass

        if command is "":
            return command

        # commands starting with '.' are for the client, and are not sent to the server
        if command.startswith('.'):
            self._do_client_command(command)
            return command

        self.s.sendall(command.encode('utf-8'))
        self.readyToSend = False
        return command

    def _receiver(self):
        while 1:
            response = self.s.recv(self.MAXPACKETSIZE)

            # if server has disconnected, the response is 0
            if len(response) == 0:
                print("\nConnection with server has been lost")
                os.kill(os.getpid(), signal.SIGUSR1)
                break

            if self.is_header_packet:
                #print("header[0]:", response[0], "1:", response[1])
                if response[0] == self.PACKET_TYPE_TEXT:
                    self.next_response_is_text = True
                elif response[0] == self.PACKET_TYPE_BINARY:
                    self.next_response_is_text = False
                else:
                    print("Error: Invalid header:", response[0], ", length: ", len(response))
                self.packets_left_in_response = response[1]
                #print("Packets to send:", self.packets_left_in_response)
                self.is_header_packet = False
                continue

            if self.packets_left_in_response > 0:
                self.packets_left_in_response -= 1
            if self.packets_left_in_response == 0:
                self.is_header_packet = True
                self.readyToSend = True
            #else:
            #    print("Packets left:", self.packets_left_in_response)

            self.data_recv_buffer = response


            #stop here for now
            continue

            # don't output generic success responses
            if response.decode(self.ENCODING) == self.GENERICSUCCESSRESPONSE:
                self.readyToSend = True
                continue

            if print_to_screen:
                print(response.decode(self.ENCODING))
            if print_to_log:
                try:
                    with open(self.log_filename, 'a') as log:
                        log.write(response.decode(self.ENCODING) + '\n')
                # if file was not created yet, then create it
                except IOError:
                    with open(self.log_filename, 'w') as log:
                        log.write(response.decode(self.ENCODING) + '\n')
            self.readyToSend = True
            self.is_header_packet = True

    def _sender(self):
        command = ""
        while command != "exit":
            command = self._send_command()
        # gets here if user types "exit"
        os.kill(os.getpid(), signal.SIGUSR1)

    def _connect_to_server(self, ip_address, port):

        for res in socket.getaddrinfo(ip_address, port, socket.AF_UNSPEC, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            try:
                self.s = socket.socket(af, socktype, proto)
            except socket.error as msg:
                self.s = None
                continue
            try:
                self.s.connect(sa)
            except socket.error as msg:
                self.s.close()
                self.s = None
                continue
            break
        if self.s is None:
            print('Failed to connect to jcm server. Check if the server is running and you are connected to the '
                  'right IP address and port')
            sys.exit(1)

    def _fetch_response(self):
        # must stall until server has responded
        while len(self.data_recv_buffer) == 0:
            pass
        data = self.data_recv_buffer
        self.data_recv_buffer = []
        return data

    def _fetch_int(self):
        return int.from_bytes(self._fetch_response(), byteorder='big', signed=False)

    def _fetch_float(self):
        return struct.unpack('f', self._fetch_response())[0]

    def _fetch_string(self):
        return self._fetch_response().decode(self.ENCODING)



    ### USER COMMANDS ###

    # Connects to the jcm server at the specified address and port
    def connect(self, ip_address, port):

        signal.signal(signal.SIGUSR1, self._signal_handler)

        try:
            self._connect_to_server(ip_address, port)

            #print('Connected to the JCM server at ' + ip_address + '.')

            self.lock = Lock()
            self.threads = []

            self.senderThr = Thread(target=self._sender, args=())
            self.senderThr.daemon = True
            self.senderThr.start()
            self.receiverTh = Thread(target=self._receiver, args=())
            self.receiverTh.daemon = True
            self.receiverTh.start()

            self.threads.append(self.senderThr)
            self.threads.append(self.receiverTh)


        except (KeyboardInterrupt, self.ExitCommand) as e:
            self.s.close()
            sys.exit(0)
        #self.s.close()

    def read_idcode(self):
        self._send_command('read idcode')
        return self._fetch_int()

    def read_status(self):
        self._send_command('read status')
        return self._fetch_int()

    def read_far(self):
        self._send_command('read far')
        return self._fetch_int()

    def read_ctrl0(self):
        self._send_command('read ctrl0')
        return self._fetch_int()

    def read_ctrl0(self):
        self._send_command('read ctrl0')
        return self._fetch_int()

    def read_crc(self):
        self._send_command('read crc')
        return self._fetch_int()

    def read_cor1(self):
        self._send_command('read cor1')
        return self._fetch_int()

    def read_cmd(self):
        self._send_command('read cmd')
        return self._fetch_int()

    def read_cur_temp(self):
        self._send_command('read xadc curtemp')
        return self._fetch_float()

    def read_vccint(self):
        self._send_command('read xadc vccint')
        return self._fetch_float()

    def read_vccaux(self):
        self._send_command('read xadc vccaux')
        return self._fetch_float()

    def read_voltage(self):
        self._send_command('read xadc voltage')
        return self._fetch_float()


    #Returns an array with all the data read
    def read_frame(self, address, num_frames=1):
        self._send_command('read frame ' + str(address) + ' ' + str(num_frames))

        response = self._fetch_response()

        while (self.packets_left_in_response > 0):
            response += self._fetch_response()

        return response

    def read_bscan(self, bscan_num, num_words=1):
        self._send_command('read bscan ' + str(bscan_num) + ' ' + str(num_words))
        return  self._fetch_response()



    #Write commands

    def write_far(self, val):
        self._send_command('write far ' + str(val))
        self._fetch_response()

    def write_cor1(self, val):
        self._send_command('write cor1 ' + str(val))
        self._fetch_response()

    #waiting on andy for implementation
    def write_bscan(self, val):
        pass
        #self._send_command('write far ' + str(hex(val)))

    def set_glutmask(self):
        self._send_command('write glutmask 1')
        return self._fetch_string()

    def clear_glutmask(self):
        self._send_command('write glutmask 0')
        return self._fetch_string()



    def ping(self):
        self._send_command('echo pong!')
        return self._fetch_string()

    def echo(self, msg):
        self._send_command('echo ' + str(msg))
        return  self._fetch_string()


    #Operation commands

    def configure(self):
        self._send_command('configure')
        return self._fetch_string()

    def readback(self):
        self._send_command('readback')
        return self._fetch_string()

    def inject_fault(self, frame_address, word_number, bit_number, num_bits_to_inject):

        #this will throw a ValueError if anything is not an int
        int_test = int(frame_address)
        int_test = int(word_number)
        int_test = int(bit_number)
        int_test = int(num_bits_to_inject)

        self._send_command('op injectfault normal ' + str(frame_address) + ' ' + str(word_number) + ' ' +
                           str(bit_number) + ' ' + str(num_bits_to_inject))
        return self._fetch_string()

    def inject_random_fault(self, num_bits_to_inject, repairFault):
        int_test = int(num_bits_to_inject)
        bool_test = bool(repairFault)
        self._send_command('op injectfault random ' + str(num_bits_to_inject) + ' ' + str(repairFault).lower())
        return self._fetch_string()

    def inject_multiframe_fault(self):
        return "not yet implemented"

    def scrub_blind(self):
        self._send_command("op scrub blind")
        print("Warning: function will stall until server function is changed")
        self._fetch_response()


    #Options commands

    def set_jtag_to_high_z(self, is_on):
        if is_on:
            self._send_command('options jtagtohighz on')
        else:
            self._send_command('options jtagtohighz off')
        return self._fetch_string()

    def set_active_device_index(self, index):
        try:
            index += 1
        except TypeError:
            return "Index parameter must be an int"
        index -= 1

        self._send_command('options activedevice ' + str(index))
        return self._fetch_string()
