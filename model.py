""" Convolutional Neural Network.

Build and train a convolutional neural network with TensorFlow.
This example is using the MNIST database of handwritten digits
(http://yann.lecun.com/exdb/mnist/)

This example is using TensorFlow layers API, see 'convolutional_network_raw' 
example for a raw implementation with variables.
"""
from __future__ import division, print_function, absolute_import

import dataset

import tensorflow as tf

tf.logging.set_verbosity(tf.logging.INFO)

# Training Parameters
start_lr = 1e-10
training_steps = 12000
batch_size = 128


# Network Parameters
num_input = 784 # MNIST data input (img shape: 28*28)
num_classes = 10 # MNIST total classes (0-9 digits)
dropout = 0.25 # Dropout, probability to drop a unit

# Data directory
data_dir = '/tmp/mnist/data'

# Create the neural network
def conv_net(x_dict, n_classes, dropout, reuse, is_training):
    # Define a scope for reusing the variables
    with tf.variable_scope('ConvNet', reuse=reuse):
        # TF Estimator input is a dict, in case of multiple inputs
        x = x_dict

        # MNIST data input is a 1-D vector of 784 features (28*28 pixels)
        # Reshape to match picture format [Height x Width x Channel]
        # Tensor input become 4-D: [Batch Size, Height, Width, Channel]
        x = tf.reshape(x, shape=[-1, 28, 28, 1])

        # Convolution Layer with 32 filters and a kernel size of 5
        conv1 = tf.layers.conv2d(x, 32, 5, activation=tf.nn.relu)
        # Max Pooling (down-sampling) with strides of 2 and kernel size of 2
        conv1 = tf.layers.max_pooling2d(conv1, 2, 2)

        # Convolution Layer with 64 filters and a kernel size of 3
        conv2 = tf.layers.conv2d(conv1, 64, 3, activation=tf.nn.relu)
        # Max Pooling (down-sampling) with strides of 2 and kernel size of 2
        conv2 = tf.layers.max_pooling2d(conv2, 2, 2)

        # Flatten the data to a 1-D vector for the fully connected layer
        fc1 = tf.contrib.layers.flatten(conv2)

        # Fully connected layer (in tf contrib folder for now)
        fc1 = tf.layers.dense(fc1, 1024)
        # Apply Dropout (if is_training is False, dropout is not applied)
        fc1 = tf.layers.dropout(fc1, rate=dropout, training=is_training)

        # Output layer, class prediction
        out = tf.layers.dense(fc1, n_classes)

    return out


# Define the model function (following TF Estimator Template)
def model_fn(features, labels, mode):
    # Build the neural network
    # Because Dropout have different behavior at training and prediction time, we
    # need to create 2 distinct computation graphs that still share the same weights.
    logits_train = conv_net(features, num_classes, dropout, reuse=False,
                            is_training=True)
    logits_test = conv_net(features, num_classes, dropout, reuse=True,
                           is_training=False)

    
    # Predictions
    pred_classes = tf.argmax(logits_test, axis=1)
    pred_probas = tf.nn.softmax(logits_test)

    # If prediction mode, early return
    if mode == tf.estimator.ModeKeys.PREDICT:
        return tf.estimator.EstimatorSpec(mode, predictions=pred_classes)

    # --------------------------------------------------------------------------
    # Calculating loss 
    # --------------------------------------------------------------------------
    loss = tf.reduce_mean(tf.nn.sparse_softmax_cross_entropy_with_logits(
        logits=logits_train, labels=tf.cast(labels, dtype=tf.int32)))
    
    train_ops = None
    acc_op = None

    # --------------------------------------------------------------------------
    # Optimize
    # --------------------------------------------------------------------------
    if mode == tf.estimator.ModeKeys.TRAIN:
        global_step = tf.train.get_global_step()
        learning_rate = tf.train.exponential_decay(
            start_lr, global_step=global_step,
            decay_steps=100, decay_rate=1.30)
        optimizer = tf.train.AdamOptimizer(learning_rate)
        train_ops = optimizer.minimize(loss, global_step=global_step)
        tf.summary.scalar("learning_rate", learning_rate)
        tf.summary.scalar("current_step", global_step)
        tf.summary.scalar("loss", loss)
        
    
    # Evaluate the accuracy of the model
    if mode == tf.estimator.ModeKeys.EVAL:
        acc_op = tf.metrics.accuracy(labels=labels, predictions=pred_classes)
        return tf.estimator.EstimatorSpec(mode, loss=loss, eval_metric_ops={'accuracy': acc_op})
        

    # TF Estimators requires to return a EstimatorSpec, that specify
    # the different ops for training, evaluating, ...
    estim_specs = tf.estimator.EstimatorSpec(
        mode=mode,
        predictions=pred_classes,
        loss=loss,
        train_op=train_ops)

    return estim_specs

# Build the Estimator
model = tf.estimator.Estimator(model_fn)

# Define the input function for training
def train_data():
    data = dataset.train(data_dir)
    data = data.cache()
    data = data.shuffle(1000).repeat().batch(batch_size)
    return data

# Train the Model
model.train(train_data, steps=training_steps)

# Evaluate the Model
# Define the input function for evaluating
def eval_data():
    data = dataset.test(data_dir)
    data = data.cache()
    data = data.shuffle(1000).repeat().batch(batch_size)
    return data

# Use the Estimator 'evaluate' method
e = model.evaluate(eval_data, steps=(0.1*training_steps))

print("The test accuracy of the network: ", e['accuracy'])


