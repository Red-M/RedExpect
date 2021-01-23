# RedExpect
# Copyright (C) 2018 - 2020  Red_M ( http://bitbucket.com/Red_M )

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
import time
import re
import redssh

redssh.RedSSH.connect.__doc__ = '''
    .. warning::
        Do not use this function, instead use :func:`redexpect.RedExpect.login`.
'''

from redexpect import exceptions

class RedExpect(redssh.RedSSH):
    '''
    Instances the start of an SSH connection.
    Extra options are available after :func:`redexpect.RedExpect.login` is called.
    This only takes the arguements below and the rest are defered to :class:`redssh.RedSSH`.

    Please also note that this class inherits from :class:`redssh.RedSSH` and tries to not override anything from that.

    :param prompt: The basic prompt to expect for the first command line.
    :type prompt: ``regex string``
    :param encoding: Set the encoding to something other than the default of ``'utf16'`` when your target SSH server doesn't return UTF-16.
    :type encoding: ``str``
    :param newline: Set the newline for sending and recieving text to the remote server.
    :type newline: ``str``
    :param expect_timeout: Set the timeout in seconds for when expecting a certain string to appear, this means that the string or regex has to be matched within this time. Set to ``0`` to disable.
    :type expect_timeout: ``float``
    '''
    def __init__(self,prompt=r'.+?[\#\$]\s+',encoding='utf8',newline='\r',expect_timeout=300.0,**kwargs):
        super().__init__(**kwargs)
        self.debug = False
        self.encoding = encoding
        self.basic_prompt = prompt
        self.prompt_regex = prompt
        self.prompt_regex_SET_SH = r"PS1='[REDEXPECT]\$ '"
        self.prompt_regex_SET_CSH = r"set prompt='[REDEXPECT]\$ '"
        self.current_send_string = ''
        self.current_output = ''
        self.current_output_clean = ''
        self.newline = newline
        self.expect_timeout = expect_timeout

    def __check_for_attr__(self,attr):
        return(attr in self.__dict__)

    def device_init(self,**kwargs):
        '''
        Override this function to intialize a device that does not simply drop to the terminal or a device will kick you out if you send any key/character other than an "acceptable" one.
        This default one will work on linux quite well but devices such as pfsense or mikrotik might require this function and :func:`redexpect.RedExpect.get_unique_prompt` to be overriden.
        '''
        pass

    def login(self,*args,auto_unique_prompt=True,**kwargs):
        '''
        This uses :class:`redssh.RedSSH.connect` to connect and then login to a remote host.
        This only takes a single optional arguement and the rest are defered to :class:`redssh.RedSSH.connect`.

        :param auto_unique_prompt: Automatically set a unique prompt to search for once logged into the remote server.
        :type auto_unique_prompt: ``float``
        '''
        self.connect(*args,**kwargs)
        self.device_init()
        self.prompt()
        if auto_unique_prompt==True:
            self.set_unique_prompt()

    def sendline_raw(self,string):
        '''
        Use this when you want to directly interact with the remote session.

        :param string: String to send to the remote session.
        :type string: ``str``
        '''
        self.send(string)

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

    def get_unique_prompt(self):
        '''
        Return a unique prompt from the existing SSH session. Override this function to generate the compiled regex however you'd like, eg, from a database or from a hostname.

        :returns: compiled ``regex str``
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

    def prompt(self,additional_matches=[],timeout=None):
        '''
        Get a command line prompt in the terminal.
        Useful for using :func:`redexpect.RedExpect.sendline` to send commands
        then using this for when you want to get back to a prompt to enter further commands.

        :param additional_matches: Additional matches to count as a prompt.
        :type additional_matches: ``arr``
        :param timeout: Timeout for the prompt to be reached.
        :type timeout: ``float`` or ``int``
        :raises: :class:`redexpect.exceptions.ExpectTimeout` if the timeout for expect has been reached.
        :returns: ``int`` - Match number, ``0`` is always the prompt defined for the session.
        '''
        if not isinstance(additional_matches,type([])):
            additional_matches = [additional_matches]
        return(self.expect([self.prompt_regex]+additional_matches,timeout=timeout))

    def expect(self,re_strings='',default_match_prefix='',strip_ansi=True,timeout=None):
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
        :type re_strings: ``array`` or ``regex str``
        :param default_match_prefix: A prefix to all match regexes, defaults to ``''``.
                                     Useful for making sure you have a prefix to match the start of a prompt.
        :type default_match_prefix: ``str``
        :param strip_ansi: If ``True``, will strip ansi control chars befores regex matching.
        :type strip_ansi: ``bool``
        :param timeout: Set the timeout for this finish blocking within, setting to ``None`` takes the value from :var:`redexpect.RedExpect.expect_timeout` which can be set at first instance, set to ``0`` to disable.
        :type timeout: ``float``
        :return: ``int`` - An ``EOF`` returns ``-1``, a regex metch returns ``0`` and a match in a
                 list of regexes returns the index of the matched string in
                 the list.
        :raises: :class:`redexpect.exceptions.ExpectTimeout` if the timeout for expect has been reached.
        '''
        current_output = ''

        if isinstance(re_strings,str) and len(re_strings)!=0:
            re_strings = [re_strings]

        time_started = time.time()
        if timeout==None:
            timeout = self.expect_timeout

        while (len(re_strings)==0 or not [re_string for re_string in re_strings if re.search(default_match_prefix+re_string,current_output,re.DOTALL)]):
            for current_buffer in self.read():
                if current_buffer==None:
                    return(-1)
                # print(current_buffer)
                current_buffer_decoded = str(self.remote_text_clean(current_buffer.decode(self.encoding),strip_ansi=strip_ansi))
                # print(current_buffer_decoded)
                current_output += current_buffer_decoded
            if float(time.time()-time_started)>timeout and timeout!=0:
                raise(exceptions.ExpectTimeout(re_strings))

        if len(re_strings)!=0:
            found_pattern = [(re_index,re_string) for (re_index,re_string) in enumerate(re_strings) if re.search(default_match_prefix+re_string,current_output,re.DOTALL)]

        self.current_output = current_output
        current_output_clean = str(current_output) # memcopy hack

        if len(self.current_send_string)!=0:
            current_output_clean = current_output_clean.replace(self.current_send_string+'\n','')
        self.current_send_string = ''

        if len(re_strings)!=0 and len(found_pattern)!=0:
            # print(current_output_clean)
            self.current_output_clean = re.sub(found_pattern[0][1],'',current_output_clean)
            self.last_match = found_pattern[0][1]
            return(found_pattern[0][0])
        # else:
            # return(-1)
        # If someone manages to get a ``None`` instead of a -1 please open an issue.
        # I want to know how you did that so I can write a test for it :)

    def read(self,block=False):
        gen = super().read(block)
        if isinstance(gen,type([])):
            return(gen)
        for data in gen:
            self.out_feed(data)
            yield(data)

    def out_feed(self,raw_data):
        '''
        Override to get the raw data from the remote machine into a function.

        Useful as a way to get data from the ``expect()`` to another library without impacting the expect side.
        '''
        pass

    def command(self,cmd,clean_output=True,remove_newline=False,timeout=None):
        '''
        Run a command in the remote terminal.

        :param cmd: Command to execute, this will send characters exactly as if they were typed. (crtl+c could be sent via this).
        :type cmd: ``str``
        :param clean_output: Set to ``False`` to remove the "smart" cleaning, useful for debugging or for when you want the prompt as well.
        :type clean_output: ``bool``
        :param remove_newline: Set to ``True`` to remove the last newline on a return, useful when a command adds a newline to its output.
        :type remove_newline: ``bool``
        :param timeout: Set the timeout for this command to complete within, if set to ``None`` this will use the value of :var:`redexpect.RedExpect.expect_timeout` which can be set at first instance.
        :type timeout: ``float``

        :returns: ``str``
        :raises: :class:`redexpect.exceptions.ExpectTimeout` if the timeout for expect has been reached.
        '''
        self.sendline(cmd)
        self.prompt(timeout=timeout)
        if clean_output==True:
            out = str(self.current_output_clean)
        else:
            out = str(self.current_output)
        if remove_newline==True:
            while out.endswith('\n') or out.endswith('\r'):
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
        password_line = r'.+?asswor.+?\:\s+'
        if sudo==True:
            cmd = 'sudo '+su_cmd
        self.sendline(cmd)
        self.expect(password_line)
        self.sendline_raw(password+self.newline)
        acceptable_response = [self.basic_prompt]
        bad_response = [password_line,r'Sorry.+?\.',r'.+?Authentication failure']
        result = self.expect(re_strings=bad_response+acceptable_response) # Might be an idea to allow extra failure strings here to be more platform agnostic
        if result>=len(bad_response)-1:
            self.set_unique_prompt()
        else:
            raise(exceptions.BadSudoPassword())

