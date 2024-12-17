#!/usr/bin/python3

import torch
from torchvision import models
import torch.quantization as qt
import argparse
from getpass import getuser

if __name__ == '__main__':
	# Input Arguments
	parser = argparse.ArgumentParser(description='Course pth model')
	parser.add_argument('--onnx_path', type=str, default='/home/'+getuser()+'/workspace/src/imagenet_1k/resnet50.onnx', required=False, help='Path to save model')
	parser.add_argument('--dynamic_batch', default=False, action='store_true')
	parser.add_argument('--onnx_path_dynamic_batch',  type=str, default='/home/'+getuser()+'/workspace/src/imagenet_1k/resnet50.onnx', required=False, help='Path to save model with dynamic batch')

	args = parser.parse_args()

	onnx_path = args.onnx_path
	dynamic_batch = args.dynamic_batch
	onnx_path_dynamic_batch = args.onnx_path_dynamic_batch

	model = models.resnet50(pretrained=True)
	model.eval()

	inputs = torch.randn(1,3,224,224)

	if dynamic_batch:
		torch.onnx.export(model,inputs,onnx_path_dynamic_batch,
				  input_names=['input'],
				  output_names=['output'],
				  dynamic_axes={'input':{0:'batch_size'},
					        'output':{0:'batch_size'}})

	else:
		torch.onnx.export(model,inputs,onnx_path,
				  input_names=['input'],
				  output_names=['output'],
				  export_params=True)
