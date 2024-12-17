#!/usr/bin/env python

import argparse
from getpass import getuser
from subprocess import run

parser = argparse.ArgumentParser(prog='Camera-Config.py', description='This code lets you easily modify camera parameters previous to the execution of inference models', epilog='')

# Arguments related to camera parameters
parser.add_argument('-c','--contrast',default=1)
parser.add_argument('-b','--brightness',default=0)
parser.add_argument('-s','--saturation',default=1)
parser.add_argument('-wb','--wbmode',default=1)
parser.add_argument('-et','--exposuretimerange',default='null')
parser.add_argument('-gr','--gainrange',default='null')
parser.add_argument('-igr','--ispdigitalgainrange',default='null')
parser.add_argument('-ec','--exposurecompensation',default=0)
parser.add_argument('--aelock',action='store_true',default=False)
parser.add_argument('--awblock',action='store_true',default=False)

# Arguments related to camera output
parser.add_argument('--width',default=1296)
parser.add_argument('--height',default=730)
parser.add_argument('--framerate',default=30)

# Argument RESET
parser.add_argument('--RESET',action='store_true',default=False)

if __name__ == '__main__':

    args = parser.parse_args()
    path = '/home/' + getuser() + '/jetson-inference/utils/camera/'
    file_path = path + 'gstCamera.cpp'
    
    try:
        old = open(path + 'gstCamera.cpp.old','x')
        command = 'cp ' + file_path + ' ' + path + 'gstCamera.cpp.old'
        print('Creating savefile with command "' + command + '"')
        #run(command, shell=True, executable="/bin/bash")
    except:
        print('Savefile already exists. Avoiding overwrite...')
        
    if args.RESET:
        print('RESET recieved...')
        print('Replacing camera control file with savefile...')
        command = 'cp ' + path + 'gstCamera.cpp.old' + ' ' + file_path
        run(command, shell=True, executable="/bin/bash")
        print('File replaced. Exiting now...')
        exit(0)
       
    with open(file_path,'r') as f:
        w = open(path + 'tmp.cpp','a')
        for i, line in enumerate(f):
            if i == 160: # or i == 144:
                # print(line)
                w.write('		ss << "nvarguscamerasrc sensor-id=" << mOptions.resource.port << " saturation=' + str(args.saturation) + ' wbmode=' + str(args.wbmode) + ' exposuretimerange=' + str(args.exposuretimerange) + ' gainrange=' + str(args.gainrange) + ' ispdigitalgainrange=' + str(args.ispdigitalgainrange) + ' exposurecompensation=' + str(args.exposurecompensation) + ' aelock=' + str(args.aelock) + ' awblock=' + str(args.awblock) + ' ! video/x-raw(memory:NVMM), width=' + str(args.width) + ', height=' + str(args.height) + ', framerate=' + str(args.framerate) + '/1, format=(string)NV12 ! nvvidconv ! videobalance contrast=' + str(args.contrast) + ' brightness=' + str(args.brightness) + ' ! nvvidconv flip-method=" << mOptions.flipMethod << " ! ";\n')

            else:
                w.write(line)
                
    print('Replacing camera config file with new config')
    command = 'mv ' + path + 'tmp.cpp ' + file_path
    run(command, shell=True, executable="/bin/bash")
    # run(['mv','tmp.cpp','gstCamera.cpp'], shell=False, cwd='/home/' + getuser() + '/jetson-inference/utils/camera')
    
    command = 'cmake -B /home/' + getuser() + '/jetson-inference/build -S /home/' + getuser() + '/jetson-inference'
    run(command, shell=True, executable="/bin/bash")
    # run(['cmake','..'], shell=False, cwd='/home/' + getuser() + '/jetson-inference/build')