#!/usr/bin/env python3
import redexpect
import getpass

def main():
    username = input('Username: ')
    passwd = getpass.getpass()
    hostnames = [
        'localhost',
        'test_machine',
        'etc'
    ]

    for hostname in hostnames:
        expect = redexpect.RedExpect()
        print(hostname)
        expect.login(hostname=hostname,username=username,password=passwd,timeout=1.5)
        print(expect.command('whoami',remove_newline=True))
        expect.exit() # it is polite to properly exit the session, but you don't have to.


if __name__=='__main__':
    main()
