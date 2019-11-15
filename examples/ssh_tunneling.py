#!/usr/bin/env python3
import requests # This requires the socks supported requests package,
# installable via `pip install requests[socks]`.
import redexpect
import getpass

def main():
    username = input('Username: ')
    hostname = input('Hostname: ')
    passwd = getpass.getpass()
    expect = redexpect.RedExpect()

    test_string = '<title>Error 404 (Not Found)!!1</title>'
    target_host = 'google.com'

    print(hostname)
    expect.login(hostname=hostname,username=username,password=passwd,allow_agent=True,timeout=1.5)

    (local_tun_thread,local_thread_terminate,local_tun_server,local_port) = expect.local_tunnel(0,target_host,80)
    expect.remote_tunnel(2223,target_host,80)
    (dyn_tun_thread,dyn_thread_terminate,dyn_tun_server,dyn_port) = expect.dynamic_tunnel(0)
    proxies = {'http':'socks5://localhost:'+str(dyn_port),'https':'socks5://localhost:'+str(dyn_port)}
    local = requests.get('http://localhost:'+str(local_port)).text
    remote = 'curl: '+expect.command('curl http://localhost:2223/')
    dynamic = requests.get('http://'+target_host,headers={'host':'localhost'},proxies=proxies).text

    print('Local: '+str(test_string in local))
    print('Remote: '+str(test_string in remote))
    print('Dynamic: '+str(test_string in dynamic))
    print('whoami: '+expect.command('whoami',remove_newline=True))
    print('hostname: '+expect.command('hostname',remove_newline=True))

    expect.exit() # it is polite to properly exit the session, but you don't have to.


if __name__=='__main__':
    main()

