"""
Library for editing Named Binary Tag (NBT) files.
Based on the work of codewarrior0, creator of MCEdit.
Can convert raw NBT data to JSON, and vice versa.
by Wire Segal
"""

from numpy import fromstring
from numpy import int8 as byte
from numpy import int16 as short
from numpy import int32 as cint
from numpy import int64 as clong
from numpy import float32 as cfloat
from numpy import float64 as double
from numpy import array, dtype, ndarray
import gzip, zlib
from io import StringIO,BytesIO
import struct

def bytearray(object, copy=True, order=None, subok=False, ndmin=0):
	return array(object, dtype='uint8', copy=copy, order=order, subok=subok, ndmin=ndmin)
def intarray(object, copy=True, order=None, subok=False, ndmin=0):
	return array(object, dtype='>u4', copy=copy, order=order, subok=subok, ndmin=ndmin)
def shortarray(array, object, copy=True, order=None, subok=False, ndmin=0):
	return array(object, dtype='>u2', copy=copy, order=order, subok=subok, ndmin=ndmin)

TYPES = {
	1: byte,
	2: short,
	3: cint,
	4: clong,
	5: cfloat,
	6: double,
	7: bytearray,
	8: str,
	9: list,
	10: dict,
	11: intarray,
	12: shortarray
}
ARRAYTYPES = {
	'uint8': 7,
	'uint32': 11,
	'uint16': 12
}
INVTYPES = {v: k for k, v in TYPES.items()}

STRUCTS = {
	1: struct.Struct(">b"),
	2: struct.Struct(">h"),
	3: struct.Struct(">i"),
	4: struct.Struct(">q"),
	5: struct.Struct(">f"),
	6: struct.Struct(">d"),
	7: struct.Struct(">b"),
	11:struct.Struct(">i"),
	12:struct.Struct(">h")
}

DTYPES = {
	7:dtype('uint8'),
	11:dtype('>u4'),
	12:dtype('>u2')
}

def write_string(string, buf):
	encoded = string

	buf.write(struct.pack(">h%ds" % (len(encoded),), len(encoded), encoded))

def gunzip(data):
	return gzip.GzipFile(fileobj=BytesIO(data)).read()

def try_gunzip(data):
    data = gunzip(data)
    return data

def _serialize(data, buf):
	if isinstance(data, int):
		data = cint(data)
	elif isinstance(data, float):
		data = cfloat(data)
	if type(data) in [byte, short, cint, clong, cfloat, double]:
		buf.write(STRUCTS[INVTYPES[type(data)]].pack(data))
	elif isinstance(data, str):
		write_string(data, buf)
	elif isinstance(data, list):
		buf.write(chr(data[0]))
		buf.write(STRUCTS[3].pack(len(data)-1))
		for i in data[1:]:
			_serialize(i, buf)
	elif isinstance(data, dict):
		for tag in data:
			if isinstance(data[tag], ndarray):
				buf.write(chr(ARRAYTYPES[data[tag].dtype.name]))
			else:
				buf.write(chr(INVTYPES[type(data[tag])]))
			write_string(tag, buf)
			_serialize(data[tag], buf)

		buf.write(chr(0))
	elif isinstance(data, ndarray):
		value_str = data.tostring()
		buf.write(struct.pack(">I%ds" % (len(value_str),), data.size, value_str))


def _unpack(tag_type, ctx):
	returnval = None
	if tag_type > 0 and tag_type < 7:
		data = ctx.data[ctx.offset:]
		fmt = STRUCTS[tag_type]
		(value,) = fmt.unpack_from(data)
		returnval = TYPES[tag_type](value)
		ctx.offset += fmt.size
	elif tag_type == 7 or tag_type == 11 or tag_type == 12:
		data = ctx.data[ctx.offset:]
		fmt = STRUCTS[tag_type]
		(string_len,) = fmt.unpack_from(data)
		value = fromstring(data[4:string_len * DTYPES[tag_type].itemsize + 4], DTYPES[tag_type])
		returnval = TYPES[tag_type](value)
		ctx.offset += string_len * DTYPES[tag_type].itemsize + 4
	elif tag_type == 8:
		returnval = load_string(ctx)
	elif tag_type == 9:
		list_type = ctx.data[ctx.offset]
		ctx.offset += 1

		(list_length,) = STRUCTS[3].unpack_from(ctx.data, ctx.offset)
		ctx.offset += STRUCTS[3].size
		returnval = [list_type]
		for i in range(list_length):
			tag = _unpack(list_type,ctx)
			returnval.append(tag)
	elif tag_type == 10:
		returnval = _NBTtoDict(ctx)
	return returnval

def load_string(ctx):
	data = ctx.data[ctx.offset:]
	(string_len,) = struct.Struct(">H").unpack_from(data)

	value = str(data[2:string_len + 2],encoding="utf-8")
	ctx.offset += string_len + 2
	return value

def _NBTtoDict(ctx):
	obj = {}
	while ctx.offset < len(ctx.data):
		tag_type = ctx.data[ctx.offset]
		ctx.offset += 1
		if tag_type == 0:
			break

		name = load_string(ctx)
		tag = _unpack(tag_type, ctx)

		obj[name] = tag
	return obj

class ctxobj(object):
	pass


def _load(buf):
	if isinstance(buf, str):
		buf = fromstring(buf, 'uint8')
	data = buf
	if not len(data):
		raise ValueError("Cannot read tag of 0 length")
	if data[0] != 10:
		raise ValueError("No root Compound object")
	ctx = ctxobj()
	ctx.offset = 1
	ctx.data = data

	name = load_string(ctx)

	return _NBTtoDict(ctx)

def save(data, compressed=True):
	buf = StringIO()
	buf.write(chr(10))
	write_string("", buf)
	_serialize(data, buf)
	outdata = buf.getvalue()

	if compressed:
		gzio = StringIO()
		gz = gzip.GzipFile(fileobj=gzio, mode='wb')
		gz.write(outdata)
		gz.close()
		outdata = gzio.getvalue()
	return outdata

def load(buf):
	"""Get a dict object from a NBT string."""
	return _load(try_gunzip(buf))
