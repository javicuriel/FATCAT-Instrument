import configparser
config_file = 'config.ini'
config = configparser.ConfigParser()
config.read(config_file)
for mode in config['MODES']:
    print(config.get('MODES', mode).split(','))

jobs = [section for section in config.sections() if section.startswith('JOB.')]
print(jobs)

print(config['MODULES']["pump"].split(','))
print(eval(config['MODULES']["pump"]))
# for mode in config['Test']:
#     x, y = config.get('Test', mode).split('\n')
#     print(x)
#     print(y)
