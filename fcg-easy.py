#!/usr/bin/env python
import sys, os, commands, tempfile, argparse

def parse_args(cmdline):
    parser = argparse.ArgumentParser(description='This is a description of %(prog)s', epilog='This is a epilog of %(prog)s', prefix_chars='-+', fromfile_prefix_chars='@', formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    subparsers  = parser.add_subparsers(help='sub-command help')

    create_parser = subparsers.add_parser('create', help='fcg-easy create -h')
    create_parser.add_argument('-g', '--group', type=str)
    create_parser.add_argument('-d', '--disk', nargs='+', type=str)
    create_parser.add_argument('-c', '--cachedev', nargs='+', type=str)
    create_parser.set_defaults(func=main_create)

    delete_parser = subparsers.add_parser('delete', help='fcg-easy delete -h')
    delete_parser.add_argument('-g', '--group', type=str)
    delete_parser.set_defaults(func=main_delete)

    args = parser.parse_args(cmdline)
    if args.group == None:
        parser.print_help()
    args.func(args)

def _os_execute(cmd):
    ret, output = commands.getstatusoutput(cmd)
    if ret == '0' or ret == 0:
        return output
    else:
        raise Exception(output)

def _get_dev_sector_count(dev):
    # try /dev/block/xxx/size
    cmd = 'blockdev --getsz %s'%dev
    devSector = _os_execute(cmd)
    if type(devSector) != int:
        try:
            devSector = int(devSector)
        except:
            return 0
    return devSector

def _sectors2MB(sectors):
    return str(sectors*512/1024/1024) + 'M'

def _linear_map_table(devices):
    table = ''
    startSector = 0
    for device in devices:
        if not os.path.exists(device):
            raise Exception('Device %s does NOT exist...' % device)
        sector = _get_dev_sector_count(device)
        if sector <= 0:
            raise Exception('Device %s is EMPTY...' % device)
        table +=  '%d %d linear %s 0\n' % (startSector, sector, device)
        startSector += sector
    return table

def _write2tempfile(content):
    temp = tempfile.NamedTemporaryFile(delete=False)
    temp.write(content)
    temp.close()
    return temp.name

def _create_table(name, table):
    tmpTableFile = _write2tempfile(table)
    cmd = 'dmsetup create %s %s' % (name, tmpTableFile)
    try:
        _os_execute(cmd)
        return True
    except Exception, ErrMsg:
        print cmd + ': ',
        print ErrMsg
        return False

def _delete_table(name):
    cmd = 'dmsetup remove %s' % name
    try:
        _os_execute(cmd)
        return True
    except Exception, ErrMsg:
        print cmd + ': ',
        print ErrMsg
        return False

def _get_table(name):
    cmd = 'dmsetup table %s' % name
    try:
        table = _os_execute(cmd)
        return table
    except Exception, ErrMsg:
        print cmd + ': ',
        print ErrMsg
        return None

def _create_flashcache(cacheName, cacheDevice, groupDevice):
    cacheSize = _sectors2MB(_get_dev_sector_count(cacheDevice))
    cmd = 'flashcache_create -p back -b 4k -s %s %s %s %s' % (cacheSize, cacheName, cacheDevice, groupDevice)
    try:
        _os_execute(cmd)
        return True
    except Exception, ErrMsg:
        print cmd + ': ',
        print ErrMsg
        return False

def _delete_flashcache(cacheName, cacheDevice):
    ret = _delete_table(cacheName)
    if ret == False:
        return False
    cmd = 'flashcache_destroy -f %s' % cacheDevice
    try:
        _os_execute(cmd)
        return True
    except Exception, ErrMsg:
        print cmd + ': ',
        print ErrMsg
        return False

def _get_cache_ssd_dev(cacheName):
        cmd = "dmsetup table %s|grep ssd|grep dev|awk '{print $3}'" % cacheName
        ssd_dev = _os_execute(cmd)[1:-2]
        return ssd_dev

def _get_device_name(device):
    name = device.split('/')[-1:][0]
    return name

def _cached_tables(devices, cacheGroupDevice):
    names = []
    tables = []
    startSector = 0
    for device in devices:
        name = 'cached-' + _get_device_name(device) 
        names.append(name)
        sector = _get_dev_sector_count(device)
        table = '0 %d linear %s %d\n' % (sector, cacheGroupDevice, startSector)
        tables.append(table)
        startSector += sector
    assert len(names) == len(tables), 'Something BAD happened when try to get cached tables...'
    return names, tables

def _get_devname_from_major_minor(majorMinor):
    cmd = "ls -l /dev/block|awk '{print $9, $11}'|grep %s" % majorMinor
    _, deviceName = _os_execute(cmd).split()
    deviceName = deviceName.split('/')[-1:][0]
    if majorMinor.split(':')[0] == '253':
        cmd = "ls -l /dev/mapper|awk '{if ($11 != \"\") print $11, $9}'|grep %s"% deviceName
        _, deviceName = _os_execute(cmd).split()
        return '/dev/mapper/%s' % deviceName   
    else:
        return '/dev/%s' % deviceName

def _is_device_busy(device):
    cmd = 'fuser %s' % device
    try:
        output = _os_execute(cmd)
        if output == '':
            return False
        else:
            return True
    except Exception, e:
        return False

def main_create(args):
    if args.group == None or args.disk == None or args.cachedev == None:
        return
    create_group(args.group, args.disk, args.cachedev)

def create_group(groupName, hddDevs, cacheDevs):
    #create linear device group
    groupTable = ''
    try:
        groupTable = _linear_map_table(hddDevs)
    except Exception, e:
        print e
        return

    cacheDevTable = ''
    try:
        cacheDevTable = _linear_map_table(cacheDevs)
    except Exception, e:
        print e
        return

    cacheDevName = 'cachedevices-%s' % groupName

    ret =  _create_table(groupName, groupTable)
    if ret == False:
        return
    ret = _create_table(cacheDevName, cacheDevTable)
    if ret == False:
        _delete_table(groupName)
        return

    #create flashcache
    groupDevice = '/dev/mapper/%s' % groupName
    cacheDevice = '/dev/mapper/%s' % cacheDevName
    cacheName = 'cachegroup-%s' % groupName
    ret = _create_flashcache(cacheName, cacheDevice, groupDevice)
    if ret == False:
        _delete_table(groupName)
        _delete_table(cacheDevName)
        return

    #create cached devices
    cacheGroupDevice = '/dev/mapper/%s' % cacheName
    cachedNames, cachedTables = _cached_tables(hddDevs, cacheGroupDevice)
    for i in range(len(cachedNames)):
        ret = _create_table(cachedNames[i], cachedTables[i])
        if ret == False:
            for j in range(i):
                _delete_table(cachedNames[j])
            _delete_flashcache(cacheName, cacheDevice)
            _delete_table(groupName)
            _delete_table(cacheDevName)
            return

def main_delete(args):
    if args.group == None:
        return
    delete_group(args.group)

def delete_group(groupName):
    groupTable = _get_table(groupName)
    if groupTable == None:
        print "Group %s dose NOT exist..." % groupName
        return
    hddDevices = []
    hddNames = []
    cachedDevices = []
    for line in groupTable.split('\n'):
        if line == '':
            continue
        line = line.split()
        while '' in line:
            line.remove('')
        if len(line) == 5:
            hddDevice = line[3]
            try:
                major, minor = [int(x) for x in hddDevice.split(':')]
                hddDevice = _get_devname_from_major_minor(hddDevice)
            except Exception, e:
                pass
            hddDevices.append(hddDevice)
            hddName = hddDevice.split('/')[-1:][0]
            hddNames.append(hddName)
            cachedDevices.append('cached-' + hddName)

    isbusy = False
    busyDev = ''
    for cachedDev in cachedDevices:
        if _is_device_busy('/dev/mapper/' + cachedDev):
            isbusy = True
            busyDev = cachedDev
            break
    if isbusy:
        print "Delete group %s failed, %s is busy..." % (groupName, busyDev)
        return

    cacheName = 'cachegroup-%s' % groupName
    ssd = _get_cache_ssd_dev(cacheName)
    for cachedDev in cachedDevices:
        _delete_table(cachedDev)
    _delete_flashcache(cacheName, ssd)
    _delete_table(groupName)
    _delete_table(ssd)
            
    
if __name__ == '__main__':
    parse_args(sys.argv[1:])
