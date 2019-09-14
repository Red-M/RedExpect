import unittest
import threading
import multiprocessing
import paramiko
import redexpect

from . import paramiko_server as ssh_server


class SSHSession(object):
    def __init__(self,hostname='localhost',port=2200,class_init={},connect_args={}):
        self.rs = redexpect.RedExpect(**class_init)
        self.rs.login(hostname, port, 'redm', 'foobar!',**connect_args)



class RedExpectUnitTest(unittest.TestCase):

    def setUp(self):
        self.ssh_servers = []
        self.ssh_sessions = []

    def start_ssh_server(self):
        q = multiprocessing.Queue()
        server = multiprocessing.Process(target=ssh_server.start_server,args=(q,))
        server.start()
        self.ssh_servers.append(server)
        server_port = q.get()
        return(server_port)

    def start_ssh_session(self,server_port=None,class_init={},connect_args={}):
        server_hostname = 'localhost'
        class_init.update({'expect_timeout':1.5})
        if server_port==None:
            server_port = self.start_ssh_server()
        sshs = SSHSession(server_hostname,server_port,class_init,connect_args)
        self.ssh_sessions.append(sshs)
        return(sshs)

    def end_ssh_session(self,sshs):
        sshs.rs.exit()

    def tearDown(self):
        for session in self.ssh_sessions:
            self.end_ssh_session(session)
        for server in self.ssh_servers:
            server.kill()


    def test_basic_read_write(self):
        sshs = self.start_ssh_session()
        result = sshs.rs.command('reply',remove_newline=True)
        assert result=='PONG!'

    def test_set_prompt(self):
        sshs = self.start_ssh_session()
        sshs.rs.set_unique_prompt(True,True)

    def test_custom_sudo(self):
        sshs = self.start_ssh_session()
        sshs.rs.sudo('bar',sudo=True,su_cmd='custom_sudo')
        result = sshs.rs.command('whoami',remove_newline=True)
        assert result=='root'

    def test_good_sudo_password(self):
        sshs = self.start_ssh_session()
        sshs.rs.sudo('bar',sudo=False,su_cmd='sudo')
        result = sshs.rs.command('whoami',remove_newline=True)
        assert result=='root'

    def test_bad_sudo_password(self):
        sshs = self.start_ssh_session()
        try:
            sshs.rs.sudo('toofooforbar',sudo=False,su_cmd='sudo')
        except redexpect.exceptions.BadSudoPassword:
            result = sshs.rs.command('whoami',remove_newline=True)
            assert result=='lowly_pleb'

    def test_expect_timeout(self):
        sshs = self.start_ssh_session()
        failed_successfully = False
        try:
            sshs.rs.prompt_regex = r'nevermatches'
            sshs.rs.command('reply',remove_newline=True)
        except redexpect.exceptions.ExpectTimeout:
            failed_successfully = True
        assert failed_successfully==True


if __name__ == '__main__':
    unittest.main()

