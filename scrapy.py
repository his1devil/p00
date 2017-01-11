#! /usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import subprocess
import ConfigParser
try:
    import simplejson as json
except ImportError:
    import json
from collections import OrderedDict


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


class DBInfo(object):
    def __init__(self, db_runner, socket, host='localhost'):
        self.db_runner = db_runner
        self.socket = socket
        self.host = host

    @staticmethod
    def get_mem():
        meminfo = OrderedDict()
        with open('/proc/meminfo') as f:
            for line in f:
                if line.startswith(('MemTotal', 'MemFree')):
                    meminfo[line.split(':')[0]] = line.split(':')[1].strip()
        return meminfo

    def get_db_status(self, db_type='mysql'):
        if self.db_runner:
            cmd = "ps aux|grep {0}|grep -v grep|grep -v root".format(db_type)
        else:
            cmd = "ps aux|grep {0}|grep -v grep".format(db_type)
        data = running_command(cmd)
        return data

    # def get_ms_status(self, cmd, fields):
    #     if data:
    #         results = [line.strip() for line in data if lines.strip().startswith(fields)]
    #     else:
    #         results = ''
    #     return results


if __name__ == '__main__':
    cfg = Config('configure')

    # 数据库 运行用户 / 状态
    runner = cfg.get('mysql_runner', 'user')
    sock = cfg.get('start', 'socket')
    results = DBInfo(runner, sock)
    print results.get_db_status()

    # 数据库M/S状态
    db_status = tuple([v.strip() for v in cfg.get('fields', 'status').split(',')])
    # command = "echo 'show slave status\G;'|mysql -u{0} -p{1} {2} {3}"
    #               .format('root', '123', '-S', '/tmp/mysql3307.sock')
    # get_ms_status(command, condition)
    # 数据库连接方式
    # sock = cfg.get('start', 'socket')
    # if sock:
    #     connection = "echo 'show slave status\G;'|mysql -u{0} -p{1} -S {2}".format('root', '123', '/tmp/mysql3307.sock')
    #
    # # 获取服务器内存状态
    # server = DBInfo()
    # print "Mem:", server.get_mem()
    #
    # # 数据库运行用户
    #
    # df = subprocess.Popen(["df", "filename"], stdout=subprocess.PIPE)
    # output = df.communicate()[0]
    # device, size, used, available, percent, mountpoint = \
    #     output.split("\n")[1].split()






