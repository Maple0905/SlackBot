import os
import time

t = time.localtime()
current_time = time.strftime("%Y-%m-%d %H:%M:%S", t)
path = '/var/www/SlackBot/uploads/file.txt'
print(path)
file = open(path, 'a')
file.write(current_time + '\n')
file.close()
