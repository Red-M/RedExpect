#!/usr/bin/env python3
import redexpect
import getpass

def main():
    username = input('Username: ')
    hostname = input('Hostname: ')
    passwd = getpass.getpass()
    expect = redexpect.RedExpect()

    print(hostname)
    expect.login(hostname=hostname,username=username,password=passwd,allow_agent=True,timeout=1.5)
    print(expect.command('whoami',remove_newline=True))
    expect.exit() # it is polite to properly exit the session, but you don't have to.


if __name__=='__main__':
    main()
