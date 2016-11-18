# coding=utf-8

from keras.models import load_model
from keras.models import Sequential
from keras.layers import Input, Dense, Convolution2D, MaxPooling2D, UpSampling2D, Dropout, Activation, Flatten
from keras.models import Model
from keras.optimizers import SGD
from keras.utils import np_utils
from keras.callbacks import EarlyStopping
from sklearn.cluster import KMeans
from sklearn.neighbors import KNeighborsClassifier
from sklearn.externals import joblib
import numpy as np
import parser as ps
import time
import cPickle as pickle
import sys

CLUSTER = 'knn'

nb_classes = 10
noise_factor = 0.2
nb_epoch = 300
nb_epoch2 = 150
batch_size = 128
batch_size2 = 1280
validPercent = 10
SEMI_TIMES = 3

LOAD_FLAG = True
LOAD_MODEL_FILE = "trained_model"
encoder_model = 'encoder_model'
autoencoder_model = 'autoencoder_model'
MODEL_FILE = sys.argv[2]
dataPath = sys.argv[1]

# slow data
# labels[0-9][0-499][0-3071]
ts = time.time()
print("Loading labeled data......")
labels = pickle.load(open(dataPath + 'all_label.p', "rb"))
X_train, Y_train = ps.parseTrain(labels, nb_classes, 'rgb')
# print('labels[9][499]', labels[9][499][1023], labels[9][499][2047], labels[9][499][3071])
# print('X_train[4999][31][31]', X_train[4999][31][31])
te = time.time()
print(te-ts, 'secs')

# unlabels[0-44999][0-3071]
ts = time.time()
print("Loading unlabeled data......")
unlabels = pickle.load(open(dataPath + 'all_unlabel.p', "rb"))
X_unlabel, Y_unlabel = ps.parseUnlabel(unlabels, nb_classes, 'rgb')
# print('unlabels[44999]', unlabels[44999][1023], unlabels[44999][2047], unlabels[44999][3071])
# print('X_unlabel[44999][31][31]', X_unlabel[44999][31][31])
te = time.time()
print(te-ts, 'secs')

# tests['ID'][0-9999], tests['data'][0-9999], tests['labels'][0-9999]
ts = time.time()
print("Loading test data......")
tests = pickle.load(open(dataPath + 'test.p', "rb"))
X_test, Y_test = ps.parseTest(tests, nb_classes, 'rgb')
# print('tests["data"][0]', tests["data"][0][0], tests["data"][0][1024], tests["data"][0][2048])
# print('X_test[0][0][0]', X_test[0][0][0])
te = time.time()
print(te-ts, 'secs')

# fast data
# ts = time.time()
# (X_train, Y_train) = pickle.load(open("fast_all_label", "rb"))
# (X_unlabel, Y_unlabel) = pickle.load(open("fast_all_unlabel", "rb"))
# (X_test, Y_test) = pickle.load(open("fast_test", "rb"))
# te = time.time()
# print('Loading data......', te-ts, 'secs')
# print('shape: X_train', X_train.shape, 'Y_train', Y_train.shape, 'X_test', X_test.shape, 'Y_test', Y_test.shape)
# '''(5000, 32, 32, 3) (5000, 10) (10000, 32, 32, 3) (10000, 10) (45000, 32, 32, 3) (45000, 10)'''

X_train = X_train.astype('float32') / 255.
X_unlabel = X_unlabel.astype('float32') / 255.
X_test = X_test.astype('float32') / 255.
X_train_prime = np.concatenate((X_train, X_unlabel), axis=0)
X_train_prime = np.concatenate((X_train_prime, X_test), axis=0)
# X_train = np.reshape(X_train, (len(X_train), 32, 32, 3))
# X_test = np.reshape(X_test, (len(X_test), 32, 32, 3))

# encoder
input_img = Input(shape=(32, 32, 3))
x = Convolution2D(64, 3, 3, activation='relu', border_mode='same')(input_img)
x = MaxPooling2D((2, 2), border_mode='same')(x)
x = Convolution2D(32, 3, 3, activation='relu', border_mode='same')(x)
encoded = MaxPooling2D((2, 2), border_mode='same')(x)

# decoder
x = Convolution2D(64, 3, 3, activation='relu', border_mode='same')(encoded)
x = UpSampling2D((2, 2))(x)
x = Convolution2D(32, 3, 3, activation='relu', border_mode='same')(x)
x = UpSampling2D((2, 2))(x)
decoded = Convolution2D(3, 3, 3, activation='sigmoid', border_mode='same')(x)

encoder = Model(input=input_img, output=encoded)
autoencoder = Model(input_img, decoded)
autoencoder.compile(optimizer='adam', loss='binary_crossentropy')
earlystopping = EarlyStopping(monitor='val_loss', patience=20, verbose=1)
print(autoencoder.summary())

if noise_factor >= 0: 
    X_train_noisy = X_train_prime + noise_factor * np.random.normal(loc=0.0, scale=1.0, size=X_train_prime.shape) 
    X_test_noisy = X_test + noise_factor * np.random.normal(loc=0.0, scale=1.0, size=X_test.shape) 
    X_train_noisy = np.clip(X_train_noisy, 0., 1.)
    X_test_noisy = np.clip(X_test_noisy, 0., 1.)
    autoencoder.fit(X_train_noisy, X_train_prime,
                nb_epoch=nb_epoch,
                batch_size=batch_size,
                shuffle=True,
                validation_data=(X_test_noisy, X_test))
else:
    autoencoder.fit(X_train_prime, X_train_prime,
                nb_epoch=nb_epoch,
                batch_size=batch_size,
                shuffle=True,
                validation_data=(X_test, X_test))

encoder.save(encoder_model)
autoencoder.save(autoencoder_model)

labeled_encoded_imgs = encoder.predict(X_train)
encoded_imgs = encoder.predict(X_train_prime)
decoded_imgs = autoencoder.predict(X_test)

if CLUSTER == 'kmeans':
    ### k-means alogrithm ###
    print "=== start K-means ==="
    # count k-means' centroids
    labeled_mean = ps.countMean(labeled_encoded_imgs, Y_train, nb_classes)
    print 'labeled_mean.shape', labeled_mean.shape, 'encoded_imgs.shape', encoded_imgs.shape
    # reshape to appropriate size
    labeled_mean_r = ps.reshape(labeled_mean)
    encoded_imgs_r = ps.reshape(np.concatenate((encoded_imgs,labeled_encoded_imgs),axis=0))
    print 'labeled_mean_r.shape', labeled_mean_r.shape, 'encoded_imgs_r.shape', encoded_imgs_r.shape
    kmeans = KMeans(n_clusters=nb_classes, init=labeled_mean_r).fit(encoded_imgs_r)
    joblib.dump(kmeans, 'kmeans.pkl')
elif CLUSTER == 'knn':
    ### KNN algorithm ###
    print "=== start KNN ==="
    knn = KNeighborsClassifier(n_neighbors=7, weights='distance')
    X_train_r = ps.reshape(labeled_encoded_imgs)
    Y_train_r = ps.raw(Y_train)
    Y_train_r = Y_train_r.reshape(len(Y_train_r))
    print 'X_train_r.shape', X_train_r.shape, 'Y_train_r.shape', Y_train_r.shape
    knn.fit(X_train_r, Y_train_r)
    joblib.dump(knn, 'knn.pkl')

# add model
model = Sequential()
if LOAD_FLAG:
    model = load_model(LOAD_MODEL_FILE)
else:
    model.add(Convolution2D(32, 3, 3, border_mode='same', input_shape=X_train.shape[1:]))
    model.add(Activation('relu'))
    model.add(Convolution2D(32, 3, 3))
    model.add(Activation('relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))
    model.add(Dropout(0.5))

    model.add(Convolution2D(64, 3, 3, border_mode='same'))
    model.add(Activation('relu'))
    model.add(Convolution2D(64, 3, 3))
    model.add(Activation('relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))
    model.add(Dropout(0.5))

    model.add(Flatten())
    model.add(Dense(512))
    model.add(Activation('relu'))
    model.add(Dropout(0.5))
    model.add(Dense(nb_classes))
    model.add(Activation('softmax'))

    sgd = SGD(lr=0.005, decay=1e-6, momentum=0.9, nesterov=True)
    model.compile(loss='categorical_crossentropy', optimizer=sgd, metrics=['accuracy'])

# predict
unlabeled_imgs = encoder.predict(X_unlabel)
print "unlabeled_imgs.shape", unlabeled_imgs.shape
unlabeled_imgs_r = ps.reshape(unlabeled_imgs)
print "unlabeled_imgs_r.shape", unlabeled_imgs_r.shape
test_imgs = encoder.predict(X_test)
print "test_imgs.shape", test_imgs.shape
test_imgs_r = ps.reshape(test_imgs)
print "test_imgs_r.shape", test_imgs_r.shape
X_train_auto_prime = np.concatenate((unlabeled_imgs_r, test_imgs_r), axis=0)
Y_train_auto_prime = np.concatenate((Y_unlabel, Y_test), axis=0)
if CLUSTER == 'kmeans':
    predict = kmeans.predict(X_train_auto_prime)
elif CLUSTER == 'knn':
    predict = knn.predict_proba(X_train_auto_prime)
print predict
print 'Y_train_auto_prime[10], predict[10]', Y_train_auto_prime[10], predict[10]
X_train_auto_prime = np.concatenate((X_unlabel, X_test),axis=0)
if CLUSTER == 'kmeans':
    for i in range(len(predict)):
        Y_train_auto_prime[i, int(predict[i])] = 1
elif CLUSTER == 'knn':
    (X_train_auto_prime, Y_train_auto_prime) = ps.parseAuto(X_train_auto_prime, Y_train_auto_prime, predict, threshold=0.8)
print 'Y_train_auto_prime[10], predict[10]', Y_train_auto_prime[10], predict[10]

# start semi-supervised
X_train_auto = np.concatenate((X_train, X_train_auto_prime), axis=0)
Y_train_auto = np.concatenate((Y_train, Y_train_auto_prime), axis=0)

for i in range(SEMI_TIMES):
    print("semi iter", i)

    X_validation, Y_validation = ps.parseValidation(X_train_auto, Y_train_auto, nb_classes, len(X_train_auto)*validPercent/100, _type='rgb')
    model.fit(X_train_auto, Y_train_auto, batch_size=batch_size2, nb_epoch=nb_epoch2, validation_data=(X_validation, Y_validation), shuffle=True)

    print(" === Predicting unlabeled data...... === \n")
    Y_unlabel = model.predict(X_unlabel)
    Y_test = model.predict(X_test)
    print('Y_unlabel[1000]',Y_unlabel[1000])
    Y_unlabel = ps.to_categorical(Y_unlabel, nb_classes)
    Y_test = ps.to_categorical(Y_test, nb_classes)
    print('after ps Y_unlabel[1000]',Y_unlabel[1000])
    X_train_auto = np.concatenate((X_train, X_unlabel), axis=0)
    X_train_auto = np.concatenate((X_train_auto, X_test), axis=0)
    Y_train_auto = np.concatenate((Y_train, Y_unlabel), axis=0)
    Y_train_auto = np.concatenate((Y_train_auto, Y_test), axis=0)
    print(" === Saving model...... === \n")
    model.save(MODEL_FILE)

# save model
print(" === Saving model...... === \n")
model.save(MODEL_FILE)
