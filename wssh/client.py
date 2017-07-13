import os
import codecs
import sys
import signal
import errno

import websocket
import select

import termios
import tty
import fcntl
import struct
import platform
import ssl

try:
    import simplejson as json
except ImportError:
    import json


def _pty_size(utf_in, utf_out):
    rows, cols = 24, 80
    # Can't do much for Windows
    if platform.system() == 'Windows':
        return rows, cols
    fmt = 'HH'
    buffer = struct.pack(fmt, 0, 0)
    result = fcntl.ioctl(utf_out.fileno(), termios.TIOCGWINSZ,
        buffer)
    rows, cols = struct.unpack(fmt, result)
    return rows, cols


def _resize(ws, utf_in, utf_out):
    rows, cols = _pty_size(utf_in, utf_out)
    ws.send(json.dumps({'resize': {'width': cols, 'height': rows}}))


def invoke_shell(endpoint, header = None):
    UTF8Reader = codecs.getreader('utf8')
    utf_in = UTF8Reader(sys.stdin)
    UTF8Writer = codecs.getwriter('utf8')
    utf_out = UTF8Writer(sys.stdout)
    ssh = websocket.create_connection(url = endpoint, header = header, sslopt={"cert_reqs": ssl.CERT_NONE})
    _resize(ssh, utf_in, utf_out)
    oldtty = termios.tcgetattr(utf_in)
    old_handler = signal.getsignal(signal.SIGWINCH)

    def on_term_resize(signum, frame):
        _resize(ssh, utf_in, utf_out)
    signal.signal(signal.SIGWINCH, on_term_resize)

    try:
        tty.setraw(utf_in.fileno())
        tty.setcbreak(utf_in.fileno())

        rows, cols = _pty_size(utf_in, utf_out)
        ssh.send(json.dumps({'resize': {'width': cols, 'height': rows}}))

        while True:
            try:
                r, w, e = select.select([ssh.sock, utf_in], [], [])
                if ssh.sock in r:
                    data = ssh.recv()
                    if not data:
                        break
                    message = json.loads(data)
                    if 'error' in message:
                        utf_out.write(message['error'])
                        break
                    utf_out.write(message['data'])
                    utf_out.flush()
                if utf_in in r:
                    x = os.read(utf_in.fileno(), 3)
                    if len(x) == 0:
                        break
                    ssh.send(json.dumps({'data': x}))
            except (select.error, IOError) as e:
                if e.args and e.args[0] == errno.EINTR:
                    pass
                else:
                    raise
    except websocket.WebSocketException:
        raise
    finally:
        termios.tcsetattr(utf_in, termios.TCSADRAIN, oldtty)
        signal.signal(signal.SIGWINCH, old_handler)
        print '\n'
