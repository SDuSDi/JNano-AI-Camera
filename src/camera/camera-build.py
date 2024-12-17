#!/usr/bin/env python

from subprocess import run
from getpass import getuser

build_path = '/home/' + getuser() + '/jetson-inference/build'

print('Building repository to apply changes for inference use')
run(['make'],shell=False,cwd=build_path)
run(['sudo','make','install'],shell=False,cwd=build_path)


