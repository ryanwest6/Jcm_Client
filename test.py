from jcm import connector

print("Jcm Python API Test")
print("Establishing connection...")

j = connector.Connector()
j.connect('169.254.131.150', 3490)

print("Connected to Jcm server")

print("\n####CONNECTION TEST####")
print("Ping:", j.ping())
print("Echo hello world msg:", j.echo('Hello World!'))

print("\n####READ TEST####")
print("Status reg:\t", format(j.read_status(), '08x'))
print("Cmd Reg:\t", format(j.read_cmd(), '08x'))
print("Cor1 Reg:\t", format(j.read_cor1(), '08x'))
print("Crc Reg:\t", format(j.read_crc(), '08x'))
print("Ctrl0 Reg:\t", format(j.read_ctrl0(), '08x'))
print("Far Reg:\t", format(j.read_far(), '08x'))
print("Idcode Reg:\t", format(j.read_idcode(), '08x'))
print("VccAux:\t\t", j.read_vccaux())
print("VccInt:\t\t", j.read_vccint())
print("Cur temp:\t", j.read_cur_temp())
print("Voltage:\t", j.read_voltage())

print("\n####WRITE TEST####")
print("Before: Cor1 Reg:\t", format(j.read_cor1(), '08x'))
print("Writing Cor1 with '0'")
j.write_cor1(0)
print("After: Cor1 Reg:\t", format(j.read_cor1(), '08x'))

print("Clearing and then setting the glut mask...")
print(j.clear_glutmask() + "\n" + j.set_glutmask())

print("\n####OPERATIONS TEST####")
print("Configuring fpga... ", end='', flush=True)
print(j.configure())
print("Saving fpga readback... ", end='', flush=True)
print(j.readback())

print("\nInjecting a fault at addr 0, word 0, bit 0, 1 bit...", j.inject_fault(0, 0, 0, 1))
print("Injecting and repairing a random fault...", j.inject_random_fault(1, True))

print("\nSetting active device to 1... " + j.set_active_device_index(1))
#print("Setting active device to 0... " + j.set_active_device_index(0)) THIS CRASHES SERVER... low level function issue
print("\nTurning Jtag to High-Z on, and then off again:")
print(j.set_jtag_to_high_z(True))
print(j.set_jtag_to_high_z(False))

#BUG: this should consistently respond with the same amount. Possible fix: after receiving each packet, send acknowledge
# packet back to the server before server sends another. May also improve timing. If this stalls and stops, it is also
# because the server is not waiting for an acknowledgement before sending another tcp packet
# for x in range(0,5):
#     data = j.read_frame(0)
#     print("Frame Response length: ", len(data))
#     # print("Response data: ", data)

print("\nTest complete.")