import logging

logging.basicConfig(filename='instrument.log', level=logging.DEBUG)
logging.warning('%s before you %s', 'Look', 'leap!')
logging.info('Finished')
