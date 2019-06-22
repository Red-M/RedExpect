# RedExpect
# Copyright (C) 2018  Red_M ( http://bitbucket.com/Red_M )

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


import os
import re
import threading
import multiprocessing
import socket
import select
from ssh2.session import Session as ssh2_session
from ssh2.session import LIBSSH2_HOSTKEY_HASH_SHA1,LIBSSH2_HOSTKEY_TYPE_RSA
from ssh2.knownhost import LIBSSH2_KNOWNHOST_TYPE_PLAIN,LIBSSH2_KNOWNHOST_KEYENC_RAW,LIBSSH2_KNOWNHOST_KEY_SSHRSA,LIBSSH2_KNOWNHOST_KEY_SSHDSS
from ssh2.session import LIBSSH2_SESSION_BLOCK_INBOUND,LIBSSH2_SESSION_BLOCK_OUTBOUND
from ssh2.error_codes import LIBSSH2_ERROR_EAGAIN
from ssh2.sftp import LIBSSH2_FXF_TRUNC,LIBSSH2_FXF_WRITE,LIBSSH2_FXF_READ,LIBSSH2_FXF_CREAT,LIBSSH2_SFTP_S_IRUSR,LIBSSH2_SFTP_S_IWUSR,LIBSSH2_SFTP_S_IRGRP,LIBSSH2_SFTP_S_IWGRP,LIBSSH2_SFTP_S_IROTH


from redexpect import exceptions
from redexpect import tunnelling


DEFAULT_WRITE_MODE = LIBSSH2_FXF_WRITE|LIBSSH2_FXF_CREAT|LIBSSH2_FXF_TRUNC
DEFAULT_FILE_MODE = LIBSSH2_SFTP_S_IRUSR | LIBSSH2_SFTP_S_IWUSR | LIBSSH2_SFTP_S_IRGRP | LIBSSH2_SFTP_S_IWGRP | LIBSSH2_SFTP_S_IROTH

class RedExpect(object):
    '''
    Instances the start of an SSH connection.
    Extra options are available after :func:`redexpect.RedExpect.connect` is called.

    :param prompt: The basic prompt to expect for the first command line.
    :type prompt: ``regex string``
    :param encoding: Set the encoding to something other than the default of ``'utf8'`` when your target SSH server doesn't return UTF-8.
    :type encoding: ``str``
    :param newline: Set the newline for sending and recieving text to the remote server to something other than the default of ``'\\r'``.
    :type newline: ``str``
    :param terminal: Set the terminal sent to the remote server to something other than the default of ``'vt100'``.
    :type terminal: ``str``
    '''
    def __init__(self,prompt=r'.+?[\#\$]\s+',encoding='utf8',newline='\r',terminal='vt100',known_hosts=None):
        self.debug = False
        self.encoding = encoding
        self.basic_prompt = prompt
        self.prompt_regex = prompt
        self.tunnels = {'local':{},'remote':{}}
        self.current_send_string = ''
        self.current_output = ''
        self.current_output_clean = ''
        self.newline = newline
        self.terminal = terminal
        self.start_scp = self.start_sftp
        if known_hosts==None:
            self.known_hosts_path = os.path.join(os.path.expanduser('~'),'.ssh','known_hosts')
        else:
            self.known_hosts_path = known_hosts

    def __check_for_attr__(self,attr):
        return(attr in self.__dict__)

    def _block_select(self,timeout=None):
        block_direction = self.session.block_directions()
        if block_direction==0:
            return()
        rfds = []
        wfds = []
        if block_direction & LIBSSH2_SESSION_BLOCK_INBOUND:
            rfds = [self.sock]
        if block_direction & LIBSSH2_SESSION_BLOCK_OUTBOUND:
            wfds = [self.sock]
        select.select(rfds,wfds,[],timeout)

    def _block(self,func,*args,**kwargs):
        out = func(*args,**kwargs)
        while out==LIBSSH2_ERROR_EAGAIN:
            self._block_select()
            out = func(*args,**kwargs)
        return(out)

    def _block_write(self,func,data,timeout=None):
        data_len = len(data)
        total_written = 0
        while total_written<data_len:
            (rc,bytes_written) = func(data[total_written:])
            total_written+=bytes_written
            if rc==LIBSSH2_ERROR_EAGAIN:
                self._block_select(timeout)

    def _read_iter(self,func,timeout=None):
        pos = 0
        remainder_len = 0
        remainder = b''
        (size,data) = func()
        while size==LIBSSH2_ERROR_EAGAIN or size>0:
            if size==LIBSSH2_ERROR_EAGAIN:
                self._block_select(timeout)
                (size,data) = func()
            if timeout is not None and size==LIBSSH2_ERROR_EAGAIN:
                raise(StopIteration)
            while size>0:
                while pos<size:
                    if remainder_len>0:
                        yield(remainder+data[pos:size])
                        remainder = b''
                        remainder_len = 0
                    else:
                        yield(data[pos:size])
                    pos = size
                (size,data) = func()
                pos = 0
        if remainder_len > 0:
            yield(remainder)

    def check_host_key(self,hostname,port):
        self.known_hosts = self.session.knownhost_init()
        self.known_hosts.readfile(self.known_hosts_path)
        (host_key,host_key_type) = self.session.hostkey()

        if isinstance(hostname,type('')):
            hostname = hostname.encode(self.encoding)
        if host_key_type==LIBSSH2_HOSTKEY_TYPE_RSA:
            server_key_type = LIBSSH2_KNOWNHOST_KEY_SSHRSA
        else:
            server_key_type = LIBSSH2_KNOWNHOST_KEY_SSHDSS
        key_bitmask = LIBSSH2_KNOWNHOST_TYPE_PLAIN|LIBSSH2_KNOWNHOST_KEYENC_RAW|server_key_type
        self.known_hosts.checkp(hostname,port,host_key,key_bitmask)
        self.known_hosts.addc(hostname,host_key,key_bitmask)
        for hk in self.known_hosts.get():
            if hk.name==hostname:
                print(self.known_hosts.writeline(hk))

    def connect(self,hostname,port=22,username=None,password=None,pkey=None,key_filename=None,timeout=None,
        allow_agent=True,look_for_keys=True,passphrase=None,sock=None,auto_unique_prompt=True):
        '''
        .. warning::
            Some authentication methods are not yet supported!

        :param hostname: Hostname to connect to.
        :type hostname: ``str``
        :param port: SSH port to connect to.
        :type port: ``int``
        :param username: Username to connect as to the remote server.
        :type username: ``str``
        :param password: Password to offer to the remote server for authentication.
        :type password: ``str``
        :param allow_agent: Allow the local SSH key agent to offer the keys held in it for authentication.
        :type allow_agent: ``bool``
        :param pkey: Private key to offer to the remote server for authentication. NOT IMPLEMENTED!
        :type pkey: ``str``
        :param key_filename: Array of filenames to offer to the remote server. NOT IMPLEMENTED!
        :type key_filename: ``array``
        :param passphrase: Passphrase to decrypt any keys offered to the remote server. NOT IMPLEMENTED!
        :type passphrase: ``str``
        :param look_for_keys: Enable offering keys in ``~/.ssh`` automatically. NOT IMPLEMENTED!
        :type look_for_keys: ``bool``
        :param sock: A pre-connected socket to the remote server. Useful if you have strange network requirements.
        :type sock: ``socket``
        :param timeout: Timeout for the socket connection to the remote server.
        :type timeout: ``float``
        :param auto_unique_prompt: Automatically set a unique prompt to search for once logged into the remote server.
        :type auto_unique_prompt: ``float``
        '''
        if self.__check_for_attr__('past_login')==False:
            if sock==None:
                self.sock = socket.create_connection((hostname,port),timeout)
                self.sock.setsockopt(socket.SOL_SOCKET,socket.SO_KEEPALIVE,1)
            else:
                self.sock = sock
            self.session = ssh2_session()
            self.session.handshake(self.sock)

            # self.check_host_key(hostname,port)

            auth_requests = self.session.userauth_list(username)
            for auth_request in auth_requests:
                if allow_agent==True and auth_request=='publickey':
                    if allow_agent==True:
                        self.session.agent_auth(username)
                        # agent = self.session.agent_init()
                        # agent.connect()
                    elif not pkey==None:
                        pass
                    elif key_filename!=None:
                        pass
                    # self.session.userauth_publickey(username,pkey)
                    # self.session.userauth_hostbased_fromfile(username,pkey,hostname,passphrase=passphrase)
                    # self.session.userauth_publickey_fromfile(username,pkey,passphrase)
                    # self.session.userauth_publickey_frommemory(username,pkey,passphrase)
                if not password==None and (auth_request=='password' or auth_request=='keyboard-interactive'):
                    self.session.userauth_password(username,password)
                if self.session.userauth_authenticated()==True:
                    break

            self.session.set_blocking(False)
            self.channel = self._block(self.session.open_session)
            self._block(self.channel.pty,self.terminal)
            self._block(self.channel.shell)
            self.past_login = True
            self.device_init()
            self.expect(self.prompt_regex)
            if auto_unique_prompt==True:
                self.set_unique_prompt()

    def prompt(self):
        '''
        Get a command line prompt in the terminal.
        Useful for using :func:`redexpect.RedExpect.sendline` to send commands
        then using this for when you want to get back to a prompt to enter further commands.
        '''
        self.expect(self.prompt_regex)

    def sendline_raw(self,string):
        '''
        Use this when you want to directly interact with the remote session.

        :param string: String to send to the remote session.
        :type string: ``str``
        '''
        self._block_write(self.channel.write,string)

    def sendline(self,send_string,newline=None):
        '''
        Saves and sends the send string provided to the remote session with a newline added.

        :param send_string: String to send to the remote session.
        :type send_string: ``str``
        :param newline: Override the newline character sent to the remote session.
        :type newline: ``str``
        '''
        self.current_send_string = send_string
        if newline==None:
            newline = self.newline
        self.sendline_raw(send_string+newline)

    def remote_text_clean(self,string,strip_ansi=True):
        string = string.replace('\r','')
        if strip_ansi==True:
            string = re.sub(r'\x1b\[([0-9,A-Z]{1,2}(;[0-9]{1,2})?(;[0-9]{3})?)?[m|K]?','',string)
        return(string)

    def expect(self,re_strings='',default_match_prefix='',strip_ansi=True):
        '''
        This function takes in a regular expression (or regular expressions)
        that represent the last line of output from the server. The function
        waits for one or more of the terms to be matched. The regexes are
        matched using expression ``r'\\n<regex>$'`` so you'll need to provide an
        easygoing regex such as ``'.*server.*'`` if you wish to have a fuzzy
        match.

        This has been originally taken from paramiko_expect and modified to work with RedExpect.
        I've also made the style consistent with the rest of the library.

        :param re_strings: Either a regex string or list of regex strings
                           that we should expect; if this is not specified,
                           then ``EOF`` is expected (i.e. the shell is completely
                           closed after the exit command is issued)
        :param default_match_prefix: A prefix to all match regexes, defaults to ``''``.
                                     Useful for making sure you have a prefix to match the start of a prompt.
        :param strip_ansi: If ``True``, will strip ansi control chars befores regex matching.
        :return: ``int`` - An ``EOF`` returns ``-1``, a regex metch returns ``0`` and a match in a
                 list of regexes returns the index of the matched string in
                 the list.
        '''
        self.current_output = ''

        if isinstance(re_strings,str) and len(re_strings)!=0:
            re_strings = [re_strings]

        while (len(re_strings)==0 or not [re_string for re_string in re_strings if re.search(default_match_prefix+re_string,self.current_output,re.DOTALL)]):
            for current_buffer in self._read_iter(self.channel.read,0.01):
                current_buffer_decoded = self.remote_text_clean(current_buffer.decode(self.encoding),strip_ansi=strip_ansi)
                self.current_output += current_buffer_decoded

        if len(re_strings)!=0:
            found_pattern = [(re_index,re_string) for (re_index,re_string) in enumerate(re_strings) if re.search(default_match_prefix+re_string,self.current_output,re.DOTALL)]

        self.current_output_clean = self.current_output

        if len(self.current_send_string)!=0:
            self.current_output_clean = self.current_output_clean.replace(self.current_send_string+'\n','')
        self.current_send_string = ''

        if len(re_strings)!=0 and len(found_pattern)!=0:
            self.current_output_clean = re.sub(found_pattern[0][1],'',self.current_output_clean)
            self.last_match = found_pattern[0][1]
            return(found_pattern[0][0])
        else:
            return(-1)


    def device_init(self,**kwargs):
        '''
        Override this function to intialize a device that does not simply drop to the terminal or a device will kick you out if you send any key/character other than an "acceptable" one.
        This default one will work on linux quite well but devices such as pfsense or mikrotik might require this function and :func:`redexpect.RedExpect.get_unique_prompt` to be overriden.
        '''
        pass

    def get_unique_prompt(self):
        '''
        Return a unique prompt from the existing SSH session. Override this function to generate the compiled regex however you'd like, eg, from a database or from a hostname.

        :returns: compiled ``rstring``
        '''
        return(re.escape(self.command('',clean_output=False)[1:])) # A smart-ish way to get the current prompt after a dumb prompt match

    def set_unique_prompt(self,use_basic_prompt=True,set_prompt=False):
        '''
        Set a unique prompt in the existing SSH session.

        :param use_basic_prompt: Use the dumb prompt from first login to the remote terminal.
        :type use_basic_prompt: ``bool``
        :param set_prompt: Set to ``True`` to set the prompt via :var:`redexpect.RedExpect.PROMPT_SET_SH`
        :type set_prompt: ``bool``
        '''
        if use_basic_prompt==True:
            self.prompt_regex = self.basic_prompt
        if set_prompt==True:
            self.command(self.prompt_regex_SET_SH)
        self.prompt_regex = self.get_unique_prompt()

    def command(self,cmd,clean_output=True,remove_newline=False):
        '''
        Run a command in the remote terminal.

        :param cmd: Command to execute, this will send characters exactly as if they were typed. (crtl+c could be sent via this).
        :type cmd: ``str``
        :param clean_output: Set to ``False`` to remove the "smart" cleaning, useful for debugging or for when you want the prompt as well.
        :type clean_output: ``bool``
        :param remove_newline: Set to ``True`` to remove the last newline on a return, useful when a command adds a newline to its output.
        :type remove_newline: ``bool``

        :returns: ``str``
        '''
        self.sendline(cmd)
        self.prompt()
        if clean_output==True:
            out = self.current_output_clean
        else:
            out = self.current_output
        if remove_newline==True:
            if out.endswith('\n'):
                out = out[:-1]
        return(out)


    def sudo(self,password,sudo=True,su_cmd='su -'):
        '''
        Sudo up or SU up or whatever up, into higher privileges.

        :param password: Password for gaining privileges
        :type password: ``str``
        :param sudo: Set to ``False`` to allow ``su_cmd`` to be executed instead.
        :type sudo: ``bool``
        :param su_cmd: Command to be executed when ``sudo`` is ``False``, allows overriding of the ``'sudo'`` default.
        :type su_cmd: ``str``
        :return: ``None``
        :raises: :class:`redexpect.exceptions.BadSudoPassword` if the password provided does not allow for privilege escalation.
        '''
        cmd = su_cmd
        reg = r'.+?asswor.+?\:\s+'
        if sudo==True:
            cmd = 'sudo '+su_cmd
        self.sendline(cmd)
        self.expect(reg)
        self.sendline(password)
        result = self.expect(re_strings=[self.basic_prompt,reg,r'Sorry.+?\.',r'.+?Authentication failure']) # Might be an idea to allow extra failure strings here to be more platform agnostic
        if result==0:
            self.set_unique_prompt()
        else:
            raise(exceptions.BadSudoPassword())

    def start_sftp(self):
        '''
        Start the SFTP client.
        '''
        if not self.__check_for_attr__('sftp_client'):
            self.sftp_client = self._block(self.session.sftp_init)

    def sftp_open(self,remote_path,sftp_flags,file_mode):
        '''
        Open a file object over SFTP on the remote server.

        .. warning::
            This will only open files with the user you logged in as, not the current user you are running commands as.

        :param remote_path: Path that file is lcoated at on the remote server.
        :type remote_path: ``str``
        :param sftp_flags: Flags for the SFTP session to understand what you are going to do with the file.
        :type sftp_flags: ``int``
        :param file_mode: File mode for the file being opened.
        :type file_mode: ``int``
        :return: ``SFTPFileObj``
        '''
        if self.__check_for_attr__('sftp_client'):
            return(self._block(self.sftp_client.open,remote_path,sftp_flags,file_mode))

    def sftp_write(self,file_obj,data_bytes):
        '''
        Write to a file object over SFTP on the remote server.

        .. warning::
            This will only write files with the user you logged in as, not the current user you are running commands as.

        :param file_obj: SFTPFileObj to interact with.
        :type file_obj: ``SFTPFileObj``
        :param data_bytes: Bytes to write to the file with.
        :type data_bytes: ``byte str``
        :return: ``None``
        '''
        if self.__check_for_attr__('sftp_client'):
            self._block_write(file_obj.write,data_bytes)

    def sftp_read(self,file_obj,iter=False):
        '''
        Read from file object over SFTP on the remote server.

        .. warning::
            This will only read files with the user you logged in as, not the current user you are running commands as.

        :param file_obj: SFTPFileObj to interact with.
        :type file_obj: ``SFTPFileObj``
        :param iter: Flag for if you want the iterable object instead of just a byte string returned.
        :type iter: ``bool``
        :return: ``byte str`` or ``iter``
        '''
        if self.__check_for_attr__('sftp_client'):
            if iter==True:
                return(self._read_iter(file_obj.read))
            elif iter==False:
                data = b''
                iter = self._read_iter(file_obj.read)
                for chunk in iter:
                    data+=chunk
                return(data)

    def sftp_close(self,file_obj):
        '''
        Closes a file object over SFTP on the remote server. It is a good idea to delete the ``file_obj`` after calling this.

        .. warning::
            This will only close files with the user you logged in as, not the current user you are running commands as.

        :param file_obj: SFTPFileObj to interact with.
        :type file_obj: ``SFTPFileObj``
        :return: ``None``
        '''
        if self.__check_for_attr__('sftp_client'):
            self._block(file_obj.fsync)
            self._block(file_obj.close)

    def put_folder(self,local_path,remote_path,recursive=False):
        '''
        Upload an entire folder via SFTP to the remote session. Similar to ``cp -r /files/* /target``
        Also retains file permissions.

        .. warning::
            This will only upload with the user you logged in as, not the current user you are running commands as.

        :param local_path: The local path, on the machine where your code is running from, to upload from.
        :type local_path: ``str``
        :param remote_path: The remote path to upload the ``local_path`` to.
        :type remote_path: ``str``
        :param recursive: Enable recursion down multiple directories from the top level of ``local_path``.
        :type recursive: ``bool``
        '''
        if self.__check_for_attr__('sftp_client'):
            for (dirpath,dirnames,filenames) in os.walk(local_path):
                for dirname in dirnames:
                    local_dir_path = os.path.join(local_path,dirname)
                    remote_dir_path = os.path.join(remote_path,dirname)
                    if not dirname in self._block(self.sftp_client.opendir,remote_path).readdir():
                        try:
                            self._block(self.sftp_client.mkdir,remote_dir_path,os.stat(local_dir_path).st_mode)
                        except Exception as e:
                            pass
                    if recursive==True:
                        self.put_folder(local_dir_path,remote_dir_path,recursive=recursive)
                for filename in filenames:
                    local_file_path = os.path.join(dirpath,filename)
                    remote_file_base = local_file_path[len(local_path):0-len(filename)]
                    if remote_file_base.startswith('/'):
                        remote_file_base = remote_file_base[1:]
                    remote_file_path = os.path.join(os.path.join(remote_path,remote_file_base),filename)
                    self.put_file(local_file_path,remote_file_path)

    def put_file(self,local_path,remote_path):
        '''
        Upload file via SFTP to the remote session. Similar to ``cp /files/file /target``.
        Also retains file permissions.

        .. warning::
            This will only upload with the user you logged in as, not the current user you are running commands as.

        :param local_path: The local path, on the machine where your code is running from, to upload from.
        :type local_path: ``str``
        :param remote_path: The remote path to upload the ``local_path`` to.
        :type remote_path: ``str``
        '''
        if self.__check_for_attr__('sftp_client'):
            f = self._block(self.sftp_client.open,remote_path,LIBSSH2_FXF_WRITE|LIBSSH2_FXF_CREAT|LIBSSH2_FXF_TRUNC,os.stat(local_path).st_mode)
            self._block_write(f.write,open(local_path,'rb').read())
            self._block(f.close)


    def forward_tunnel(self,local_port,remote_host,remote_port,bind_addr=''):
        '''

        Forwards a port the same way the ``-L`` option does for the OpenSSH client.

        :param local_port: The local port on the local machine to connect to.
        :type local_port: ``int``
        :param remote_host: The remote host to connect to via the remote machine.
        :type remote_host: ``str``
        :param remote_port: The remote host's port to connect to via the remote machine.
        :type remote_port: ``int``
        :param bind_addr: The bind address on this machine to bind to for the local port.
        :type bind_addr: ``str``
        :return: ``tuple`` of ``(tun_thread,thread_queue,tun_server)`` this is so you can control the tunnel's thread if you need to.
        '''
        option_string = str(local_port)+':'+remote_host+':'+str(remote_port)
        if not option_string in self.tunnels['local']:
            thread_queue = multiprocessing.Queue()

            class SubHander(tunnelling.ForwardHandler):
                caller = self
                chain_host = remote_host
                chain_port = remote_port
                queue = thread_queue
                src_tup = (bind_addr,local_port)
                dst_tup = (remote_host,remote_port)

            tun_server = tunnelling.ForwardServer((bind_addr,local_port),SubHander)
            tun_thread = threading.Thread(target=tun_server.serve_forever)
            tun_thread.daemon = True
            tun_thread.name = option_string
            tun_thread.start()
            self.tunnels['local'][option_string] = (tun_thread,thread_queue,tun_server)
        return(self.tunnels['local'][option_string])

    def reverse_tunnel(self,local_port,remote_host,remote_port,bind_addr=''):
        '''
        .. warning::
            This is broken in this commit. Will be fixed later. It currently does nothing.


        Forwards a port the same way the ``-R`` option does for the OpenSSH client.

        :param local_port: The local port on the remote side to connect to.
        :type local_port: ``int``
        :param remote_host: The remote host to connect to via the local machine.
        :type remote_host: ``str``
        :param remote_port: The remote host's port to connect to via the local machine.
        :type remote_port: ``int``
        :return: ``tuple`` of ``(tun_thread,thread_queue,None)`` this is so you can control the tunnel's thread if you need to.
        '''
        return()
        option_string = str(local_port)+':'+remote_host+':'+str(remote_port)
        if not option_string in self.tunnels['remote']:
            thread_queue = multiprocessing.Queue()
            listener = self._block(self.session.forward_listen_ex,bind_addr,local_port,0,1024)
            tun_thread = threading.Thread(target=tunnelling.reverse_handler,args=(self,listener,remote_host,remote_port,local_port,thread_queue))
            tun_thread.daemon = True
            tun_thread.name = option_string
            tun_thread.start()
            self.tunnels['remote'][option_string] = (tun_thread,thread_queue,None)
        return(self.tunnels['remote'][option_string])


    def close_tunnels(self):
        '''
        Closes all SSH tunnels if any are open.
        '''
        for thread_type in self.tunnels:
            for option_string in self.tunnels[thread_type]:
                try:
                    (thread,queue,server) = self.tunnels[thread_type][option_string]
                    queue.put('terminate')
                    if not server==None:
                        server.shutdown()
                    if thread.is_alive():
                        thread.join()
                except Exception as e:
                    pass

    def exit(self):
        '''
        Kill the current session if actually connected.
        After this you might as well just free memory from the class instance.
        '''
        if self.__check_for_attr__('past_login')==True:
            if self.past_login==True:
                self.close_tunnels()
                self._block(self.channel.close)
                self._block(self.session.disconnect)
                self.sock.close()
                del self.sock,self.session,self.channel,self.past_login
