#!/usr/bin/env python

import warnings
warnings.filterwarnings("ignore")

import tensorrt as trt
import pycuda.driver as cuda
import pycuda.autoinit
import argparse
import logging
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
import torchvision
import torchvision.transforms as trf
from torchvision.transforms import Normalize, ToPILImage,Grayscale, Resize, ToTensor
import torchvision.models as models 
import time
from pathlib import Path
from typing import Tuple, List, Union
import time
import os
from PIL import Image
import cv2
import matplotlib.pyplot as plt
import random
import json

# Configure Logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

stream_handler = logging.StreamHandler()
formatter = logging.Formatter(fmt = "%(asctime)s: %(message)s", datefmt= '%Y-%m-%d %H:%M%S')
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

def read_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine', type = str, default= None, help = 'path to save the generated trt file')
    parser.add_argument('--data', type = str, default= None, help = 'path to the fusion dataset')
    parser.add_argument('--save', type = str, default= "Tardal/data/m3fd_chunked/", help = 'save fused dataset')
    parser.add_argument('--fp16', action= "store_true",  help = 'use fp16 precisoin')
    #parser.add_argument('--batch', type = int, default=32, help = 'batch size')
    opt = parser.parse_args()
    return opt

class RunTRT:

    def __init__(self, engine_file: Path, data_type: str = "fp32", batch_size: int = 1,
                 image_shape: Tuple[int, int, int]= (3, 224, 224), img_transforms: torchvision.transforms = None):
        
        self.engine_file = engine_file
        self.data_type = data_type
        self.batch_size = batch_size
        self.image_shape = image_shape
        self.transformations = img_transforms

        self.target_dtype = np.float16 if self.data_type == "fp16" else np.float32
        self.output = np.empty([self.batch_size, self.image_shape[0], self.image_shape[1], self.image_shape[2]], dtype = self.target_dtype)
        
        # allocating device memory
        f = open(self.engine_file, "rb")
        self.runtime = trt.Runtime(trt.Logger(trt.Logger.WARNING)) 

        self.engine = self.runtime.deserialize_cuda_engine(f.read())
        self.context = self.engine.create_execution_context()

        # allocate device memory
        self.d_input = cuda.mem_alloc(1 * np.empty([self.batch_size, self.image_shape[0], self.image_shape[1], self.image_shape[2]], dtype = self.target_dtype).nbytes)
        self.d_output = cuda.mem_alloc(1 * self.output.nbytes)

        self.bindings = [int(self.d_input), int(self.d_output)]

        self.stream = cuda.Stream()
    
    # preprocess the images
    def preprocess_image(self, img):
        norm = Normalize(mean=[0.485], std=[0.229])
        result = norm(torch.from_numpy(img).transpose(0,2).transpose(1,2))
        return np.array(result, dtype=np.float16)
    
    # run inference
    def predict(self, inputs):
        # transfer input data to device
        cuda.memcpy_htod_async(self.d_input, inputs, self.stream)
        # execute model
        self.context.execute_async_v2(self.bindings, self.stream.handle, None)
        # transfer predictions back
        cuda.memcpy_dtoh_async(self.output, self.d_output, self.stream)
        # syncronize threads
        self.stream.synchronize()
        return self.output

    # warmup..
    def warmup(self):
        logger.info("Warming up...")
        WARMUP_EPOCHS = 150
        for _ in range(WARMUP_EPOCHS):
            pred = self.predict((self.optical_batch, self.infrared_batch))
        logger.info("Warmup complete!")

if __name__ == "__main__":

    args = read_args()
    trt_engine_path = "/home/brais/workspace/src/resnet50.trt"

    logger.info("setting fusion pipeline")
    engine_file = trt_engine_path
    data_type = "fp32"
    batch = 1
    image_shape = (3, 224, 224)

    img = Image.open("/home/brais/workspace/src/imagenet_1k/train/024/047_5619.jpg").resize((256,256))
    left = (256 - 224)/2
    top = (256 - 224)/2
    right = (256 + 224)/2
    bottom = (256 + 224)/2
    img = img.crop((left, top, right, bottom))
    img_array = np.array(img)

    trt_runner = RunTRT(engine_file= engine_file, data_type= data_type, batch_size= batch, 
                        image_shape= image_shape, img_transforms= None)

    output = trt_runner.predict(img_array)
    print(output[0])

