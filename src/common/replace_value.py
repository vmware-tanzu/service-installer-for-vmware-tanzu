import json


def replaceValue(fileName, key1, key2, value):
    with open(fileName) as f:
        data = json.load(f)
        if str(key2).lower() == "false":
            data[key1] = [value]
        else:
            data[key1][0][key2] = value
    with open(fileName, 'w') as f:
        json.dump(data, f)


def replaceValueSysConfig(fileName, key1, key2, value):
    with open(fileName) as f:
        data = json.load(f)
        if str(key2).lower() == "false":
            data[key1]["server_list"] = generateDnsList(value)
        elif str(key2).lower() == "ntp":
            data[key1]["ntp_servers"] = generateNtpList(value)
        elif str(key2).lower() == "name":
            data[key1] = value
        else:
            data[key1][key2] = value
    with open(fileName, 'w') as f:
        json.dump(data, f)


def replaceCertConfig(fileName, key1, key2, value):
    with open(fileName) as f:
        data = json.load(f)
        if str(key2).lower() == "false":
            data[key1] = [value]
        else:
            data[key1][key2] = [value]
    with open(fileName, 'w') as f:
        json.dump(data, f)


def replaceSe(fileName, key1, attrName, toMatchKey, toReplaceKey, value):
    with open(fileName) as f:
        data = json.load(f)
    for a in data[key1]:
        if a[toMatchKey] == attrName:
            a[toReplaceKey] = value
    with open(fileName, 'w') as f:
        json.dump(data, f)


def replaceSeGroup(fileName, key1, key2, value):
    with open(fileName) as f:
        data = json.load(f)
        if str(key2).lower() == "false":
            data[key1] = value
        else:
            data[key1][key2] = value
    with open(fileName, 'w') as f:
        json.dump(data, f)


def replaceMac(file, mac):
    with open(file) as f:
        data = json.load(f)
    for value in data['data_vnics']:
        for x in value.values():
            if x == mac:
                value['dhcp_enabled'] = True
                break
    with open(file, 'w') as f:
        json.dump(data, f)


def generateDnsList(dnsIpList):
    dnsIpListSplits = dnsIpList.split(",")
    listing = []
    for dnsIpListSplit in dnsIpListSplits:
        listing.append({"addr": dnsIpListSplit.replace(" ", ""), "type": "V4"})
    return listing


def generateNtpList(ntpList):
    ntpIpListSplits = ntpList.split(",")
    listing = []
    for ntpIpListSplit in ntpIpListSplits:
        dic = dict(server=dict(addr=ntpIpListSplit.replace(" ", ""), type="DNS"))
        listing.append(dic)
    return listing


def generateVsphereConfiguredSubnets(filename, beginIp, endIp, prefixIp, prefixMask):
    with open(filename) as f:
        data = json.load(f)
    listing = []
    listofstaticip = []
    test = dict(range=dict(begin=dict(addr=beginIp, type="V4"), end=dict(addr=endIp, type="V4")),
                type="STATIC_IPS_FOR_VIP_AND_SE")
    listofstaticip.append(test)
    listing.append(
        dict(prefix=dict(ip_addr=dict(addr=prefixIp, type="V4"), mask=prefixMask), static_ip_ranges=listofstaticip))
    dic = dict(configured_subnets=listing)
    data.update(dic)
    with open(filename, 'w') as f:
        json.dump(data, f)


def generateVsphereConfiguredSubnetsForSe(filename, seBeginIp, seEndIp, prefixIp, prefixMask):
    with open(filename) as f:
        data = json.load(f)
    listing = []
    listofstaticip = []
    test1 = dict(range=dict(begin=dict(addr=seBeginIp, type="V4"), end=dict(addr=seEndIp, type="V4")),
                 type="STATIC_IPS_FOR_SE")
    listofstaticip.append(test1)
    listing.append(
        dict(prefix=dict(ip_addr=dict(addr=prefixIp, type="V4"), mask=prefixMask), static_ip_ranges=listofstaticip))
    dic = dict(configured_subnets=listing)
    data.update(dic)
    json_object_m = json.dumps(data, indent=4)
    with open(filename, 'w') as f:
        f.write(json_object_m)
