import logging

def main():
    logging.basicConfig(filename='test.log', level=logging.DEBUG, format='%(asctime)s, %(levelname)s, %(message)s')
    logging.info('Started')
    myresult = 23 + 897
    logging.debug('Holy cow, theres a real problemm here...')
    logging.warning('%s before you %s', 'Look', 'leap')
    logging.info('Finished')

if __name__ == '__main__':
    main()
 