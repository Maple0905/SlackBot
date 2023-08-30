import os
import time

now = time.time()
path = os.getcwd() + '/file.txt'
file = open(path, 'a')
file.write(str(now))
file.close()
