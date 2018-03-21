# !/usr/bin/python3
# pylint: disable=c0111,c0325,e0401

import subprocess
import os
import shutil
import socket
import time

from charms.reactive import hook, when, when_not, set_flag, clear_flag
from charmhelpers.fetch.archiveurl import ArchiveUrlFetchHandler
from charmhelpers.core import unitdata
from charmhelpers.core.hookenv import status_set, remote_unit
from charmhelpers.core.host import service_restart, service_running, mkdir
from charmhelpers.core.templating import render

from plugin_manager import PluginManager
from count_manager import CountManager


DB = unitdata.kv()
CONFIG_FILE = "/etc/telegraf/telegraf.conf"
PLUGINS_FILE = "/opt/telegraf/plugins.json"
COUNT_FILE = "/opt/telegraf/telegraf.json"


@when_not('layer-telegraf.installed')
def install_layer_telegraf():
    """Installs the Telegraf software if it is not already installed."""
    if is_telegraf_installed():
        increment_number_telegrafs()
    else:
        status_set('maintenance', 'Installing Telegraf...')
        fetcher = ArchiveUrlFetchHandler()
        if not os.path.isdir('/opt/telegraf'):
            mkdir('/opt/telegraf')
        fetcher.download('https://dl.influxdata.com/telegraf/releases/telegraf_1.4.5-1_amd64.deb',
                         '/opt/telegraf/telegraf_1.4.5-1_amd64.deb')
        subprocess.check_call(['dpkg', '--force-confdef', '-i',
                               '/opt/telegraf/telegraf_1.4.5-1_amd64.deb'])
        shutil.copyfile('files/plugins.json', '/opt/telegraf/plugins.json')
        shutil.copyfile('files/telegraf.json', '/opt/telegraf/telegraf.json')
        increment_number_telegrafs()

    set_flag('layer-telegraf.installed')


@when('layer-telegraf.installed')
@when('layer-telegraf.needs_restart')
def start_layer_telegraf():
    time.sleep(5)
    service_restart('telegraf')
    if service_running('telegraf'):
        status_set('active', 'Telegraf is running.')
        clear_flag('layer-telegraf.needs_restart')
    else:
        status_set('blocked', 'Telegraf failed.')


@when('layer-telegraf.check_need_remove')
def check_removal():
    count_manager = CountManager(COUNT_FILE)
    number_of_telegrafs = count_manager.get_count()
    if number_of_telegrafs == 0:
        set_flag('layer-telegraf.remove')
    clear_flag('layer-telegraf.check_need_remove')


@when('layer-telegraf.remove')
def remove_telegraf():
    """Removes the Telegraf service and all its files and directories."""
    if os.path.isdir('/opt/telegraf'):
        subprocess.check_call(['rm', '-r', '/opt/telegraf'])
        subprocess.check_call(['dpkg', '-P', 'telegraf'])


@hook('host-system-relation-joined')
def host_system_joined(host):
    """Executes when a juju-info relation is made with a service."""
    name_service = remote_unit().replace('/', '-')
    add_tag(name_service)
    render_config()
    set_flag('layer-telegraf.needs_restart')


@hook('host-system-relation-departed')
def host_system_departed(host):
    name_service = remote_unit().replace('/', '-')
    remove_tag(name_service)
    render_config()
    decrement_number_telegrafs()
    set_flag('layer-telegraf.check_need_remove')


###############################################################################
#                            OUTPUT RELATIONS                                 #
###############################################################################


@when('layer-telegraf.installed')
@when_not('plugins.influxdb-output.configured')
def no_influx_blocked():
    """A relation with InfluxDB is required."""
    status_set('blocked', 'Please create a relation with InfluxDB.')


@when('influxdb-output.available')
@when_not('plugins.influxdb-output.configured')
def configure_influxdb_output(influxdb):
    urls = ['http://' + influxdb.hostname() + ':' + influxdb.port()]
    context = {'urls': urls,
               'user': influxdb.user(),
               'password': influxdb.password()}
    influxdb_config = get_config(context, 'output/influxdb.conf')
    add_output_plugin('influxdb', influxdb_config)
    render_config()
    set_flag('layer-telegraf.needs_restart')
    set_flag('plugins.influxdb-output.configured')


@when('opentsdb-output.available')
@when_not('plugins.opentsdb-output.configured')
def configure_opentsdb_output(opentsdb):
    context = {'host': opentsdb.host(),
               'port': opentsdb.port()}
    opentsdb_config = get_config(context, 'output/opentsdb.conf')
    add_output_plugin('opentsdb', opentsdb_config)
    render_config()
    set_flag('layer-telegraf.needs_restart')
    set_flag('plugins.opentsdb-output.configured')


###############################################################################
#                             INPUT RELATIONS                                 #
###############################################################################


@when('mongodb-input.available')
@when_not('plugins.mongodb-input.configured')
def configure_mongodb_input(mongodb):
    servers = ['mongodb://{}:{}'.format(mongodb.hostname(), mongodb.port())]
    context = {'servers': servers}
    mongodb_config = get_config(context, 'input/mongodb.conf')
    add_input_plugin('mongodb', mongodb_config)
    render_config()
    set_flag('layer-telegraf.needs_restart')
    set_flag('plugins.mongodb-input.configured')


@when('plugins.mongodb-input.configured')
@when_not('mongodb-input.connected')
def unconfigure_mongodb_input():
    remove_input_plugin('mongodb')
    render_config()
    decrement_number_telegrafs()
    clear_flag('plugins.mongodb-input.configured')
    # Must be manually removed because mongodb interface doesn't do it.
    clear_flag('mongodb-input.available')
    set_flag('layer-telegraf.check_need_remove')


@when('nginx-input.available')
@when_not('plugins.nginx-input.configured')
def configure_nginx_input(nginx):
    # TODO: Make dynamic! Maybe create own interface?
    # urls = [nginx.status_url]
    urls = ["http://localhost/nginx_status"]
    context = {'urls': urls}
    nginx_config = get_config(context, 'input/nginx.conf')
    add_input_plugin('nginx', nginx_config)
    render_config()
    set_flag('layer-telegraf.needs_restart')
    set_flag('plugins.nginx-input.configured')


@when('plugins.nginx-input.configured')
@when_not('nginx-input.available')
def unconfigure_nginx_input():
    remove_input_plugin('nginx')
    render_config()
    decrement_number_telegrafs()
    clear_flag('plugins.nginx-input.configured')
    # Must be manually removed because mongodb interface doesn't do it.
    clear_flag('nginx-input.available')
    set_flag('layer-telegraf.check_need_remove')


@when('arangodb-input.available')
@when_not('plugins.arangodb-input.configured')
def configure_arangodb_input(arangodb):
    print('configure arangodb input')
    print(arangodb.host())
    servers = ["http://{}:{}/_admin/statistics".format(arangodb.host(), arangodb.port())]
    print(servers)
    context = {'servers': servers, 'username': arangodb.username(), 'password': arangodb.password()}
    arangodb_config = get_config(context, 'input/http.conf')
    add_input_plugin('arangodb', arangodb_config)
    render_config()
    set_flag('layer-telegraf.needs_restart')
    set_flag('plugins.arangodb-input.configured')


@when('plugins.arangodb-input.configured')
@when_not('arangodb-input.available')
def unconfigure_arangodb_input():
    remove_input_plugin('arangodb')
    render_config()
    decrement_number_telegrafs()
    clear_flag('plugins.arangodb-input.configured')
    clear_flag('arangodb-input.available')
    set_flag('layer-telegraf.check_need_remove')


# TODO:Configure MySQL
# @when('mysql-input.available')
# @when_not('plugins.mysql-input.configured')
# def configure_mysql_input(mysql):
#     servers = [mysql.user() + ':' + mysql.password() + "@tcp(" + mysql.host()
#                + ':' + str(mysql.port()) + ')/?tls=false']
#     context = {'servers': servers}
#     mysql_config = get_config(context, 'input/mysql.conf')
#     add_input_plugin('mysql', mysql_config)
#     render_config()
#     set_flag('layer-telegraf.needs_restart')
#     set_flag('plugins.mysql-input.configured')


# TODO: Unconfigure MySQL


###############################################################################
#                                 HELPERS                                     #
###############################################################################


def get_config(context, filename):
    content = render(source=filename, target=None, context=context)
    return content


def add_tag(app_name):
    plugin_manager = PluginManager(PLUGINS_FILE)
    plugin_manager.add_tag(app_name)


def add_output_plugin(plugin_name, plugin_config):
    plugin_manager = PluginManager(PLUGINS_FILE)
    plugin_manager.add_output_plugin(plugin_name, plugin_config)


def add_input_plugin(plugin_name, plugin_config):
    plugin_manager = PluginManager(PLUGINS_FILE)
    plugin_manager.add_input_plugin(plugin_name, plugin_config)


def remove_tag(app_name):
    plugin_manager = PluginManager(PLUGINS_FILE)
    plugin_manager.remove_tag(app_name)


def remove_input_plugin(plugin_name):
    plugin_manager = PluginManager(PLUGINS_FILE)
    plugin_manager.remove_input_plugin(plugin_name)


def get_tags_config():
    """Returns a list of all the tags (applications)."""
    plugin_manager = PluginManager(PLUGINS_FILE)
    tags = plugin_manager.get_tags()
    tags_config = ""
    for tag in tags:
        line = "    {} = '{}_cpu'\n".format(tag, tag)
        tags_config += line
    return tags_config


def get_output_plugins_config():
    """Append all configs of the output plugins."""
    config = ""
    plugin_manager = PluginManager(PLUGINS_FILE)
    output_plugins = plugin_manager.get_output_plugins()
    for app, conf in output_plugins.items():
        config += conf + "\n\n\n"
    return config


def get_input_plugins_config():
    """Append all configs of the input plugins."""
    config = ""
    plugin_manager = PluginManager(PLUGINS_FILE)
    input_plugins = plugin_manager.get_input_plugins()
    for app, conf in input_plugins.items():
        config += conf + "\n\n\n"
    return config


def render_config():
    context = {'hostname': socket.gethostname(),
               'output_plugins': get_output_plugins_config(),
               'input_plugins': get_input_plugins_config(),
               'tags': get_tags_config()}
    render(source='telegraf.conf',
           target='/etc/telegraf/telegraf.conf',
           context=context)


def is_telegraf_installed():
    """Checks if Telegraf is already installed on machine."""
    return os.path.isdir('/opt/telegraf')


def increment_number_telegrafs():
    count_manager = CountManager(COUNT_FILE)
    count_manager.increment()


def decrement_number_telegrafs():
    count_manager = CountManager(COUNT_FILE)
    count_manager.decrement()
