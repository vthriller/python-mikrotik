#!/usr/bin/python3
from mikrotik import API
from sys import argv

router = API(argv[1])
router.login(argv[2], argv[3])

addrs, _ = router.query('/ip/firewall/address-list/print').eq('disabled', 'false').eq('dynamic', 'false')()
from collections import defaultdict
addrdict = defaultdict(lambda: [])
for i in addrs:
    list = i.pop('list')
    addrdict[list].append((i['.id'], i['address']))

for list, addrs in addrdict.items():
    print('%s' % list)
    for id, addr in addrs:
        print('\t%s %s' % (id, addr))

print(router.talk([
    '/ip/address/add',
    '=address=192.168.88.1',
    '=interface=asdf',
]))
