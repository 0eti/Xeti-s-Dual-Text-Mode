"""Read and write Ren'Py RPA-3.0 archives (the layout dual_text_mod.rpa uses).

The index is a zlib-compressed pickle of {name: [(offset ^ key, length ^ key)]}. Reading uses a
restricted unpickler, so an archive from elsewhere cannot run code while it is listed or unpacked.
"""

import codecs
import io
import os
import pickle
import zlib

KEY = 0xDEADBEEF


def write(path, root, names):
    """Pack `names` (paths relative to `root`, with forward slashes) into an archive at `path`."""
    with open(path, "wb") as f:
        f.write(b"RPA-3.0 %016x %08x\n" % (0, KEY))
        index = {}
        for name in names:
            with open(os.path.join(root, name), "rb") as src:
                data = src.read()
            offset = f.tell()
            f.write(data)
            index[name] = [(offset ^ KEY, len(data) ^ KEY)]
        index_offset = f.tell()
        f.write(zlib.compress(pickle.dumps(index, 2)))
        f.seek(0)
        f.write(b"RPA-3.0 %016x %08x\n" % (index_offset, KEY))


class _SafeUnpickler(pickle.Unpickler):

    def find_class(self, module, name):
        # Ren'Py writes byte strings in Python 2 style indexes through _codecs.encode.
        if (module, name) == ("_codecs", "encode"):
            return codecs.encode
        raise pickle.UnpicklingError("blocked %s.%s" % (module, name))


def read(path):
    """Return {name: bytes} for every file in the archive."""
    with open(path, "rb") as f:
        header = f.readline().split()
        if header[0] != b"RPA-3.0":
            raise ValueError("%s is not an RPA-3.0 archive" % path)
        index_offset, key = int(header[1], 16), int(header[2], 16)
        f.seek(index_offset)
        index = _SafeUnpickler(io.BytesIO(zlib.decompress(f.read())), encoding="bytes").load()

        files = {}
        for name, parts in index.items():
            if isinstance(name, bytes):
                name = name.decode("utf-8")
            part = parts[0]
            offset, length = part[0] ^ key, part[1] ^ key
            start = part[2] if len(part) > 2 else b""
            if isinstance(start, str):
                start = start.encode("latin-1")
            f.seek(offset)
            files[name] = start + f.read(length - len(start))
        return files
