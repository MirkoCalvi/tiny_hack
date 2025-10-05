import serial.tools.list_ports


if __name__ == "__main__":
    import serial.tools.list_ports

    ports = serial.tools.list_ports.comports()
    for port in ports:
        print(f"{port.device}: {port.description}")
    ser = serial.Serial(
        port='/dev/cu.usbmodem1201',   # Device path
        baudrate=921600,               # Speed (9600, 115200, etc.)
        bytesize=serial.EIGHTBITS,     # Data bits
        parity=serial.PARITY_NONE,     # Parity checking
        stopbits=serial.STOPBITS_ONE,  # Stop bits
        timeout=1,                     # Read timeout (seconds)
        write_timeout=1               # Write timeout
    )
    print(f"Connected to {ser.name}")



