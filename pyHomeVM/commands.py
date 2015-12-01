import logging
import subprocess
from CONSTANTS import CONSTANTS

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(CONSTANTS['log_file_path'])
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def executeCommand(command):
    '''
    Function that executes a command to shell.
    Allows to waitbetween each command
    Input: command as string
    Ouptut: None
    '''
    logger.debug('Executing: {}'.format(command))
    proc = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    stdout, err = proc.communicate()
    proc.wait()
    return(stdout, err)
