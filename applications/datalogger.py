from lib.OSCP import OSCP

print("////////////////////////////////")
print("// IoT Datalogger v0.1")
print("////////////////////////////////")
gateway = OSCP('etc/config.json')
gateway.run()
