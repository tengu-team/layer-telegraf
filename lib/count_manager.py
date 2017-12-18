import json

class CountManager(object):
    """Class for managing the number of Telegraf instances on a machine."""

    def __init__(self, file_path):
        self.file_path = file_path

    def get_json(self):
        with open(self.file_path) as counter_file:
            data = json.load(counter_file)
            return data

    def get_count(self):
        with open(self.file_path) as counter_file:
            data = json.load(counter_file)
            return data['count']

    def increment(self):
        data = self.get_json()
        data['count'] += 1
        with open(self.file_path, 'w') as counter_file:
            json.dump(data, counter_file, indent=4)

    def decrement(self):
        data = self.get_json()
        data['count'] -= 1
        with open(self.file_path, 'w') as counter_file:
            json.dump(data, counter_file, indent=4)
