# Associative Memories Experiments
This repository contains the data and procedures to replicate the expermients presented in the paper 

Pineda, Luis A., Gibrán Fuentes, y Rafael Morales. 2021. “An entropic associative memory”. *Scientific Reports* 11 (1): 6948. https://doi.org/10.1038/s41598-021-86270-7.

The code was written in Python 3 and was run on a desktop computer with the following specifications:
* CPU: Intel Core i7-6700 at 3.40 GHz
* GPU: Nvidia GeForce GTX 1080
* OS: Ubuntu 16.04 Xenial
* RAM: 64GB

### Requeriments
The following libraries need to be installed beforehand:
* joblib
* matplotlib
* numpy
* png
* TensorFlow 2.3

The experiments were run using the Anaconda 3 distribution.

### Data
The EMNIST database of handwritten digits, available throught TensorFlow 2.3, was used for all the experiments.

### Use

To see how to use the code, just run the following command in the source directory

```shell
python3 main_test_associative.py -h
```



## License

Copyright [2020] Luis Alberto Pineda Cortés, Gibrán Fuentes Pineda, and Rafael Morales Gamboa.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

# References
- [Image Classification on CIFAR-10](https://paperswithcode.com/sota/image-classification-on-cifar-10)
- [Autoencoder as Feature Extractor - EMNIST](https://www.kaggle.com/mahtabshaan/autoencoder-as-feature-extractor-EMNIST/notebook)
- [Convolution padding and stride | Deep Learning Tutorial 25 (Tensorflow2.0, Keras & Python)](https://www.youtube.com/watch?v=oDAPkZ53zKk)
- [Variational autoenconder - VAE (2.)](https://olaralex.com/variational-auto-encoder-with-cifar-10-2/)
- [How to Develop a CNN From Scratch for CIFAR-10 Photo Classification](https://machinelearningmastery.com/how-to-develop-a-cnn-from-scratch-for-cifar-10-photo-classification/)
- [Autoencoder de TensorFlow: Ejemplo de aprendizaje profundo](https://guru99.es/autoencoder-deep-learning/)
- [EMNIST](https://pypi.org/project/emnist/)
- [Mnist and Emnist Handwriting Recognition Using Keras and Tensorflow](https://tracemycode.com/handwriting-recognition-keras-tensorflow/)
- [Tutorial: Alphabet Recognition Through Gestures — A Deep Learning and OpenCV Application](https://towardsdatascience.com/tutorial-alphabet-recognition-deeplearning-opencv-97e697b8fb86)