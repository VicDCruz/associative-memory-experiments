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

import sys
import numpy as np
import tensorflow as tf
from tensorflow.keras import Model
from tensorflow.keras.layers import Input, Conv2D, MaxPooling2D, Dropout, Flatten, Dense, \
    LayerNormalization, Reshape, Conv2DTranspose, BatchNormalization, UpSampling2D
from tensorflow.keras.utils import to_categorical
from tensorflow.keras.callbacks import Callback
from joblib import Parallel, delayed
from extra_keras_datasets import emnist
import png

import constants

LABELS = constants.n_labels

img_rows = 28
img_columns = 28

TOP_SIDE = 0
BOTTOM_SIDE = 1
LEFT_SIDE = 2
RIGHT_SIDE = 3
VERTICAL_BARS = 4
HORIZONTAL_BARS = 5

truly_training_percentage = 0.80
epochs = 40
batch_size = 100
patience = 8


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

    # Load MNIST data, as part of TensorFlow.
    (train_images, train_labels), (test_images, test_labels) = emnist.load_data(type='balanced')

    all_data = np.concatenate((train_images, test_images), axis=0)
    all_labels = np.concatenate((train_labels, test_labels), axis=0)

    for i,l in enumerate(all_labels):
        all_labels[i] = {
            36:10,
            37:11,
            38:13,
            39:14,
            40:15,
            41:16,
            42:17,
            43:23,
            44:26,
            45:27,
            46:29
        }.get(l,l)

    all_data = add_noise(all_data, experiment, occlusion, bars_type)

    all_data = all_data.reshape((all_labels.size, img_columns, img_rows, 1))
    all_data = all_data.astype('float32') / 255

    if one_hot:
        # Changes labels to binary rows. Each label correspond to a column, and only
        # the column for the corresponding label is set to one.
        all_labels = to_categorical(all_labels)

    return (all_data, all_labels)


def get_data_in_range(data, i, j):
    total = len(data)
    if j >= i:
        return data[i:j]
    else:
        return np.concatenate((data[i:total], data[0:j]), axis=0)


def get_encoder(input_img):

    # Convolutional Encoder
    conv = Conv2D(constants.domain//2, kernel_size=3, activation='relu', padding='same',
                  input_shape=(img_columns, img_rows, 1))(input_img)
    batch = BatchNormalization()(conv)
    conv = Conv2D(constants.domain//2, kernel_size=3,
                  activation='relu', padding='same')(batch)
    batch = BatchNormalization()(conv)
    pool = MaxPooling2D((2, 2))(batch)
    drop = Dropout(0.4)(pool)

    conv = Conv2D(constants.domain//2, kernel_size=3,
                  activation='relu', padding='same')(drop)
    batch = BatchNormalization()(conv)
    conv = Conv2D(constants.domain//2, kernel_size=3,
                  activation='relu', padding='same')(batch)
    batch = BatchNormalization()(conv)
    pool = MaxPooling2D((2, 2))(batch)
    drop = Dropout(0.4)(pool)

    conv = Conv2D(constants.domain, kernel_size=3,
                  activation='relu', padding='same')(drop)
    batch = BatchNormalization()(conv)
    conv = Conv2D(constants.domain, kernel_size=3,
                  activation='relu', padding='same')(batch)
    batch = BatchNormalization()(conv)
    conv = Conv2D(constants.domain, kernel_size=3,
                  activation='relu', padding='same')(batch)
    batch = BatchNormalization()(conv)
    pool = MaxPooling2D((2, 2))(batch)
    drop = Dropout(0.4)(pool)

    conv = Conv2D(constants.domain, kernel_size=3,
                  activation='relu', padding='same')(drop)
    batch = BatchNormalization()(conv)
    conv = Conv2D(constants.domain, kernel_size=3,
                  activation='relu', padding='same')(batch)
    batch = BatchNormalization()(conv)
    conv = Conv2D(constants.domain, kernel_size=3,
                  activation='relu', padding='same')(batch)
    batch = BatchNormalization()(conv)
    pool = MaxPooling2D((2, 2))(batch)
    drop = Dropout(0.4)(pool)
    norm = LayerNormalization()(drop)

    # Produces an array of size equal to constants.domain.
    code = Flatten()(norm)

    return code


def get_decoder(encoded):

    dense = Dense(units=7*7*32, activation='relu', input_shape=(64, ))(encoded)
    reshape = Reshape((7, 7, 32))(dense)

    trans = Conv2DTranspose(64, kernel_size=3, strides=1,
                            padding='same', activation='relu')(reshape)
    drop = Dropout(0.4)(trans)

    trans = Conv2DTranspose(64, kernel_size=3, strides=2,
                            padding='same', activation='relu')(drop)
    drop = Dropout(0.4)(trans)

    trans = Conv2DTranspose(32, kernel_size=3, strides=1,
                            padding='same', activation='relu')(drop)
    drop = Dropout(0.4)(trans)

    trans = Conv2DTranspose(32, kernel_size=3, strides=2,
                            padding='same', activation='relu')(drop)
    drop = Dropout(0.4)(trans)

    output_img = Conv2D(1, kernel_size=3, strides=1,
                        activation='sigmoid', padding='same', name='autoencoder')(drop)

    # up = UpSampling2D((2,2))(reshape)
    # conv = Conv2D(64,kernel_size=3,activation='relu',padding='same')(up)
    # batch = BatchNormalization()(conv)
    # conv = Conv2D(64,kernel_size=3,activation='relu',padding='same')(batch)
    # batch = BatchNormalization()(conv)
    # conv = Conv2D(64,kernel_size=3,activation='relu',padding='same')(batch)
    # batch = BatchNormalization()(conv)

    # up = UpSampling2D((2,2))(batch)
    # conv = Conv2D(32,kernel_size=3,activation='relu',padding='same')(up)
    # batch = BatchNormalization()(conv)
    # conv = Conv2D(32,kernel_size=3,activation='relu',padding='same')(batch)
    # batch = BatchNormalization()(conv)

    # output_img = Conv2D(1, kernel_size=3, strides=1,
    #     activation='sigmoid', padding='same', name='autoencoder')(batch)

    # Produces an image of same size and channels as originals.
    return output_img


def get_classifier(encoded):
    dense = Dense(constants.domain*2, activation='relu')(encoded)
    drop = Dropout(0.4)(dense)

    #dense = Dense(constants.domain, activation='relu')(drop)
    #drop = Dropout(0.4)(dense)

    classification = Dense(LABELS, activation='softmax',
                           name='classification')(drop)

    return classification


class EarlyStoppingAtLossCrossing(Callback):
    """ Stop training when the loss gets lower than val_loss.

        Arguments:
            patience: Number of epochs to wait after condition has been hit.
            After this number of no reversal, training stops.
            It starts working after 10% of epochs have taken place.
    """

    def __init__(self, patience=0):
        super(EarlyStoppingAtLossCrossing, self).__init__()
        self.patience = patience
        self.prev_loss = float('inf')
        # best_weights to store the weights at which the loss crossing occurs.
        self.best_weights = None
        self.start = max(epochs // 20, 3)
        self.wait = 0

    def on_train_begin(self, logs=None):
        # The number of epoch it has waited since loss crossed val_loss.
        self.wait = 0
        # The epoch the training stops at.
        self.stopped_epoch = 0

    def on_epoch_end(self, epoch, logs=None):
        loss = logs.get('loss')
        val_loss = logs.get('val_loss')

        if (epoch < self.start) or ((val_loss < self.prev_loss) and (val_loss < loss)):
            self.wait = 0
            self.prev_loss = val_loss
            self.best_weights = self.model.get_weights()
        else:
            self.wait += 1
            if self.wait >= self.patience:
                self.stopped_epoch = epoch
                self.model.stop_training = True
                print("Restoring model weights from the end of the best epoch.")
                self.model.set_weights(self.best_weights)

    def on_train_end(self, logs=None):
        if self.stopped_epoch > 0:
            print("Epoch %05d: early stopping" % (self.stopped_epoch + 1))


def train_networks(training_percentage, filename, experiment):

    stages = constants.training_stages

    (data, labels) = get_data(experiment, one_hot=True)

    total = len(data)
    step = total/stages

    # Amount of training data, from which a percentage is used for
    # validation.
    training_size = int(total*training_percentage)

    histories = []
    for n in range(stages):
        i = int(n*step)
        j = (i + training_size) % total

        training_data = get_data_in_range(data, i, j)
        training_labels = get_data_in_range(labels, i, j)
        testing_data = get_data_in_range(data, j, i)
        testing_labels = get_data_in_range(labels, j, i)

        truly_training = int(training_size*truly_training_percentage)

        validation_data = training_data[truly_training:]
        validation_labels = training_labels[truly_training:]
        training_data = training_data[:truly_training]
        training_labels = training_labels[:truly_training]

        input_img = Input(shape=(img_columns, img_rows, 1))
        encoded = get_encoder(input_img)
        classified = get_classifier(encoded)
        decoded = get_decoder(encoded)

        model = Model(inputs=input_img, outputs=[classified, decoded])

        model.compile(loss=['categorical_crossentropy', 'mean_squared_error'],
                      optimizer='adam',
                      metrics='accuracy')

        model.summary()

        history = model.fit(training_data,
                            (training_labels, training_data),
                            batch_size=batch_size,
                            epochs=epochs,
                            validation_data=(validation_data,
                                             {'classification': validation_labels, 'autoencoder': validation_data}),
                            callbacks=[EarlyStoppingAtLossCrossing(patience)],
                            verbose=2)

        histories.append(history)
        history = model.evaluate(testing_data,
                                 (testing_labels, testing_data), return_dict=True)
        histories.append(history)

        model.save(constants.model_filename(filename, n))

    return histories


def store_images(original, produced, directory, stage, idx, label):
    original_filename = constants.original_image_filename(
        directory, stage, idx, label)
    produced_filename = constants.produced_image_filename(
        directory, stage, idx, label)

    pixels = original.reshape(28, 28) * 255
    pixels = pixels.round().astype(np.uint8)
    png.from_array(pixels, 'L;8').save(original_filename)
    pixels = produced.reshape(28, 28) * 255
    pixels = pixels.round().astype(np.uint8)
    png.from_array(pixels, 'L;8').save(produced_filename)


def store_memories(labels, produced, features, directory, stage, msize):
    (idx, label) = labels
    produced_filename = constants.produced_memory_filename(
        directory, msize, stage, idx, label)

    if np.isnan(np.sum(features)):
        pixels = np.full((28, 28), 255)
    else:
        pixels = produced.reshape(28, 28) * 255
    pixels = pixels.round().astype(np.uint8)
    png.from_array(pixels, 'L;8').save(produced_filename)


def obtain_features(model_prefix, features_prefix, labels_prefix, data_prefix,
                    training_percentage, am_filling_percentage, experiment,
                    occlusion=None, bars_type=None):
    """ Generate features for images.

    Uses the previously trained neural networks for generating the features corresponding
    to the images. It may introduce occlusions.
    """
    stages = constants.training_stages

    (data, labels) = get_data(experiment, occlusion, bars_type)

    total = len(data)
    step = int(total/constants.training_stages)

    training_size = int(total*training_percentage)
    filling_size = int(total*am_filling_percentage)
    testing_size = total - training_size - filling_size

    histories = []
    for n in range(stages):
        i = int(n*step)
        j = (i+training_size) % total

        training_data = get_data_in_range(data, i, j)
        training_labels = get_data_in_range(labels, i, j)

        k = (j+filling_size) % total
        filling_data = get_data_in_range(data, j, k)
        filling_labels = get_data_in_range(labels, j, k)

        l = (k+testing_size) % total
        testing_data = get_data_in_range(data, k, l)
        testing_labels = get_data_in_range(labels, k, l)

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

        for dlayer, alayer in zip(decoder.layers[1:], autoencoder.layers[31:]):
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
