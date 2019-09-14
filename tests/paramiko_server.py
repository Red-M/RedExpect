#!/usr/bin/env python

# Copyright (C) 2003-2007  Robey Pointer <robeypointer@gmail.com>
#
# This file is part of paramiko.
#
# Paramiko is free software; you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# Paramiko is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Paramiko; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA.

import base64
from binascii import hexlify
import os
import subprocess
import socket
import sys
import threading
import cryptography
import traceback

import paramiko
from paramiko.py3compat import b, u, decodebytes
from sftpserver.stub_sftp import StubServer, StubSFTPServer

StubSFTPServer.ROOT = '/tmp'

server_port = 0 # pick one for me!
server_prompt = '$'
line_endings = '\r\n'

class Server(StubServer):
    def __init__(self):
        self.pkey = paramiko.RSAKey.generate(bits=1024, progress_func=None)
        self.event = threading.Event()

    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return(paramiko.OPEN_SUCCEEDED)
        return(paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED)

    def check_port_forward_request(self, address, port):
        print((address, port))
        return(port)

    def check_auth_password(self, username, password):
        if (username == 'redm') and (password == 'foobar!'):
            return(paramiko.AUTH_SUCCESSFUL)
        return(paramiko.AUTH_FAILED)

    def check_auth_publickey(self, username, key):
        print('Auth attempt with key: ' + u(hexlify(key.get_fingerprint())))
        if (username == 'robey') and (key == self.pkey):
            return(paramiko.AUTH_SUCCESSFUL)
        return(paramiko.AUTH_FAILED)

    def check_auth_gssapi_with_mic(self, username, gss_authenticated=paramiko.AUTH_FAILED, cc_file=None):
        if gss_authenticated == paramiko.AUTH_SUCCESSFUL:
            return paramiko.AUTH_SUCCESSFUL
        return(paramiko.AUTH_FAILED)

    def check_auth_gssapi_keyex(self, username, gss_authenticated=paramiko.AUTH_FAILED, cc_file=None):
        if gss_authenticated == paramiko.AUTH_SUCCESSFUL:
            return(paramiko.AUTH_SUCCESSFUL)
        return(paramiko.AUTH_FAILED)

    def enable_auth_gssapi(self):
        return(True)

    def get_allowed_auths(self, username):
        return('gssapi-keyex,gssapi-with-mic,password,publickey')

    def check_channel_shell_request(self, channel):
        self.event.set()
        return(True)

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        return(True)

class Commands(object):
    def __init__(self, chan):
        global server_port,server_prompt
        self.chan = chan
        self.server_prompt = server_prompt

    def send(self, line):
        self.chan.send(line+line_endings)

    def tunnel_test(self, line):
        time.sleep(5)
        self.chan.close()

    def cmd_reply(self):
        self.send('PONG!')

    def cmd_sudo(self):
        self.chan.send('[sudo] password for lowly_pleb: ')
        f = self.chan.makefile('rU')
        received_passwd = f.readline().strip('\r\n')
        self.send('')
        if received_passwd=='bar':
            self.server_prompt = '#'
        else:
            self.send('Sorry, try again.')

    def cmd_sudo_custom_sudo(self):
        self.cmd_sudo()

    def cmd_whoami(self):
        whoswho = {'$':'lowly_pleb','#':'root'}
        self.send(whoswho[self.server_prompt])

    def cmd_exit(self):
        self.send('END OF TEST')
        self.chan.close()


def start_server(queue):
    global server_port,server_prompt
    DoGSSAPIKeyExchange = False

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', server_port))
        queue.put(sock.getsockname()[1])
    except Exception as e:
        print('*** Bind failed: ' + str(e))
        traceback.print_exc()
        sys.exit(1)

    try:
        sock.listen(100)
        print('Listening for connection ...')
        client, addr = sock.accept()
    except Exception as e:
        print('*** Listen/accept failed: ' + str(e))
        traceback.print_exc()
        sys.exit(1)

    print('Got a connection!')

    try:
        t = paramiko.Transport(client, gss_kex=DoGSSAPIKeyExchange)

        t.set_subsystem_handler('sftp', paramiko.SFTPServer, StubSFTPServer)
        t.set_gss_host(socket.getfqdn(''))
        try:
            t.load_server_moduli()
        except:
            print('(Failed to load moduli -- gex will be unsupported.)')
            raise
        server = Server()
        t.add_server_key(server.pkey)
        try:
            t.start_server(server=server)
        except paramiko.SSHException:
            print('*** SSH negotiation failed.')
            sys.exit(1)

        # wait for auth
        chan = t.accept(20)
        if chan is None:
            print('*** No channel.')
            sys.exit(1)
        print('Authenticated!')

        server.event.wait(10)
        if not server.event.is_set():
            print('*** Client never asked for a shell.')
            sys.exit(1)

        commands = Commands(chan)
        chan.send('MOTD'+line_endings)
        command = ''
        while not command=='cmd_exit':
            chan.send(line_endings+'Command'+server_prompt+' ')
            f = chan.makefile('rU')
            command = 'cmd_'+f.readline().strip('\r\n').replace(' ','_')
            print('Got: '+command)
            # chan.send(line_endings)
            if command in dir(commands):
                func = getattr(commands,command)
                func()

    except Exception as e:
        print('*** Caught exception: ' + str(e.__class__) + ': ' + str(e))
        traceback.print_exc()
        try:
            t.close()
        except:
            pass
        # sys.exit(1)
