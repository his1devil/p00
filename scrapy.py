#! /usr/bin/env python
# -*- coding: utf-8 -*-
import subprocess
import ConfigParser
try:
    import simplejson as json
except ImportError:
    import json
# from collections import OrderedDict new in 2.7 ;(


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
        used = running_command("du -sh {0}".format(self.datadir)).split()[0]
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
        # 所有数据大小
        select concat(round(sum(DATA_LENGTH/1024/1024), 2), 'MB') as data from TABLES;
        # 指定数据库实例大小
        select concat(round(sum(DATA_LENGTH/1024/1024), 2), 'MB') as data from TABLES where table_schema='dbname';
        # 指定数据库表的大小
        select concat(round(sum(DATA_LENGTH/1024/1024), 2), 'MB') \
        as data from TABLES where table_schema='dbname' and table_name='tablename';
        # table 大小
        select table_name round round(((data_length + index_length) / 1024 / 1024), 2) \
        from information_schema.TABLES where table_schema = 'db_name' and table_name='table_name';
        # 某数据库下所有table大小信息
        SELECT table_schema, table_name, round(((data_length+index_length) / 1024 / 1024), 2)\
          FROM information_schema.TABLES WHERE table_schema='db_name';
        # 数据库实例中各数据库的大小
        select table_schema, round(sum(data_length + index_length) / 1024 / 1024, 1) \
        from information_schema.tables group by table_schema;
        :return:
        """
        options = self.check_mysql_start()
        get_db_size_sql = "'select table_schema, round(sum(data_length+index_length) / 1024 /1024, 2) \
        from information_schema.tables group by table_schema;'"
        cmd = "mysql -u{0} -p{1} {2} {3} -e {4}|sed 1d"\
            .format(self.user, self.passwd, options[0], options[1], get_db_size_sql)
        db_size_response = running_command(cmd)
        db_size_dict = dict((item.split('\t')[0], item.split('\t')[1]) for item in db_size_response)
        return db_size_dict

    def get_table_size(self):
        db = self.get_db_size()
        options = self.check_mysql_start()
        db_table_lst = []
        for dbname, dbsize in db.items():
            cmd = """mysql -u{0} -p{1} {2} {3} -e \
                "select table_name, round(((data_length+index_length) / 1024 / 1024), 2)\
                from information_schema.tables where table_schema='{4}';"|sed 1d"""\
                .format(self.user, self.passwd, options[0], options[1], dbname)
            table_size_response = running_command(cmd)
            table_size_dict = dict((item.split('\t')[0], item.split('\t')[1]) for item in table_size_response)
            db_table_lst.append(table_size_dict)
        return db_table_lst


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


class Ins(DBInfo):
    def __init__(self, *args, **kwargs):
        super(Ins, self).__init__(*args, **kwargs)


class Tables(object):
    pass


if __name__ == '__main__':
    cfg = Config('configure')

    # Get configure kw
    runner = cfg.get('mysql_runner', 'user')
    sock = cfg.get('start', 'socket')
    db_user = cfg.get('mysql_user', 'user')
    db_passwd = cfg.get('mysql_user', 'password')

    # Get port sock info
    dbinfo = DBInfo(runner)
    dbs_json = dbinfo.get_db_status()

    # 数据库实例具体信息
    ins = Instance('root', '123', '3307', '/tmp/mysql3308.sock', '/usr/local/mysql/data/')
    print ins.get_table_size()
    #
    # 获取服务器内存状态
    # server = DBInfo()
    # print "Mem:", server.get_mem()
