import json

class PluginManager(object):
    """Class for managing the plugin.json file."""

    def __init__(self, file_path):
        self.file_path = file_path

    def get_plugins(self):
        """Reads plugins.json and returns a dict containing all the plugins."""
        with open(self.file_path) as plugins_file:
            data = json.load(plugins_file)
        return data

    def get_output_plugins(self):
        """Reads plugins.json and returns a dict containing the output plugins."""
        with open(self.file_path) as plugins_file:
            data = json.load(plugins_file)
        return data['output']

    def get_input_plugins(self):
        """Reads plugins.json and returns a dict containing the input plugins."""
        with open(self.file_path) as plugins_file:
            data = json.load(plugins_file)
        return data['input']

    def add_output_plugin(self, app_name, config):
        """Adds an output plugin to plugins.json."""
        plugins = self.get_plugins()
        plugins['output'][app_name] = config
        with open(self.file_path, 'w') as plugins_file:
            json.dump(plugins, plugins_file, indent=4)

    def add_input_plugin(self, app_name, config):
        """Adds an input plugin to plugins.json."""
        plugins = self.get_plugins()
        plugins['input'][app_name] = config
        with open(self.file_path, 'w') as plugins_file:
            json.dump(plugins, plugins_file, indent=4)

    def remove_input_plugin(self, app_name):
        """Removes an input plugin from plugins.json."""
        plugins = self.get_plugins()
        if app_name in plugins['input']:
            plugins['input'].pop(app_name)
        with open(self.file_path, 'w') as plugins_file:
            json.dump(plugins, plugins_file, indent=4)
