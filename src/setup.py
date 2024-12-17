#!/usr/bin/python

import os
from PIL import Image
import zipfile
from getpass import getuser
from shutil import move, rmtree

def check_path(folder_path):
    if not os.path.exists(folder_path):
        print(f"Nested folders '{folder_path}' don't exist.")
        return False
    else:
        print(f"Nested folders '{folder_path}' already exist.")
        return True

def unpack_data(data_path):

    previous_train = check_path(os.path.join(data_path,'train'))
    previous_val = check_path(os.path.join(data_path,'val'))

    if previous_train:

        rmtree(os.path.join(data_path,'train'))
        print('Train folder removed for clean extraction')

    if previous_val:

        rmtree(os.path.join(data_path,'val'))
        print('Validation folder removed for clean extraction')

    train_path = '/home/'+getuser()+'/workspace/ImageNet1k'
    val_path = '/home/'+getuser()+'/workspace/Small-ImageNet1k'

    with zipfile.ZipFile(os.path.join(train_path,'imagenet1k.zip'), 'r') as zip_ref:
        zip_ref.extractall(data_path)
        zip_ref.close()

    with zipfile.ZipFile(os.path.join(val_path,'smallimagenet1k.zip'), 'r') as zip_ref:
        zip_ref.extractall(data_path)
        zip_ref.close()

    os.rename('/home/'+getuser()+'/workspace/src/imagenet_1k/imagenet1k', '/home/'+getuser()+'/workspace/src/imagenet_1k/train')

    move('/home/'+getuser()+'/workspace/src/imagenet_1k/Small-ImageNet-Validation-Dataset-1000-Classes-main/ILSVRC2012_img_val_subset', '/home/'+getuser()+'/workspace/src/imagenet_1k/ILSVRC2012_img_val_subset')
    os.rename('/home/'+getuser()+'/workspace/src/imagenet_1k/ILSVRC2012_img_val_subset', '/home/'+getuser()+'/workspace/src/imagenet_1k/val')
    rmtree('/home/'+getuser()+'/workspace/src/imagenet_1k/Small-ImageNet-Validation-Dataset-1000-Classes-main')

def prune_data(data_path):

    unpack_data(data_path)

    for section in os.listdir(data_path):

        full_section = os.path.join(data_path, section)

        if section == 'labels.txt':
            continue

        for folder in os.listdir(full_section):

            images = 0
            if not folder == ('00'+(folder[:3]))[-3:]:
                pwd = os.getcwd()
                os.rename(os.path.join(full_section,folder), os.path.join(full_section,('00'+(folder[:3]))[-3:]))
                folder = ('00'+(folder[:3]))[-3:]
            full_dir = os.path.join(full_section, folder)

            for file in os.listdir(full_dir):

                img = Image.open(os.path.join(full_dir,file)).convert('RGB')

                if img is not None and images<1:

                    images+=1

                else:

                    os.remove(os.path.join(full_dir,file))

if __name__ == '__main__':
    prune_data('./imagenet_1k')