#!/usr/bin/python3
from api import ApiRos
from sys import argv

apiros = ApiRos(argv[1])
apiros.login(argv[2], argv[3])

addrs, _ = apiros.query('/ip/firewall/address-list/print').eq('disabled', 'false').eq('dynamic', 'false')()
from collections import defaultdict
addrdict = defaultdict(lambda: [])
for i in addrs:
    list = i.pop('list')
    addrdict[list].append((i['.id'], i['address']))

for list, addrs in addrdict.items():
    print('%s' % list)
    for id, addr in addrs:
        print('\t%s %s' % (id, addr))

print(apiros.talk([
    '/ip/address/add',
    '=address=192.168.88.1',
    '=interface=asdf',
]))
