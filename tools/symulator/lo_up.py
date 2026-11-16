# Podnosi interfejs lo w nowej przestrzeni sieciowej (unshare -n) – bez narzędzia ip.
import fcntl
import socket
import struct

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
fl = struct.unpack("16sH", fcntl.ioctl(s, 0x8913, struct.pack("16sH", b"lo", 0)))[1]
fcntl.ioctl(s, 0x8914, struct.pack("16sH", b"lo", fl | 1))
