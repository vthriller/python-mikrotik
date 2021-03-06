#!/usr/bin/python3
import binascii
import socket
import hashlib
from struct import pack, unpack

__all__ = 'Trap Fatal API'.split()

class Trap(Exception): pass
class Fatal(Exception): pass

class Query:
	def __init__(self, api, cmd):
		self.api = api
		self.words = [cmd]
	def has(self, k):
		self.words.append('?%s' % k)
		return self
	def hasnot(self, k):
		self.words.append('?-%s' % k)
		return self
	def eq(self, k, v):
		self.words.append('?=%s=%s' % (k, v))
		return self
	def lt(self, k, v):
		self.words.append('?<%s=%s' % (k, v))
		return self
	def gt(self, k, v):
		self.words.append('?>%s=%s' % (k, v))
		return self
	def n(self): # not is a reserved word
		self.words.append('?#!')
		return self
	def o(self): # or is a reserved word
		self.words.append('?#|')
		return self
	def a(self): # and is a reserved word
		self.words.append('?#&')
		return self
	def __call__(self):
		return self.api.talk(self.words)

class API:
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

	###

	def read(self, length):
		ret = b''
		while len(ret) < length:
			s = self.sk.recv(length - len(ret))
			if s == '': raise RuntimeError("connection closed by remote end")
			ret += s
		return ret

	def write(self, str):
			r = self.sk.sendall(str)
			if r: raise RuntimeError("connection closed by remote end")

	###

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

	def read_len(self):
		c = self.read(1)
		len_extra = self.len_len(c) - 1
		if len_extra: c += self.read(len_extra)

		if len(c) == 1: return unpack('>B',        c)[0]
		if len(c) == 2: return unpack('>H',        c)[0] & ~0x8000
		if len(c) == 3: return unpack('>I', '\x00'+c)[0] & ~0xC00000
		if len(c) == 4: return unpack('>I',        c)[0] & ~0xE0000000
		if len(c) == 5: return unpack('>I',        c[1:])[0]

	###

	def read_word(self):
		ret = self.read(self.read_len()).decode('utf-8', 'replace')
		return ret

	def write_word(self, w):
		w = w.encode('utf-8')
		self.write(self.len(w))
		self.write(w)

	###

	def read_sentence(self):
		r = []
		while 1:
			w = self.read_word()
			if w == '': return r
			r.append(w)

	def write_sentence(self, words):
		for w in words:
			self.write_word(w)
		self.write_word('')

	###

	def talk(self, words):
		self.write_sentence(words)
		re = []
		done = {}
		while 1:
			snt = self.read_sentence()
			if len(snt) == 0: continue
			reply = snt[0]
			attrs = {}
			for w in snt[1:]:
				w = w[1:] # drop leading '='
				try:
					k, v = w.split('=', 1)
				except TypeError:
					k, v = w, ''
				attrs[k] = v

			if reply == '!trap':
				raise Trap(attrs['message'])
			if reply == '!fatal':
				self.sk.close()
				raise Fatal() # TODO message?
			if reply == '!done':
				done = attrs
			elif reply == '!re':
				re.append(attrs)
			else: raise RuntimeError('Unknown reply %s' % reply)
			if reply == '!done': return re, done

	def query(self, cmd):
		return Query(self, cmd)

	###

	def login(self, username, pwd):
		re, done = self.talk(["/login"])
		chal = binascii.unhexlify((done['ret']).encode('UTF-8'))
		md = hashlib.md5()
		md.update(b'\x00')
		md.update(pwd.encode('UTF-8'))
		md.update(chal)
		self.talk([
			'/login',
			'=name=' + username,
			'=response=00' + binascii.hexlify(md.digest()).decode('UTF-8')
		])
