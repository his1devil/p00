#! /usr/bin/env python
# -*- coding: utf-8 -*-
import subprocess
import ConfigParser
try:
    import simplejson as json
except ImportError:
    import json
# from collections import OrderedDict new in 2.7 ;(
import re
import urllib2


class Config(object):
    """
    读取配置文件
    """
    def __init__(self, configure_file_path):
        self.configure_file_path = configure_file_path
        self.config = ConfigParser.ConfigParser()
        self.config.read(self.configure_file_path)

    def get(self, section, key):
        try:
            result = self.config.get(section, key)
        except ConfigParser.NoSectionError:
            result = ''
        return result


def running_command(cmd):
    stream = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    stream.wait()
    res = stream.stdout.read().splitlines()
    return res


class Instance(object):
    """
    : Base on / port
    """
    def __init__(self, user, passwd, port, socket, datadir):
        self.user = user
        self.passwd = passwd
        self.port = port
        self.socket = socket
        self.datadir = datadir

    def get_datadir_size(self):
        free = running_command("df -h {0}".format(self.datadir))[1].split()[3]
        used = running_command("du -sh {0}".format(self.datadir))[0].split()[0]
        size_dict = {'Used': used, 'Free': free}
        return size_dict

    def check_mysql_start(self):
        socket = cfg.get('start', 'socket')
        so = '-S'
        if not socket:
            so = ''
            self.socket = ''
        return so, self.socket

    def get_ms_status(self):
        """
        :return: Master/Slave Status
        """
        options = self.check_mysql_start()
        fields = tuple([v.strip() for v in cfg.get('fields', 'status').split(',')])

        cmd = "echo 'show slave status\G;'|mysql -u{0} -p{1} {2} {3}" \
            .format(self.user, self.passwd, options[0], options[1])
        data = running_command(cmd)
        ms_status_dict = {}
        if data is not None:
            results = [line.strip() for line in data if line.strip().startswith(fields)]
            ms_status_dict = dict((line.split(':')[0].strip(), line.split(':')[1].strip()) for line in results)
        return ms_status_dict

    def get_db_size(self):
        """
        use information_schema;
        :return:
        """
        options = self.check_mysql_start()
        get_db_size_sql = "'select table_schema, round(sum(data_length+index_length) / 1024 /1024, 2) \
        from information_schema.tables group by table_schema;'"
        cmd = "mysql -u{0} -p{1} {2} {3} -e {4}|sed 1d"\
            .format(self.user, self.passwd, options[0], options[1], get_db_size_sql)
        db_size_response = running_command(cmd)
        db_size_dict = dict((i.split('\t')[0], i.split('\t')[1]) for i in db_size_response)
        return db_size_dict

    def get_table_size(self):
        db = self.get_db_size()
        options = self.check_mysql_start()
        db_table = []
        for dbname, dbsize in db.items():
            cmd = """mysql -u{0} -p{1} {2} {3} -e \
                "select table_name, round(((data_length+index_length) / 1024 / 1024), 2)\
                from information_schema.tables where table_schema='{4}';"|sed 1d"""\
                .format(self.user, self.passwd, options[0], options[1], dbname)
            table_size_response = running_command(cmd)
            # db_table_lst = []
            db_table_dict = {}
            table_info = dict((i.split('\t')[0], i.split('\t')[1]) for i in table_size_response)
            db_table_dict['db_name'] = dbname
            db_table_dict['db_size'] = dbsize
            db_table_dict['table_info'] = table_info
            db_table.append(db_table_dict)
        return db_table


class DBInfo(object):
    def __init__(self, db_runner, host='localhost'):
        self.db_runner = db_runner
        self.host = host

    @staticmethod
    def get_mem():
        meminfo = {}
        with open('/proc/meminfo') as f:
            for line in f:
                if line.startswith(('MemTotal', 'MemFree')):
                    meminfo[line.split(':')[0]] = line.split(':')[1].strip()
        return meminfo

    def get_db_ms_status(self, port):
        pass

    def get_db_status(self, db_type='mysql'):
        if self.db_runner:
            cmd = "ps aux|grep {0}|grep -v grep|grep -v root".format(db_type)
        else:
            cmd = "ps aux|grep {0}|grep -v grep".format(db_type)
        data = running_command(cmd)
        instances = []
        for line in data:
            response_json = {}
            # if not mysql, change later
            for i in line.split("--"):
                if i.startswith(('datadir', 'user', 'socket', 'port')):
                    response_json[i.split('=')[0]] = i.split('=')[1]
            instances.append(response_json)
        return instances

    @staticmethod
    def running_ifconfig():
        p = subprocess.Popen("ifconfig", stdout=subprocess.PIPE, shell=True)
        return p.communicate()[0]

    def get_ip(self):
        data = self.running_ifconfig()
        info = (i for i in data.split('\n\n') if i and not i.startswith('lo'))
        ip_lst = []
        iface = re.compile(r'(eth[\d:]*|wlan[\d:]*)')
        ipaddr = re.compile(
            r'(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[0-9]{1,2})(\.(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[0-9]{1,2})){3}')
        macaddr = re.compile(r'[A-F0-9a-f:]{17}')
        for i in info:
            ip_dict = {}
            if macaddr.search(i):
                mac = macaddr.search(i).group()
                ip_dict["macaddr"] = mac
            if iface.search(i):
                adt = iface.match(i).group()
                ip_dict["interface"] = adt
            if ipaddr.search(i):
                ip = ipaddr.search(i).group()
                ip_dict["ipaddr"] = ip
            else:
                ip_dict["ipaddr"] = None
            ip_lst.append(ip_dict)
        return ip_lst


class Ins(DBInfo):
    def __init__(self, *args, **kwargs):
        super(Ins, self).__init__(*args, **kwargs)


class Tables(object):
    pass


def main():
    # get configure args
    runner = cfg.get('mysql_runner', 'user')
    # sock = cfg.get('start', 'socket')
    db_user = cfg.get('mysql_user', 'user')
    db_passwd = cfg.get('mysql_user', 'password')

    # get port sock
    dbinfo = DBInfo(runner)
    instances_lst = []
    for item in dbinfo.get_db_status():
        ins = Instance(db_user, db_passwd, item['port'], item['socket'], item['datadir'])
        db_dict = {
            "port": item["port"],
            "db": ins.get_table_size(),
            "datadir_size": ins.get_datadir_size()["Used"],
            "datadir_free": ins.get_datadir_size()["Free"],
            "user": db_user,
            "ms_status": ins.get_ms_status(),
            "info": ""
        }
        if item["port"].startswith("43"):
            db_dict["info"] = "backup"
        instances_lst.append(db_dict)

        # response output
        server_response_dict = {
            "ip": dbinfo.get_ip(),
            "instances": instances_lst
        }

        # POST api
        post_url = "http://10.200.70.192:8888/p00/api/data/"

        try:
            req = urllib2.Request(post_url)
            req.add_header('Content-Type', 'application/json')
            req.add_header('X-CSRFToken', 'client')
            response = urllib2.urlopen(req, json.dumps(server_response_dict))
            print response.read()
        except urllib2.HTTPError, error:
            print "ERROR: ", error.read()

if __name__ == '__main__':
    # # Get CSRF token first
    # client = requests.session() if with lib
    # client.get(URL)  # sets cookie
    # csrftoken = client.cookies['csrf']
    # login_data = dict(headers=headers, csrfmiddlewaretoken=csrftoken, next='/')
    # r = client.post(URL, data=login_data, headers=dict(Referer=URL))
    #
    # hostdetail/?ip=10.203.4.20  获取服务器资产编号
    # {"status": "\u4f7f\u7528\u4e2d",
    # "ip": "10.203.4.20",
    # "hostname": "shwgq-t-mysql-4-10.osd-sql2-s.lin.idc.pplive.cn",
    # "asset_no": "JA03374D1201",
    # "ywlb": "osd-sql2/"}
    cfg = Config('configure')
    main()
