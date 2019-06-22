#!/usr/bin/env python3
import redexpect
import getpass

def main():
    username = input('Username: ')
    hostname = input('Hostname: ')
    passwd = getpass.getpass()
    expect = redexpect.RedExpect()

    print(hostname)
    expect.connect(hostname=hostname,username=username,password=passwd,timeout=1.5)
    print(expect.command('whoami',remove_newline=True))
    expect.exit()


if __name__=='__main__':
    main()
