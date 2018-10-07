# Jcm_Client

The JCM (Jtag Configuration Manager) is an embedded system running Arch Linux. It is used in the Configurable Computing Lab at BYU, and its purpose is to monitor the response that FPGA devices have when exposed to radiation. The JCM can also emulate the behavior of radiation and inject faults into the FPGA configuration memory, providing a safe, efficient way to do radation tests.

The Jcm Server is a program that allows a researcher to control the JCM (which connects to their FPGA) remotely and with ease. It provides an API for the researcher to use and automatically connects to and configures the JCM to the FPGA settings, so the user doesn't have to. [See the server code here.](https://github.com/ryanwest6/Jcm_server)

This is a Python API that connects to the JCM server to perform fault injection and testing on FPGA devices. Note that this API is deprecated, as it was used to connect to the C/C++ version of the server. I wrote an updated server completely in Python that is now included in the JCM image (and is proprietary so not included here).
