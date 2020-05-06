# -*- coding: utf-8 -*-
"""find-the-cluster-data-science.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1WVpc7Om9nFDLARcztlRxIXPa6yPe9hfg
"""

import numpy as np
import pandas as pd
import json
import re
import matplotlib.pyplot as plt

from google.colab import drive
from tqdm import tqdm
from geopy.distance import geodesic
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.svm import OneClassSVM
from sklearn.metrics import roc_auc_score
from sklearn.metrics import accuracy_score
get_ipython().run_line_magic('matplotlib', 'inline')

drive.mount('/content/gdrive')

"""# Data Cleaning and preprocessing"""

data = pd.read_csv('/content/gdrive/My Drive/find-the-cluster/clean_data_20200329.csv')
data['symptoms'] = data['symptoms'].str.replace("{}", '')
data = data[data.symptoms != ""]
data = data.dropna(subset=['symptoms', 'latitude', 'longitude'])
data = data[['symptoms', 'travel_history', 'latitude', 'longitude']]
data = data.reset_index()

features = set()
for i in tqdm(range(len(data))):
    data.at[i, 'symptoms'] = data.at[i, 'symptoms'].replace("\'", "\"")
    data.at[i, 'symptoms'] = re.findall('"([^"]*)"', data.at[i, 'symptoms'])
    for element in data.at[i, 'symptoms']:
        if 'others' not in element:
            features.add(element)
        # i will use only whether the patient have traveled or not for prediction
    if "[]" in data.at[i, 'travel_history']:
        data.at[i, 'travel_history'] = 0
    else:
        data.at[i, 'travel_history'] = 1
features.add('travel_history')
features.add('latitude')
features.add('longitude')

# add one hot encoding
print(features)
data.reset_index()
one_hot_encoded = pd.DataFrame()
for entry in features:
    one_hot_encoded[entry] = 0

for i in tqdm(range(len(data))):
    new_row = []
    for entry in features:
        if 'latitude' in entry:
            new_row.append(data.at[i, 'latitude'])
        elif 'longitude' in entry:
            new_row.append(data.at[i, 'longitude'])
        elif 'travel_history' in entry:
            new_row.append(data.at[i, 'travel_history'])
        # the symptoms (search)
        else:
            found = False
            for symptom in data.at[i, 'symptoms']:
                if entry in symptom:
                    new_row.append(1)
                    found = True
            if not found:
                new_row.append(0)
    one_hot_encoded = one_hot_encoded.append(pd.Series(new_row, index=one_hot_encoded.columns), ignore_index=True)

long_lat = one_hot_encoded[['latitude', 'longitude']]

one_hot_encoded

# run k-means multiple times with different values of k to determine the 
# optimal value using the elbow method

distortions = []
for i in range(1, 30):
    km = KMeans(
        n_clusters=i, init='random',
        n_init=10, max_iter=300,
        tol=1e-04, random_state=0
    )
    km.fit(long_lat)
    distortions.append(km.inertia_)

# plot
plt.plot(range(1, 30), distortions, marker='o')
plt.xlabel('Number of clusters')
plt.ylabel('Distortion')
plt.show()

# optimal number of clusters for this dataset is 4
# this may increase when our dataset increases in size
Kmean = KMeans(n_clusters=4)
Kmean.fit(long_lat)
centroids = Kmean.cluster_centers_
print(centroids)
plt.scatter(long_lat['latitude'], long_lat['longitude'], c= Kmean.labels_.astype(float), s=50, alpha=0.5)
plt.scatter(centroids[:, 0], centroids[:, 1], c='red', s=50)
plt.show()

def findDistance(coords_1,coords_2):
    return geodesic(coords_1, coords_2).km

for i,x in enumerate(centroids):
    col_name = f'cluster_distance_{i}'
    long_lat[col_name] = long_lat[['latitude','longitude']].apply(lambda arr: findDistance(arr, x),axis=1)
long_lat = long_lat.drop(['longitude', 'latitude'], axis = 1)
one_hot_encoded = one_hot_encoded.drop(['longitude', 'latitude'], axis = 1)
data = pd.concat([long_lat, one_hot_encoded], axis=1, sort=False)

data

X = data.to_numpy()
X = StandardScaler().fit_transform(X)
pca = PCA(n_components=29, svd_solver='full')
X = pca.fit_transform(X)
print(np.sum(pca.explained_variance_ratio_))
print(X.shape)
np.random.shuffle(X)
X_train, X_test = X[:550], X[550:]
print(X_train[0])
print(X_test[0])

"""# Building model"""

def sigmoid(x):
    return 1/(1 + np.exp(-x))

clf = OneClassSVM(gamma='auto').fit(X_train)

# dist is +ve for an inlier and -ve for an outlier
dist_from_boundary = clf.decision_function(X_test)
probs = sigmoid(dist_from_boundary)
pred = clf.predict(X_test)
true = np.ones(53)
print(dist_from_boundary)
print(probs)
print(pred)

accuracy_score(true, pred)
