#!/usr/bin/python3
from api import ApiRos
from sys import argv

apiros = ApiRos(argv[1])
apiros.login(argv[2], argv[3])

addrs, _ = apiros.talk(['/ip/firewall/address-list/print'])
from collections import defaultdict
addrdict = defaultdict(
    lambda: defaultdict(
        lambda: defaultdict(
            lambda: []
        )
    )
)
for i in addrs:
    list = i.pop('list')
    disabled = i.pop('disabled') == 'true'
    dynamic = i.pop('dynamic') == 'true'
    addrdict[list][disabled][dynamic].append((i['.id'], i['address']))

for list, ad2 in addrdict.items():
    for disabled, ad3 in ad2.items():
        for dynamic, addrs in ad3.items():
            print('%s disabled: %s dynamic: %s' % (list, disabled, dynamic))
            for id, addr in addrs:
                print('\t%s %s' % (id, addr))

print(apiros.talk([
    '/ip/address/add',
    '=address=192.168.88.1',
    '=interface=asdf',
]))
