# !/usr/bin/python3
# pylint: disable=c0111,c0325,e0401

import subprocess
import json
import os
import shutil

from charmhelpers.core import unitdata
from charms.reactive import when, when_not, set_state, remove_state
from charmhelpers.fetch.archiveurl import ArchiveUrlFetchHandler
from charmhelpers.core.hookenv import open_port, close_port, status_set
from charmhelpers.core.host import service_stop, service_restart, service_running, service_available, mkdir
from charmhelpers.core.templating import render

from plugin_manager import PluginManager


DB = unitdata.kv()
CONFIG_FILE = "/etc/telegraf/telegraf.conf"
PLUGINS_FILE = "/opt/telegraf/plugins.json"


@when_not('layer-telegraf.installed')
def install_layer_telegraf():
    """Installs the Telegraf software."""
    # Check if another Telegraf subordinate is already installed.
    if is_telegraf_installed():
        print("Telegraf already installed.")
        set_state('layer-telegraf.installed')
    else:
        print("Telegraf is not installed. Will install it...")
        status_set('maintenance', 'Installing Telegraf...')
        fetcher = ArchiveUrlFetchHandler()
        if not os.path.isdir('/opt/telegraf'):
            mkdir('/opt/telegraf')
        fetcher.download('https://dl.influxdata.com/telegraf/releases/telegraf_1.4.5-1_amd64.deb',
                         '/opt/telegraf/telegraf_1.4.5-1_amd64.deb')
        subprocess.check_call(['dpkg', '--force-confdef', '-i',
                               '/opt/telegraf/telegraf_1.4.5-1_amd64.deb'])
        shutil.copyfile('files/plugins.json', '/opt/telegraf/plugins.json')
        set_state('layer-telegraf.installed')
        set_state('layer-telegraf.needs_restart')


@when('layer-telegraf.installed')
@when('layer-telegraf.needs_restart')
def start_layer_telegraf():
    service_restart('telegraf')
    if service_running('telegraf'):
        status_set('active', 'Telegraf is running.')
        remove_state('layer-telegraf.needs_restart')
    else:
        status_set('blocked', 'Telegraf failed.')


@when('stop')
def stop_and_remove_telegraf():
    """Removes the Telegraf service and all its files and directories."""
    print("Removing Telegraf...")
    subprocess.check_call(['rm', '/opt/telegraf_1.4.5-1_amd64.deb'])
    subprocess.check_call(['dpkg', '-P', 'telegraf'])


###############################################################################
#                            OUTPUT RELATIONS                                 #
###############################################################################


@when('influxdb-output.available')
@when_not('plugins.influxdb-output.configured')
def configure_influxdb_output(influxdb):
    urls = ['http://' + influxdb.hostname() + ':' + influxdb.port()]
    context = {'urls': urls,
               'user': influxdb.user(),
               'password': influxdb.password()}
    # Render influx config
    influxdb_config = get_config(context, 'output-influxdb.conf')
    # Add to key value store
    add_output_plugin('influxdb', influxdb_config)
    # Render telegraf.conf
    render_config()
    # Restart
    set_state('layer-telegraf.needs_restart')
    set_state('plugins.influxdb-output.configured')


###############################################################################
#                             INPUT RELATIONS                                 #
###############################################################################


@when('mongodb-input.available')
@when_not('plugins.mongodb-input.configured')
def configure_mongodb_input(mongodb):
    servers = ['mongodb://' + mongodb.hostname() + ':' + mongodb.port()]
    context = {'servers': servers}
    # Render mongodb config
    mongodb_config = get_config(context, 'input-mongodb.conf')
    # Add to key value store
    add_input_plugin('mongodb', mongodb_config)
    # Render telegraf.conf
    render_config()
    # Restart
    set_state('layer-telegraf.needs_restart')
    set_state('plugins.mongodb-input.configured')


@when('mysql-input.available')
@when_not('plugins.mysql-input.configured')
def configure_mysql_input(mysql):
    servers = [mysql.user() + ':' + mysql.password() + "@tcp(" + mysql.host() + ':' + str(mysql.port()) + ')/?tls=false']
    context = {'servers': servers}
    # Render mysql config
    mysql_config = get_config(context, 'input/mysql.conf')
    # Add to key value store
    add_input_plugin('mysql', mysql_config)
    # Render telegraf.conf
    render_config()
    # Restart
    set_state('layer-telegraf.needs_restart')
    set_state('plugins.mysql-input.configured')


###############################################################################
#                                 HELPERS                                     #
###############################################################################


def get_config(context, filename):
    content = render(source=filename, target=None, context=context)
    return content


# def add_output_plugin(plugin_name, plugin_config):
#     """Add output plugin config string to key-value store."""
#     output_plugins = DB.get('output_plugins')
#     if output_plugins is not None:
#         output_plugins[plugin_name] = plugin_config
#     else:
#         output_plugins = {plugin_name: plugin_config}
#     DB.set('output_plugins', output_plugins)

def add_output_plugin(plugin_name, plugin_config):
    """Adds an output plugin to plugins.json."""
    plugin_manager = PluginManager(PLUGINS_FILE)
    plugin_manager.add_output_plugin(plugin_name, plugin_config)


# def add_input_plugin(plugin_name, plugin_config):
#     """Add input plugin config string to key-value store."""
#     input_plugins = DB.get('input_plugins')
#     if input_plugins is not None:
#         input_plugins[plugin_name] = plugin_config
#     else:
#         input_plugins = {plugin_name: plugin_config}
#     DB.set('input_plugins', input_plugins)


def add_input_plugin(plugin_name, plugin_config):
    """Adds an input plugin to plugins.json."""
    plugin_manager = PluginManager(PLUGINS_FILE)
    plugin_manager.add_input_plugin(plugin_name, plugin_config)


# def get_output_plugins_config():
#     """Append all configs of the output plugins."""
#     config = ""
#     output_plugins = DB.get('output_plugins')
#     if output_plugins is not None:
#         for app, conf in output_plugins.items():
#             config += conf
#     return config

def get_output_plugins_config():
    """Append all configs of the output plugins."""
    config = ""
    plugin_manager = PluginManager(PLUGINS_FILE)
    output_plugins = plugin_manager.get_output_plugins()
    for app, conf in output_plugins.items():
        config += conf
    return config


# def get_input_plugins_config():
#     """Append all configs of the input plugins."""
#     config = ""
#     input_plugins = DB.get('input_plugins')
#     if input_plugins is not None:
#         for app, conf in input_plugins.items():
#             config += conf
#     return config

def get_input_plugins_config():
    """Append all configs of the input plugins."""
    config = ""
    plugin_manager = PluginManager(PLUGINS_FILE)
    input_plugins = plugin_manager.get_input_plugins()
    for app, conf in input_plugins.items():
        config += conf
    return config


def render_config():
    context = {'output_plugins': get_output_plugins_config(),
               'input_plugins': get_input_plugins_config()}
    render(source='telegraf.conf', target='/etc/telegraf/telegraf.conf', context=context)


def is_telegraf_installed():
    """Checks if Telegraf is already installed on machine."""
    try:
        subprocess.check_output(['dpkg', '-l', 'telegraf'])
    except subprocess.CalledProcessError as e:
        return False
    else:
        return True
