# Copyright [2020] Luis Alberto Pineda Cortés, Gibrán Fuentes Pineda,
# Rafael Morales Gamboa.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from PIL import Image
import sys
import numpy as np
import tensorflow as tf
from tensorflow.keras import Model
from tensorflow.keras.layers import Input, Conv2D, MaxPooling2D, Dropout, Flatten, Dense, \
    Activation, Reshape, Conv2DTranspose, BatchNormalization
from tensorflow.keras.utils import to_categorical
from joblib import Parallel, delayed
# import png

import constants

img_rows = 32
img_columns = 32

batch_size = 100

TOP_SIDE = 0
BOTTOM_SIDE = 1
LEFT_SIDE = 2
RIGHT_SIDE = 3
VERTICAL_BARS = 4
HORIZONTAL_BARS = 5


def print_error(*s):
    print('Error:', *s, file=sys.stderr)


def add_side_occlusion(data, side_hidden, occlusion):
    noise_value = 0
    mid_row = int(round(img_rows*occlusion))
    mid_col = int(round(img_columns*occlusion))
    origin = (0, 0)
    end = (0, 0)

    if side_hidden == TOP_SIDE:
        origin = (0, 0)
        end = (mid_row, img_columns)
    elif side_hidden == BOTTOM_SIDE:
        origin = (mid_row, 0)
        end = (img_rows, img_columns)
    elif side_hidden == LEFT_SIDE:
        origin = (0, 0)
        end = (img_rows, mid_col)
    elif side_hidden == RIGHT_SIDE:
        origin = (0, mid_col)
        end = (img_rows, img_columns)

    for image in data:
        n, m = origin
        end_n, end_m = end

        for i in range(n, end_n):
            for j in range(m, end_m):
                image[i, j] = noise_value

    return data


def add_bars_occlusion(data, bars, n):
    pattern = constants.bar_patterns[n]

    if bars == VERTICAL_BARS:
        for image in data:
            for j in range(img_columns):
                image[:, j] *= pattern[j]
    else:
        for image in data:
            for i in range(img_rows):
                image[i, :] *= pattern[i]

    return data


def add_noise(data, experiment, occlusion=0, bars_type=None):
    # data is assumed to be a numpy array of shape (N, img_rows, img_columns)

    if experiment < constants.EXP_5:
        return data
    elif experiment < constants.EXP_9:
        sides = {constants.EXP_5: TOP_SIDE,  constants.EXP_6: BOTTOM_SIDE,
                 constants.EXP_7: LEFT_SIDE, constants.EXP_8: RIGHT_SIDE}
        return add_side_occlusion(data, sides[experiment], occlusion)
    else:
        bars = {constants.EXP_9: VERTICAL_BARS,
                constants.EXP_10: HORIZONTAL_BARS}
        return add_bars_occlusion(data, bars[experiment], bars_type)


def get_data(experiment, occlusion=None, bars_type=None, one_hot=False):

   # Load CIFAR10 data, as part of TensorFlow.
    cifar = tf.keras.datasets.cifar10
    (train_images, train_labels), (test_images, test_labels) = cifar.load_data()
    train_labels = train_labels.reshape(-1, )
    test_labels = test_labels.reshape(-1, )

    all_data = np.concatenate((train_images, test_images), axis=0)
    all_labels = np.concatenate((train_labels, test_labels), axis=0)

    all_data = add_noise(all_data, experiment, occlusion, bars_type)

    all_data = all_data.reshape(
        (60000, img_columns, img_rows, constants.colors))
    all_data = all_data.astype('float32') / 255

    if one_hot:
        # Changes labels to binary rows. Each label correspond to a column, and only
        # the column for the corresponding label is set to one.
        all_labels = to_categorical(all_labels)

    return (all_data, all_labels)


def useBlockEncoder(input, filters, repeat=1):
    """
    Convolution block of 2 layers
    """
    x = input
    for _ in range(repeat):
        x = Conv2D(filters, 4, strides=2, padding="same")(x)
        x = Activation("relu")(x)
        x = BatchNormalization()(x)
    return x


def useBlockDecoder(input, filters, repeat=1, light=False):
    """
    Convolution block of 2 layers
    """
    x = input
    for _ in range(repeat):
        x = Conv2DTranspose(filters, 4, strides=2, padding='same')(x)
        if light:
            x = Dropout(0.4)(x)
        else:
            x = Activation("relu")(x)
            x = BatchNormalization()(x)
    return x


def get_encoder(input_img):

    # Convolutional Encoder
    # conv_1 = Conv2D(32, kernel_size=3, activation='relu', padding='same',
    #                 input_shape=(img_columns, img_rows, constants.colors))(input_img)
    # pool_1 = MaxPooling2D((2, 2))(conv_1)
    # conv_2 = Conv2D(32, kernel_size=3, activation='relu')(pool_1)
    # pool_2 = MaxPooling2D((2, 2))(conv_2)
    # drop_1 = Dropout(0.4)(pool_2)
    # conv_3 = Conv2D(64, kernel_size=5, activation='relu')(drop_1)
    # pool_3 = MaxPooling2D((2, 2))(conv_3)
    # drop_2 = Dropout(0.4)(pool_3)

    x = Conv2D(32, kernel_size=3, activation='relu', padding='same',
               input_shape=(img_columns, img_rows, constants.colors))(input_img)
    x = MaxPooling2D(2)(x)
    x = useBlockEncoder(x, 32)
    x = MaxPooling2D(2)(x)
    x = useBlockEncoder(x, constants.domain)

    # Produces an array of size equal to constants.domain.
    code = Flatten()(x)

    return code


def get_decoder(encoded):
    dense = Dense(units=4 * 4 * 32, activation='relu', input_shape=(constants.domain, ))(encoded)
    # dense = Dense(units=4 * 4 * 32, activation='relu')(encoded)
    reshape = Reshape((4, 4, 32))(dense)
    x = useBlockDecoder(reshape, 64)
    x = useBlockDecoder(x, 32, repeat=2, light=True)
    x = useBlockDecoder(x, 8, light=True)
    drop_2 = Dropout(0.4)(x)
    output_img = Conv2D(constants.colors, kernel_size=4, strides=2,
                        activation='sigmoid', padding='same', name='autoencoder')(drop_2)

    # Produces an image of same size and channels as originals.
    return output_img


def get_classifier(encoded):
    # mean = Dense(constants.domain*2, activation='softplus')(encoded)
    # sigma = Dense(constants.domain*2, activation='relu')(encoded)
    # sqr = tf.sqrt(tf.exp(sigma))
    # z = mean + tf.multiply(sqr, tf.random.normal(shape=tf.shape(sqr)))
    # drop = Dropout(0.4)(z)
    # classification = Dense(10, activation='softmax',
    #                        name='classification')(drop)

    dense_1 = Dense(constants.domain*2, activation='relu')(encoded)
    drop = Dropout(0.4)(dense_1)
    classification = Dense(10, activation='softmax',
                           name='classification')(drop)

    return classification


def train_networks(training_percentage, filename, experiment):

    EPOCHS = constants.model_epochs
    stages = constants.training_stages

    (data, labels) = get_data(experiment, one_hot=True)

    total = len(data)
    step = int(total/stages)

    # Amount of testing data
    atd = total - int(total*training_percentage)

    n = 0
    histories = []
    for i in range(0, total, step):
        j = (i + atd) % total

        if j > i:
            testing_data = data[i:j]
            testing_labels = labels[i:j]

            training_data = np.concatenate((data[0:i], data[j:total]), axis=0)
            training_labels = np.concatenate(
                (labels[0:i], labels[j:total]), axis=0)
        else:
            testing_data = np.concatenate((data[i:total], data[0:j]), axis=0)
            testing_labels = np.concatenate(
                (labels[i:total], labels[0:j]), axis=0)
            training_data = data[j:i]
            training_labels = labels[j:i]

        input_img = Input(shape=(img_columns, img_rows, 3))
        encoded = get_encoder(input_img)
        classified = get_classifier(encoded)
        decoded = get_decoder(encoded)
        model = Model(inputs=input_img, outputs=[classified, decoded])

        model.compile(loss=['categorical_crossentropy', 'binary_crossentropy'],
                      optimizer='adam',
                      metrics='accuracy')

        model.summary()

        history = model.fit(training_data,
                            (training_labels, training_data),
                            batch_size=batch_size,
                            epochs=EPOCHS,
                            validation_data=(testing_data,
                                             {'classification': testing_labels, 'autoencoder': testing_data}),
                            verbose=2)

        histories.append(history)
        model.save(constants.model_filename(filename, n))
        n += 1

    return histories


def store_images(original, produced, directory, stage, idx, label):
    original_filename = constants.original_image_filename(
        directory, stage, idx, label)
    produced_filename = constants.produced_image_filename(
        directory, stage, idx, label)

    pixels = original.reshape(img_columns, img_rows, constants.colors) * 255
    pixels = pixels.round().astype(np.uint8)
    img = Image.fromarray(pixels, 'RGB')
    img.save(original_filename)
    # png.from_array(pixels, 'L;8').save(original_filename)
    pixels = produced.reshape(img_columns, img_rows, constants.colors) * 255
    pixels = pixels.round().astype(np.uint8)
    img = Image.fromarray(pixels, 'RGB')
    img.save(produced_filename)
    # png.from_array(pixels, 'L;8').save(produced_filename)


def store_memories(labels, produced, features, directory, stage, msize):
    (idx, label) = labels
    produced_filename = constants.produced_memory_filename(
        directory, msize, stage, idx, label)

    if np.isnan(np.sum(features)):
        pixels = np.full((img_columns, img_rows, constants.colors), 255)
    else:
        pixels = produced.reshape(
            img_columns, img_rows, constants.colors) * 255
    pixels = pixels.round().astype(np.uint8)
    img = Image.fromarray(pixels, 'RGB')
    img.save(produced_filename)
    # png.from_array(pixels, 'L;8').save(produced_filename)


def obtain_features(model_prefix, features_prefix, labels_prefix, data_prefix,
                    training_percentage, am_filling_percentage, experiment,
                    occlusion=None, bars_type=None):
    """ Generate features for images.

    Uses the previously trained neural networks for generating the features corresponding
    to the images. It may introduce occlusions.
    """
    (data, labels) = get_data(experiment, occlusion, bars_type)
    # data - imagenes - (60000, 32, 32, 3)
    # labels - txt - (60000,)

    total = len(data)
    step = int(total/constants.training_stages)

    # Amount of data used for training the networks
    trdata = int(total*training_percentage)

    # Amount of data used for testing memories
    tedata = step

    n = 0
    histories = []
    for i in range(0, total, step):
        j = (i + tedata) % total

        if j > i:
            testing_data = data[i:j]
            testing_labels = labels[i:j]
            other_data = np.concatenate((data[0:i], data[j:total]), axis=0)
            other_labels = np.concatenate(
                (labels[0:i], labels[j:total]), axis=0)
            training_data = other_data[:trdata]
            training_labels = other_labels[:trdata]
            filling_data = other_data[trdata:]
            filling_labels = other_labels[trdata:]
        else:
            testing_data = np.concatenate((data[0:j], data[i:total]), axis=0)
            testing_labels = np.concatenate(
                (labels[0:j], labels[i:total]), axis=0)
            training_data = data[j:j+trdata]
            training_labels = labels[j:j+trdata]
            filling_data = data[j+trdata:i]
            filling_labels = labels[j+trdata:i]

        # Recreate the exact same model, including its weights and the optimizer
        model = tf.keras.models.load_model(
            constants.model_filename(model_prefix, n))

        # Drop the autoencoder and the last layers of the full connected neural network part.
        classifier = Model(model.input, model.output[0])
        no_hot = to_categorical(testing_labels)
        classifier.compile(
            optimizer='adam', loss='categorical_crossentropy', metrics='accuracy')
        history = classifier.evaluate(
            testing_data, no_hot, batch_size=batch_size, verbose=1, return_dict=True)
        print(history)
        histories.append(history)
        model = Model(classifier.input, classifier.layers[-4].output)
        model.summary()

        training_features = model.predict(training_data)
        if len(filling_data) > 0:
            filling_features = model.predict(filling_data)
        else:
            r, c = training_features.shape
            filling_features = np.zeros((0, c))
        testing_features = model.predict(testing_data)

        dict = {
            constants.training_suffix: (training_data, training_features, training_labels),
            constants.filling_suffix: (filling_data, filling_features, filling_labels),
            constants.testing_suffix: (
                testing_data, testing_features, testing_labels)
        }

        for suffix in dict:
            data_fn = constants.data_filename(data_prefix+suffix, n)
            features_fn = constants.data_filename(features_prefix+suffix, n)
            labels_fn = constants.data_filename(labels_prefix+suffix, n)

            d, f, l = dict[suffix]
            np.save(data_fn, d)
            np.save(features_fn, f)
            np.save(labels_fn, l)

        n += 1

    return histories


def remember(experiment, occlusion=None, bars_type=None, tolerance=0):
    """ Creates images from features.

    Uses the decoder part of the neural networks to (re)create images from features.

    Parameters
    ----------
    experiment : TYPE
        DESCRIPTION.
    occlusion : TYPE, optional
        DESCRIPTION. The default is None.
    tolerance : TYPE, optional
        DESCRIPTION. The default is 0.

    Returns
    -------
    None.

    """

    for i in range(constants.training_stages):
        testing_data_filename = constants.data_name + constants.testing_suffix
        testing_data_filename = constants.data_filename(
            testing_data_filename, i)
        testing_features_filename = constants.features_name(
            experiment, occlusion, bars_type) + constants.testing_suffix
        testing_features_filename = constants.data_filename(
            testing_features_filename, i)
        testing_labels_filename = constants.labels_name + constants.testing_suffix
        testing_labels_filename = constants.data_filename(
            testing_labels_filename, i)
        memories_filename = constants.memories_name(
            experiment, occlusion, bars_type, tolerance)
        memories_filename = constants.data_filename(memories_filename, i)
        labels_filename = constants.labels_name + constants.memory_suffix
        labels_filename = constants.data_filename(labels_filename, i)
        model_filename = constants.model_filename(constants.model_name, i)

        testing_data = np.load(testing_data_filename)
        testing_features = np.load(testing_features_filename)
        testing_labels = np.load(testing_labels_filename)
        memories = np.load(memories_filename)
        labels = np.load(labels_filename)
        model = tf.keras.models.load_model(model_filename)

        # Drop the classifier.
        autoencoder = Model(model.input, model.output[1])
        autoencoder.summary()

        # Drop the encoder
        input_mem = Input(shape=(constants.domain, ))
        decoded = get_decoder(input_mem)
        decoder = Model(inputs=input_mem, outputs=decoded)
        decoder.summary()

        # for dlayer, alayer in zip(decoder.layers[1:], autoencoder.layers[11:]):
        for dlayer, alayer in zip(decoder.layers[1:], autoencoder.layers[11:]):
            dlayer.set_weights(alayer.get_weights())

        produced_images = decoder.predict(testing_features)
        n = len(testing_labels)

        Parallel(n_jobs=constants.n_jobs, verbose=5)(
            delayed(store_images)(original, produced, constants.testing_directory(
                experiment, occlusion, bars_type), i, j, label)
            for (j, original, produced, label) in
            zip(range(n), testing_data, produced_images, testing_labels))

        total = len(memories)
        steps = len(constants.memory_fills)
        step_size = int(total/steps)

        for j in range(steps):
            print('Decoding memory size ' + str(j) + ' and stage ' + str(i))
            start = j*step_size
            end = start + step_size
            mem_data = memories[start:end]
            mem_labels = labels[start:end]
            produced_images = decoder.predict(mem_data)

            Parallel(n_jobs=constants.n_jobs, verbose=5)(
                delayed(store_memories)(label, produced, features, constants.memories_directory(
                    experiment, occlusion, bars_type, tolerance), i, j)
                for (produced, features, label) in zip(produced_images, mem_data, mem_labels))
