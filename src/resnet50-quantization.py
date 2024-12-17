#!/usr/bin/env python

# Since resnet50 network implementation of pytorch is not quantizable, we need to modify the network, so that we can quantize it.

import torch
from torch import Tensor
import torch.nn as nn
from typing import Type, Any, Callable, Union, List, Optional
from torch.quantization import QuantStub, DeQuantStub


try:
    from torch.hub import load_state_dict_from_url
except ImportError:
    from torch.utils.model_zoo import load_url as load_state_dict_from_url


model_urls = {
    'resnet50': 'https://download.pytorch.org/models/resnet50-19c8e357.pth',
}


def conv3x3(in_planes: int, out_planes: int, stride: int = 1, groups: int = 1, dilation: int = 1) -> nn.Conv2d:
    """3x3 convolution with padding"""
    return nn.Conv2d(in_planes, out_planes, kernel_size=3, stride=stride,
                     padding=dilation, groups=groups, bias=False, dilation=dilation)


def conv1x1(in_planes: int, out_planes: int, stride: int = 1) -> nn.Conv2d:
    """1x1 convolution"""
    return nn.Conv2d(in_planes, out_planes, kernel_size=1, stride=stride, bias=False)


class BasicBlock(nn.Module):
    expansion: int = 1

    def __init__(
        self,
        inplanes: int,
        planes: int,
        stride: int = 1,
        downsample: Optional[nn.Module] = None,
        groups: int = 1,
        base_width: int = 64,
        dilation: int = 1,
        norm_layer: Optional[Callable[..., nn.Module]] = None
    ) -> None:
        super(BasicBlock, self).__init__()
        if norm_layer is None:
            norm_layer = nn.BatchNorm2d
        if groups != 1 or base_width != 64:
            raise ValueError('BasicBlock only supports groups=1 and base_width=64')
        if dilation > 1:
            raise NotImplementedError("Dilation > 1 not supported in BasicBlock")
        # Both self.conv1 and self.downsample layers downsample the input when stride != 1
        self.conv1 = conv3x3(inplanes, planes, stride)
        self.bn1 = norm_layer(planes)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = conv3x3(planes, planes)
        self.bn2 = norm_layer(planes)
        self.downsample = downsample
        self.stride = stride
        self.skip_add = nn.quantized.FloatFunctional()

    def forward(self, x: Tensor) -> Tensor:
        identity = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)

        if self.downsample is not None:
            identity = self.downsample(x)

        #out += identity
        out = self.skip_add.add(out, identity)
        out = self.relu(out)

        return out


class Bottleneck(nn.Module):
    # Bottleneck in torchvision places the stride for downsampling at 3x3 convolution(self.conv2)
    # while original implementation places the stride at the first 1x1 convolution(self.conv1)
    # according to "Deep residual learning for image recognition"https://arxiv.org/abs/1512.03385.
    # This variant is also known as ResNet V1.5 and improves accuracy according to
    # https://ngc.nvidia.com/catalog/model-scripts/nvidia:resnet_50_v1_5_for_pytorch.

    expansion: int = 4

    def __init__(
        self,
        inplanes: int,
        planes: int,
        stride: int = 1,
        downsample: Optional[nn.Module] = None,
        groups: int = 1,
        base_width: int = 64,
        dilation: int = 1,
        norm_layer: Optional[Callable[..., nn.Module]] = None
    ) -> None:
        super(Bottleneck, self).__init__()
        if norm_layer is None:
            norm_layer = nn.BatchNorm2d
        width = int(planes * (base_width / 64.)) * groups
        # Both self.conv2 and self.downsample layers downsample the input when stride != 1
        self.conv1 = conv1x1(inplanes, width)
        self.bn1 = norm_layer(width)
        self.conv2 = conv3x3(width, width, stride, groups, dilation)
        self.bn2 = norm_layer(width)
        self.conv3 = conv1x1(width, planes * self.expansion)
        self.bn3 = norm_layer(planes * self.expansion)
        self.relu = nn.ReLU(inplace=True)
        self.downsample = downsample
        self.stride = stride
        self.skip_add = nn.quantized.FloatFunctional()

    def forward(self, x: Tensor) -> Tensor:
        identity = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)
        out = self.relu(out)

        out = self.conv3(out)
        out = self.bn3(out)

        if self.downsample is not None:
            identity = self.downsample(x)

        #out += identity 
        out = self.skip_add.add(out, identity)
        out = self.relu(out)

        return out


class ResNet(nn.Module):

    def __init__(
        self,
        block: Type[Union[BasicBlock, Bottleneck]],
        layers: List[int],
        num_classes: int = 1000,
        zero_init_residual: bool = False,
        groups: int = 1,
        width_per_group: int = 64,
        replace_stride_with_dilation: Optional[List[bool]] = None,
        norm_layer: Optional[Callable[..., nn.Module]] = None
    ) -> None:
        super(ResNet, self).__init__()
        if norm_layer is None:
            norm_layer = nn.BatchNorm2d
        self._norm_layer = norm_layer

        self.inplanes = 64
        self.dilation = 1
        if replace_stride_with_dilation is None:
            # each element in the tuple indicates if we should replace
            # the 2x2 stride with a dilated convolution instead
            replace_stride_with_dilation = [False, False, False]
        if len(replace_stride_with_dilation) != 3:
            raise ValueError("replace_stride_with_dilation should be None "
                             "or a 3-element tuple, got {}".format(replace_stride_with_dilation))
        self.groups = groups
        self.base_width = width_per_group
        self.conv1 = nn.Conv2d(3, self.inplanes, kernel_size=7, stride=2, padding=3,
                               bias=False)
        self.bn1 = norm_layer(self.inplanes)
        self.relu = nn.ReLU(inplace=True)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        self.layer1 = self._make_layer(block, 64, layers[0])
        self.layer2 = self._make_layer(block, 128, layers[1], stride=2,
                                       dilate=replace_stride_with_dilation[0])
        self.layer3 = self._make_layer(block, 256, layers[2], stride=2,
                                       dilate=replace_stride_with_dilation[1])
        self.layer4 = self._make_layer(block, 512, layers[3], stride=2,
                                       dilate=replace_stride_with_dilation[2])
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(512 * block.expansion, num_classes)

        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
            elif isinstance(m, (nn.BatchNorm2d, nn.GroupNorm)):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)

        self.quant = QuantStub()
        self.dequant = DeQuantStub()
        # Zero-initialize the last BN in each residual branch,
        # so that the residual branch starts with zeros, and each residual block behaves like an identity.
        # This improves the model by 0.2~0.3% according to https://arxiv.org/abs/1706.02677
        if zero_init_residual:
            for m in self.modules():
                if isinstance(m, Bottleneck):
                    nn.init.constant_(m.bn3.weight, 0)  # type: ignore[arg-type]
                elif isinstance(m, BasicBlock):
                    nn.init.constant_(m.bn2.weight, 0)  # type: ignore[arg-type]

    def _make_layer(self, block: Type[Union[BasicBlock, Bottleneck]], planes: int, blocks: int,
                    stride: int = 1, dilate: bool = False) -> nn.Sequential:
        norm_layer = self._norm_layer
        downsample = None
        previous_dilation = self.dilation
        if dilate:
            self.dilation *= stride
            stride = 1
        if stride != 1 or self.inplanes != planes * block.expansion:
            downsample = nn.Sequential(
                conv1x1(self.inplanes, planes * block.expansion, stride),
                norm_layer(planes * block.expansion),
            )

        layers = []
        layers.append(block(self.inplanes, planes, stride, downsample, self.groups,
                            self.base_width, previous_dilation, norm_layer))
        self.inplanes = planes * block.expansion
        for _ in range(1, blocks):
            layers.append(block(self.inplanes, planes, groups=self.groups,
                                base_width=self.base_width, dilation=self.dilation,
                                norm_layer=norm_layer))

        return nn.Sequential(*layers)

    def _forward_impl(self, x: Tensor) -> Tensor:
        # See note [TorchScript super()]
        x = self.quant(x) # add quant
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)

        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)

        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.fc(x)
        x = self.dequant(x) # add dequant

        return x

    def forward(self, x: Tensor) -> Tensor:
        return self._forward_impl(x)


def _resnet(
    arch: str,
    block: Type[Union[BasicBlock, Bottleneck]],
    layers: List[int],
    pretrained: bool,
    progress: bool,
    **kwargs: Any
) -> ResNet:
    model = ResNet(block, layers, **kwargs)
    if pretrained:
        state_dict = load_state_dict_from_url(model_urls[arch],
                                              progress=progress)
        model.load_state_dict(state_dict)
    return model


def resnet50_quantizable(pretrained: bool = False, progress: bool = True, **kwargs: Any) -> ResNet:
    r"""ResNet-50 model from
    `"Deep Residual Learning for Image Recognition" <https://arxiv.org/pdf/1512.03385.pdf>`_.
    Args:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
        progress (bool): If True, displays a progress bar of the download to stderr
    """
    return _resnet('resnet50', Bottleneck, [3, 4, 6, 3], pretrained, progress,
                   **kwargs)

#####################################################################################################################

# add a random seed so that our results would be reproducable
torch.manual_seed(280012)

# load the model
float_model = resnet50_quantizable(pretrained=True).to('cpu')

import os
from PIL import Image
import csv

def load_labels(path):
  img2label = {}
  with open(path) as csv_file:
      csv_reader = csv.reader(csv_file, delimiter=',')
      for row in csv_reader:
        img2label[('00'+row[0].split(':')[0][1:])[-3:]] = row[0].split(':')[1][2:-1] if row[0].split(':')[1][-1:]=="'" else row[0].split(':')[1][2:]
  return img2label

def load_data(data_path, labels_path):
    images = []
    labels = []
    img2label = load_labels(labels_path)
    #print(img2label)
    for folder in os.listdir(data_path):
        full_dir = os.path.join(data_path, folder)
        for filename in os.listdir(full_dir):
            img = Image.open(os.path.join(full_dir,filename)).convert('RGB')
            if img is not None:
                images.append(img)
                labels.append(img2label[('00'+(folder[:3]))[-3:]])
    return images, labels

data_path = "imagenet_1k/"
labels_path = os.path.join(data_path, 'labels.txt')
traindir = os.path.join(data_path, 'train')
valdir = os.path.join(data_path, 'val')
train_data, train_labels = load_data(traindir, labels_path)
test_data, test_labels = load_data(valdir, labels_path)

print('Pasamos la carga')

from torchvision import transforms

def transform_data(data):
  for index, img in enumerate(data):
      preprocess = transforms.Compose([
      transforms.Resize(256),
      transforms.CenterCrop(224),
      transforms.ToTensor(),
      #transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
      ])
      input_tensor = preprocess(img)
      input_batch = input_tensor.unsqueeze(0)
      data[index] = input_batch
  return data

train_data = transform_data(train_data)
test_data = transform_data(test_data)

print('Pasamos la transformacion')

import urllib
import json 

url, filename = ("https://s3.amazonaws.com/deep-learning-models/image-models/imagenet_class_index.json", "labels.txt")
try: urllib.URLopener().retrieve(url, filename)
except: urllib.request.urlretrieve(url, filename)

class_idx = json.load(open(filename))
idx2label = [class_idx[str(k)][1] for k in range(len(class_idx))]

print('Pasamos el labeleado')

import time
def evaluate(model, data, target):
  model.eval()
  total_time, correct = 0, 0
  with torch.no_grad():
    for img, target in zip(data, target):
      start = time.time()
      output = model(img)
      end = time.time()
      delta = end - start
      total_time += delta
      pred_idx = int(output[0].sort()[1][-1:])
      pred = idx2label[pred_idx]
      #print(pred, target)
      if target == pred:
        correct += 1
  inference_time = total_time/len(data)
  accuracy = (correct/len(data))*100
  return inference_time, accuracy

inference_time, accuracy = evaluate(float_model, test_data, test_labels)

print("Baseline Inference Time: ", inference_time)
print("Baseline Accuracy: ", accuracy, '%')

from getpass import getuser

inputs = torch.randn(1,3,224,224)
torch.onnx.export(float_model,inputs,'/home/'+getuser()+'/workspace/src/imagenet_1k/resnet50.onnx',
                  input_names=['input'],output_names=['output'],export_params=True)

###############################################################################################################################

# print('Probamos a quantizar')

# # Our initial baseline model which is FP32
# model_fp32 = float_model
# model_fp32.eval()

# # Sets the backend for x86
# model_fp32.qconfig = torch.quantization.get_default_qconfig('fbgemm')

# # Prepares the model for the next step i.e. calibration.
# # Inserts observers in the model that will observe the activation tensors during calibration
# model_fp32_prepared = torch.quantization.prepare(model_fp32, inplace = False)

# # Calibrate over the train dataset. This determines the quantization params for activation.
# # I used 1000 images of Imagenet train dataset for calibration.
# evaluate(model_fp32_prepared, train_data, train_labels)

# # Converts the model to a quantized model(int8) 
# model_quantized = torch.quantization.convert(model_fp32_prepared) # Quantize the model

# # Evaluates the quantized model on the test dataset
# inference_time, accuracy = evaluate(model_quantized, test_data, test_labels)

# print("Baseline Inference Time: ", inference_time)
# print("Baseline Accuracy: ", accuracy, '%')

# inputs = torch.randn(1,3,224,224)
# torch.onnx.export(model_quantized,inputs,'/home/'+getuser()+'/workspace/src/imagenet_1k/quantized_resnet50.onnx',
#                   input_names=['input'],output_names=['output'],export_params=True)
