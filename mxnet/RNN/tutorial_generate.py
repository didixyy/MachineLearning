#coding=gbk
#coding=utf-8
#-*- coding: UTF-8 -*-
import mxnet as mx
import numpy as np
import codecs
import random
import bisect
# set up logging
import logging
reload(logging)
logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.DEBUG, datefmt='%I:%M:%S')
from lstm import lstm_unroll, lstm_inference_symbol
from bucket_io import BucketSentenceIter
from rnn_model import LSTMInferenceModel
# Read from doc
def read_content(path):
    with open(path) as ins:
        content = ins.read()
        return content

def read_chinese_content(path):
    with codecs.open(path,encoding='utf-8') as ins:
        content = ins.read()
    return content.replace('\r','')[1:]

# Build a vocabulary of what char we have in the content
def build_vocab(path):
    content = read_content(path)
    content = list(content)
    idx = 1 # 0 is left for zero-padding
    the_vocab = {}
    for word in content:
        if len(word) == 0:
            continue
        if not word in the_vocab:
            the_vocab[word] = idx
            idx += 1
    return the_vocab

def build_chinese_vocab(path):
    content = read_chinese_content(path)
    content = list(content)
    idx = 1 # 0 is left for zero-padding
    the_vocab = {}
    for word in content:
        if len(word) == 0 or word == "\n" or word == '\r':
            continue
        if not word in the_vocab:
            the_vocab[word] = idx
            idx += 1
    return the_vocab

# We will assign each char with a special numerical id
def text2id(sentence, the_vocab):
    words = list(sentence)
    words = [the_vocab[w] for w in words if len(w) > 0]
    return words


# Evaluation
def Perplexity(label, pred):
    label = label.T.reshape((-1,))
    loss = 0.
    for i in range(pred.shape[0]):
        loss += -np.log(max(1e-10, pred[i][int(label[i])]))
    return np.exp(loss / label.size)

# import os
# data_url = "http://data.mxnet.io/mxnet/data/char_lstm.zip"
# os.system("wget %s" % data_url)
# os.system("unzip -o char_lstm.zip")

# The batch size for training
batch_size = 32
# We can support various length input
# For this problem, we cut each input sentence to length of 129
# So we only need fix length bucket
buckets = [10]
# hidden unit in LSTM cell
num_hidden = 512
# embedding dimension, which is, map a char to a 256 dim vector
num_embed = 256
# number of lstm layer
num_lstm_layer = 3

# we will show a quick demo in 2 epoch
# and we will see result by training 75 epoch
num_epoch = 100
# learning rate
learning_rate = 0.01
# we will use pure sgd without momentum
momentum = 0.0

filePath = "./shige1.txt"#"./obama.txt"
# build char vocabluary from input
#vocab = build_vocab(filePath)
vocab = build_chinese_vocab(filePath)


# helper strcuture for prediction
def MakeRevertVocab(vocab):
    dic = {}
    for k, v in vocab.items():
        dic[v] = k
    return dic

# make input from char
def MakeInput(char, vocab, arr):
    idx = vocab[char]
    tmp = np.zeros((1,))
    tmp[0] = idx
    arr[:] = tmp

# helper function for random sample
def _cdf(weights):
    total = sum(weights)
    result = []
    cumsum = 0
    for w in weights:
        cumsum += w
        result.append(cumsum / total)
    return result

def _choice(population, weights):
    assert len(population) == len(weights)
    cdf_vals = _cdf(weights)
    x = random.random()
    idx = bisect.bisect(cdf_vals, x)
    return population[idx]

# we can use random output or fixed output by choosing largest probability
def MakeOutput(prob, vocab, sample=False, temperature=1.):
    if sample == False:
        idx = np.argmax(prob, axis=1)[0]
    else:
        fix_dict = [""] + [vocab[i] for i in range(1, len(vocab) + 1)]
        scale_prob = np.clip(prob, 1e-6, 1 - 1e-6)
        rescale = np.exp(np.log(scale_prob) / temperature)
        rescale[:] /= rescale.sum()
        return _choice(fix_dict, rescale[0, :])
    try:
        char = vocab[idx]
    except:
        char = ''
    return char

# load from check-point
_, arg_params, __ = mx.model.load_checkpoint("tutorial", num_epoch)

# build an inference model
model = LSTMInferenceModel(num_lstm_layer, len(vocab) + 1,
                           num_hidden=num_hidden, num_embed=num_embed,
                           num_label=len(vocab) + 1, arg_params=arg_params, ctx=mx.gpu(), dropout=0.2)

# generate a sequence of 1200 chars

seq_length = 50
input_ndarray = mx.nd.zeros((1,))
revert_vocab = MakeRevertVocab(vocab)
# Feel free to change the starter sentence
output =revert_vocab[np.random.randint(1,len(revert_vocab)-1)]#'The joke'#
random_sample = True
new_sentence = True

ignore_length = len(output)

for i in range(seq_length):
    if i <= ignore_length - 1:
        MakeInput(output[i], vocab, input_ndarray)
    else:
        MakeInput(output[-1], vocab, input_ndarray)
    prob = model.forward(input_ndarray, new_sentence)
    new_sentence = False
    next_char = MakeOutput(prob, revert_vocab, random_sample)
    if next_char == '':
        new_sentence = True
    if i >= ignore_length - 1:
        output += next_char

print output
