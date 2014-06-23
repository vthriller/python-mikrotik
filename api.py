#!/usr/bin/python3
import binascii
import socket
import hashlib
from struct import pack, unpack

class ApiRos:
    "Routeros api"
    def __init__(self, host, port='8728'):
        s = None
        for af, socktype, proto, canonname, sa in socket.getaddrinfo(
            host, port,
            socket.AF_UNSPEC, socket.SOCK_STREAM,
        ):
            try: s = socket.socket(af, socktype, proto)
            except (socket.error, msg):
                s = None
                continue
            try: s.connect(sa)
            except (socket.error, msg):
                s.close()
                s = None
                continue
            break
        if s is None:
            raise RuntimeError('could not open socket')

        self.sk = s
        self.currenttag = 0

    def login(self, username, pwd):
        for repl, attrs in self.talk(["/login"]):
            chal = binascii.unhexlify((attrs['=ret']).encode('UTF-8'))
        md = hashlib.md5()
        md.update(b'\x00')
        md.update(pwd.encode('UTF-8'))
        md.update(chal)
        self.talk(["/login", "=name=" + username,
                   "=response=00" + binascii.hexlify(md.digest()).decode('UTF-8') ])

    def talk(self, words):
        if self.writeSentence(words) == 0: return
        r = []
        while 1:
            i = self.readSentence();
            if len(i) == 0: continue
            reply = i[0]
            attrs = {}
            for w in i[1:]:
                j = w.find('=', 1)
                if (j == -1):
                    attrs[w] = ''
                else:
                    attrs[w[:j]] = w[j+1:]
            r.append((reply, attrs))
            if reply == '!done': return r

    def writeSentence(self, words):
        ret = 0
        for w in words:
            self.writeWord(w)
            ret += 1
        self.writeWord('')
        return ret

    def readSentence(self):
        r = []
        while 1:
            w = self.readWord()
            if w == '': return r
            r.append(w)

    def writeWord(self, w):
        w = w.encode('utf-8')
        self.writeStr(self.len(w))
        self.writeStr(w)

    def readWord(self):
        ret = self.readStr(self.readLen()).decode('utf-8', 'replace')
        return ret

    def len(self, l):
        l = len(l)
        if l < 0x80:
            return pack('>B', l)
        elif l < 0x4000:
            l |= 0x8000
            return pack('>H', l)
        elif l < 0x200000:
            l |= 0xC00000
            return pack('>I', l)[:3]
        elif l < 0x10000000:
            l |= 0xE0000000
            return pack('>I', l)
        else:
            return '\xf0' + pack('>I', l)

    def len_len(self, c):
        ''' `c` is a len's first byte '''
        c = ord(c)
        if (c & 0x80) == 0x00: return 1
        if (c & 0xC0) == 0x80: return 2
        if (c & 0xE0) == 0xC0: return 3
        if (c & 0xF0) == 0xE0: return 4
        if (c & 0xF8) == 0xF0: return 5

    def readLen(self):
        c = self.readStr(1)
        len_extra = self.len_len(c) - 1
        if len_extra: c += self.readStr(len_extra)

        if len(c) == 1: return unpack('>B',        c)[0]
        if len(c) == 2: return unpack('>H',        c)[0] & ~0x8000
        if len(c) == 3: return unpack('>I', '\x00'+c)[0] & ~0xC00000
        if len(c) == 4: return unpack('>I',        c)[0] & ~0xE0000000
        if len(c) == 5: return unpack('>I',        c[1:])[0]

    def writeStr(self, str):
            r = self.sk.sendall(str)
            if r: raise RuntimeError("connection closed by remote end")

    def readStr(self, length):
        ret = b''
        while len(ret) < length:
            s = self.sk.recv(length - len(ret))
            if s == '': raise RuntimeError("connection closed by remote end")
            ret += s
        return ret

