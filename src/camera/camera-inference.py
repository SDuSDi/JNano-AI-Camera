#!/usr/bin/env python

import argparse
from getpass import getuser
from subprocess import run

work_dir = '/home/' + getuser() + '/jetson-inference/build/aarch64/bin'

parser = argparse.ArgumentParser(prog='Camera-Inference.py', description='This code lets you easily execute inference models', epilog='')

# Arguments for all inference
parser.add_argument('job')
parser.add_argument('-m','--model')

# Arguments for detection
parser.add_argument('--overlay',default='box,labels,conf')
parser.add_argument('--alpha',default=120)
parser.add_argument('--threshold',default=0.5)

# Arguments for segmentation
parser.add_argument('--visualize',default='overlay')
#parser.add_argument('--alpha',default=120)
parser.add_argument('--filtermode',default='linear')

if __name__ == '__main__':

    args = parser.parse_args()
    if args.job == 'classification':
        if args.model == None or args.model == 'None':
            args.model = 'resnet-50'
        run(['./imagenet','csi://0','--network='+str(args.model)],shell=False,cwd=work_dir)
        
    if args.job == 'detection':
        if args.model == None or args.model == 'None':
            args.model = 'ssd-mobilenet-v2'
        run(['./detectnet','csi://0','--network='+str(args.model),'--overlay='+str(args.overlay),'--alpha='+str(args.alpha),'--threshold='+str(args.threshold)],shell=False,cwd=work_dir)
        
    if args.job == 'segmentation':
        if args.model == None or args.model == 'None':
            print('Segmentation task has no default network. Please select one.')
            exit(0)
        run(['./segnet','csi://0','--network='+str(args.model),'--visualize='+str(args.visualize),'--alpha='+str(args.alpha),'--filter-mode='+str(args.filtermode)],shell=False,cwd=work_dir)

    else:
        print("Sorry, task not recognized. Please check that task is one of the following: ['classification', 'detection', 'segmentation']")

