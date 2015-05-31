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
from numpy import array, dtype
import gzip, zlib
from cStringIO import StringIO
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

def gunzip(data):
	return gzip.GzipFile(fileobj=StringIO(data)).read()

def try_gunzip(data):
	try:
		data = gunzip(data)
	except IOError, zlib.error:
		pass
	return data

def _serialize(tag_type, ctx):
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
		returnval = []
		for i in xrange(list_length):
			tag = _serialize(list_type,ctx)
			returnval.append(tag)
	elif tag_type == 10:
		returnval = _NBTtoDict(ctx)
	return returnval

def load_string(ctx):
	data = ctx.data[ctx.offset:]
	(string_len,) = struct.Struct(">H").unpack_from(data)

	value = data[2:string_len + 2].tostring()
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
		tag = _serialize(tag_type, ctx)

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



def load(buf):
	"""Get a dict object from a NBT string."""
	return _load(try_gunzip(buf))