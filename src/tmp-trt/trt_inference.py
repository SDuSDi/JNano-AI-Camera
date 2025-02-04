#!/usr/bin/env python

import numpy as np
import pycuda.driver as cuda
import pycuda.autoinit
import tensorrt as trt
import time
import torch
from PIL import Image
import cv2 as cv
import json

#class TensorRTInference:
#    def __init__(self, engine_path):
#        self.logger = trt.Logger(trt.Logger.ERROR)
#        self.runtime = trt.Runtime(self.logger)
#        self.engine = self.load_engine(engine_path)
#        self.context = self.engine.create_execution_context()
#
#        # Allocate buffers
#        self.inputs, self.outputs, self.bindings, self.stream = self.allocate_buffers(self.engine)
#
#    def load_engine(self, engine_path):
#        with open(engine_path, "rb") as f:
#            engine = self.runtime.deserialize_cuda_engine(f.read())
#        return engine
#
#    class HostDeviceMem:
#        def __init__(self, host_mem, device_mem):
#            self.host = host_mem
#            self.device = device_mem
#
#    def allocate_buffers(self, engine):
#        inputs, outputs, bindings = [], [], []
#        stream = cuda.Stream()
#
#        for i in range(engine.num_bindings):
#            tensor_name = engine.get_binding_name(i)
#            size = trt.volume(engine.get_binding_shape(tensor_name))
#            dtype = trt.nptype(engine.get_binding_dtype(tensor_name))
#
#            # Allocate host and device buffers
#            host_mem = cuda.pagelocked_empty(size, dtype)
#            device_mem = cuda.mem_alloc(host_mem.nbytes)
#
#            # Append the device buffer address to device bindings
#            bindings.append(int(device_mem))
#
#            # Append to the appropiate input/output list
#            if engine.binding_is_input(tensor_name):
#                inputs.append(self.HostDeviceMem(host_mem, device_mem))
#            else:
#                outputs.append(self.HostDeviceMem(host_mem, device_mem))
#
#        return inputs, outputs, bindings, stream
#
#    def infer(self, input_data):
#        # Transfer input data to device
#        print(self.inputs[0].host.shape)
#        np.copyto(self.inputs[0].host, input_data.ravel())
#        cuda.memcpy_htod_async(self.inputs[0].device, self.inputs[0].host, self.stream)
#
#        # Set tensor address
#        # for i in range(self.engine.num_bindings):
#        #     self.context.set_tensor_address(self.engine.get_binding_name(i), self.bindings[i])
#
#        # Run inference
#        self.context.execute_async(stream_handle=self.stream.handle)
#
#        # Transfer predictions back
#        cuda.memcpy_dtoh_async(self.outputs[0].host, self.outputs[0].device, self.stream)
#
#        # Synchronize the stream
#        self.stream.synchronize()
#
#        return self.outputs[0].host

class HostDeviceMem:
    def __init__(self, host_mem, device_mem):
        self.host = host_mem
        self.device = device_mem

def allocate_buffers(engine):
    """
    Allocates all buffers required for the specified engine
    """
    inputs = []
    outputs = []
    bindings = []
    # Iterate over binding names in engine
    for binding in engine:
        # Get binding (tensor/buffer) size
        size = trt.volume(engine.get_binding_shape(binding)) * engine.max_batch_size
        # Get binding (tensor/buffer) data type (numpy-equivalent)
        dtype = trt.nptype(engine.get_binding_dtype(binding))
        # Allocate page-locked memory (i.e., pinned memory) buffers
        host_mem = cuda.pagelocked_empty(size, dtype)
        # Allocate linear piece of device memory
        device_mem = cuda.mem_alloc(host_mem.nbytes)
        # Append the device buffer to device bindings
        bindings.append(int(device_mem))
        # Append to inputs/ouputs list@@@@@@@@
        if engine.binding_is_input(binding):
            inputs.append(HostDeviceMem(host_mem, device_mem))
        else:
            outputs.append(HostDeviceMem(host_mem, device_mem))
    # Create a stream (to eventually copy inputs/outputs and run inference)
    stream = cuda.Stream()
    return inputs, outputs, bindings, stream

def infer(context, bindings, inputs, outputs, stream, batch_size=1):
    """
    Infer outputs on the IExecutionContext for the specified inputs
    """
    # Transfer input data to the GPU
    [cuda.memcpy_htod_async(inp.device, inp.host, stream) for inp in inputs]
    # Run inference
    context.execute_async(batch_size=batch_size, bindings=bindings, stream_handle=stream.handle)
    #print(np.array(outputs)[0].host)
    # Transfer predictions back from the GPU
    [cuda.memcpy_dtoh_async(out.host, out.device, stream) for out in np.array(outputs)]
    # Synchronize the stream
    stream.synchronize()
    # Return the host outputs
    return [out.host for out in outputs]

if __name__ == "__main__":
#    engine_path = "/home/brais/workspace/src/resnet50_fp16.trt"
#    trt_inference = TensorRTInference(engine_path)
#    img = Image.open("/home/brais/workspace/src/imagenet_1k/train/000/050_664.jpg").resize((256,256))
#
#    left = (256 - 224)/2
#    top = (256 - 224)/2
#    right = (256 + 224)/2
#    bottom = (256 + 224)/2
#
#    img = img.crop((left, top, right, bottom))
#
#    img_array = np.array(img)
#    inputs = img_array.transpose(2, 0, 1)  # (3, 224, 224)
#    
#    # Run inference
#    output_data = trt_inference.infer(inputs)
#    # output_data in (1280, ) shape

    trt_engine_path = "/home/brais/workspace/src/resnet50.trt"

    # Read the serialized ICudaEngine
    with open(trt_engine_path, 'rb') as f, trt.Runtime(trt.Logger(trt.Logger.ERROR)) as runtime:
        # Deserialize ICudaEngine
        engine = runtime.deserialize_cuda_engine(f.read())

    #camera = cv.VideoCapture('nvv4l2camerasrc device=/dev/video0 ! video/x-raw(memory:NVMM),format=UYVY,width=1280,height=720,framerate=30/1 ! nvvidconv ! video/x-raw,format=BGRx ! videoconvert ! video/x-raw,format=BGR ! appsink drop=1', cv.CAP_GSTREAMER)
    camera = cv.VideoCapture('nvarguscamerasrc ! video/x-raw(memory:NVMM),width=1024,height=576,framerate=10/1 ! nvvidconv flip-method=2 ! videoconvert ! video/x-raw,format=BGR ! appsink drop=1', cv.CAP_GSTREAMER)

    if not camera.isOpened():
        print('Failed to open camera')
        exit(-1)

    w = int(camera.get(cv.CAP_PROP_FRAME_WIDTH))
    h = int(camera.get(cv.CAP_PROP_FRAME_HEIGHT))
    fps = float(camera.get(cv.CAP_PROP_FPS))

    print('Camera opened - Framing %dx%d@%f fps' % (w,h,fps))

    font                   = cv.FONT_HERSHEY_SIMPLEX
    bottomLeftCornerOfText = (10,30)
    fontScale              = 1
    fontColor              = (255,255,255)
    thickness              = 1
    lineType               = 2

    with open('./labels.txt','r') as file:
        data = json.load(file)

    #img = Image.open("/home/brais/workspace/src/imagenet_1k/train/000/050_664.jpg").resize((256,256))
    #left = (256 - 224)/2
    #top = (256 - 224)/2
    #right = (256 + 224)/2
    #bottom = (256 + 224)/2
    #img = img.crop((left, top, right, bottom))
    #img_array = np.array(img)
    #inputs = img_array.transpose(2, 0, 1)  # (3, 224, 224)

    while True:

        ret, frame = camera.read()

        if not ret:
            print('Failed to read frame from camera')
            camera.release()
            exit(-3)

        img = cv.resize(frame, (256,256))
        crop_img = img[int(256-224):int(224), int(256-224):int(224)]
        #img_array = np.array(crop_img)
        #cv.imshow('Cropped frame',crop_img)

        # Create an IExecutionContext (context for executing inference)
        with engine.create_execution_context() as context:

            img = Image.open("/home/brais/workspace/src/imagenet_1k/train/000/050_664.jpg").resize((256,256))
            left = (256 - 224)/2
            top = (256 - 224)/2
            right = (256 + 224)/2
            bottom = (256 + 224)/2
            img = img.crop((left, top, right, bottom))
            img_array = np.array(img)

            # Allocate memory for inputs/outputs
            inputs, outputs, bindings, stream = allocate_buffers(engine)
            # Set host input to the image
            inputs[0].host = img_array
            # Inference
            trt_outputs = infer(context, bindings=bindings, inputs=inputs, outputs=outputs, stream=stream)
            # Prediction
            pred_id = np.argmax(trt_outputs)
            print(trt_outputs[0][24])

        cv.putText(frame,str(pred_id),
                   bottomLeftCornerOfText, font, fontScale, fontColor, thickness, lineType)

        cv.imshow('Camera output - %1.0f fps' % (fps),frame)

        if cv.waitKey(1) == ord('q'):
            break

    camera.release()
    cv.destroyAllWindows()



