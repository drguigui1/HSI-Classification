import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

def remove_unclassified(preds, labels):
    '''
    Remove unclassified data on predictions (label == 0)
    Usefull for Clustering Unsupervised algorithm

    params
    ----------
    preds: Predictions array of shape (n_pixels_row, n_pixels_col)

    labels: Labels array of shape (n_pixels_row, n_pixels_col)


    returns
    ----------
    final_preds: Final predictions without unclassified data of shape (n_pixels_row, n_pixels_col)
    '''
    preds_cpy = preds.copy()
    zeros_idx = np.argwhere(labels.flatten() == 0).flatten()
    preds_cpy += 1
    preds_flatten = preds_cpy.flatten()
    preds_flatten[zeros_idx] = 0
    final_preds = preds_flatten.reshape((preds.shape[0], preds.shape[1]))
    return final_preds

def remove_unclassified_input(X, labels):
    '''
    Remove unclassified data from the input (label == 0)

    params
    ----------
    X: Input data, array of shape (n_samples, n_features)

    labels: Labels array of shape (n_pixels_row, n_pixels_col)


    returns
    ----------
    new_X: New data with classified data of shape (n_samples_usefull, n_features)

    arr_idx: Indexes of usefull data in the input image, array of shape (n_samples_usefull,)
    '''
    X_cpy = X.copy()
    idx = np.argwhere(labels.flatten() == 0).flatten()
    mask = np.ones(labels.flatten().shape, dtype=bool)
    mask[idx] = False
    arr = np.arange(labels.size)
    return X_cpy[mask], arr[mask]

def get_number_components(X):
    # first PCA with by keeping all features
    print("Fitting the PCA")
    pca_model = PCA()
    pca_model.fit(X)
    var_cumsum = pca_model.explained_variance_ratio_.cumsum()
    return len(var_cumsum[var_cumsum <= 0.9991])

def extract_features(X, n_components):
    '''
    Extract features using PCA

    params
    ----------
    X: Input data of shape (n_samples, n_features)

    n_components: Number of components to extract (int)


    returns
    ----------
    reduced_X: New data with few dimensions, after features extraction
        array of shape (n_samples, n_components)
    '''
    pca_model = PCA(n_components=n_components)
    pca_model.fit(X)
    return pca_model.transform(X)

def copy_without_outlier(X, outlier_pos):
    '''
    Copy data without outliers
    Outliers can be computed using RX anomaly detector for example

    params
    ----------
    X: Input data of shape (n_pixels_row, n_pixels_col)

    outlier_pos: Outlier positions array of shape (n_outliers,)


    returns
    ----------
    new_X: New data without outliers of shape (n_pixels_row-n_outliers, n_pixels_col-n_outliers)
    '''
    l = []
    X_positions = []
    for i in range(X.shape[0]):
        for j in range(X.shape[1]):
            if [i, j] in outlier_pos:
                continue
            l.append(X[i, j])
            X_positions.append([i, j])
    return np.array(l), np.array(X_positions)

def rebuild_data_with_outliers(salinas_preds, X_positions, outlier_pos, target_shape):
    preds = np.empty(target_shape)
    for i in range(salinas_preds.shape[0]):
        pos = X_positions[i]
        preds[pos[0], pos[1]] = salinas_preds[i]
    for j in range(len(outlier_pos)):
        pos = outlier_pos[j]
        preds[pos[0], pos[1]] = 0
    return preds

def get_label(labels, x):
    return np.where(labels == x, labels, 0)

def compute_labels_correspondence(labels, preds, n_cluster):
    l2, c2 = np.unique(labels, return_counts=True)
    c2 = c2.argsort()
    l, c = np.unique(preds, return_counts=True)
    c = c.argsort()

    res_labels = labels.copy().flatten()
    res_preds = preds.copy().flatten()

    j = 0
    offset = len(l2) - len(l)

    for i in range(n_cluster):
        if i in l:
            idx = np.argwhere(preds.flatten() == l[c[j]]).flatten()
            res_preds[idx] = j + offset + 1
            j += 1

        idx2 = np.argwhere(labels.flatten() == l2[c2[i]]).flatten()
        res_labels[idx2] = i + 1

    zeros_idx = np.argwhere(labels.flatten() == 0).flatten()
    res_preds[zeros_idx] = 0
    res_preds = res_preds.reshape((preds.shape[0], preds.shape[1]))
    res_labels = res_labels.reshape((labels.shape[0], labels.shape[1]))

    return res_labels, res_preds

def shuffle(X, labels):
    # Copy arrays
    X_cpy = X.copy()
    labels_cpy = labels.copy()

    # Shuffle idx
    arr_idx = np.arange(labels.shape[0])
    np.random.shuffle(arr_idx) # in place
    arr_arange = np.arange(labels.shape[0])

    # Shuffle array
    X_cpy[arr_arange] = X_cpy[arr_idx]
    labels_cpy[arr_arange] = labels_cpy[arr_idx]
    return X_cpy, labels_cpy, arr_idx

def split_x_train_test(X_shuffle, count, labels, labels_argsort, size, train_split=0.75):
    sum_ = 0
    x_train = np.empty(size)
    x_test = np.empty(size)

    y_train = np.array([])
    y_test = np.array([])

    cols = ['Class', 'Nb samples train', 'Nb samples test', 'Nb total samples']
    df = pd.DataFrame(columns=cols)

    for cluster in labels:
        idx = int(count[cluster] * train_split)

        x_train = np.vstack((x_train, X_shuffle[labels_argsort[sum_:sum_+idx]]))
        x_test = np.vstack((x_test, X_shuffle[labels_argsort[sum_+idx: sum_ + count[cluster]]]))

        y_train = np.hstack((y_train, np.full((idx), cluster)))
        y_test = np.hstack((y_test, np.full((count[cluster] - idx), cluster)))

        df.loc[cluster] = [cluster, idx, count[cluster] - idx, count[cluster]]
        sum_ += count[cluster]

    display(df.T)
    return x_train, x_test, y_train, y_test


def calculate_mean_score(labels, x_labels, y_labels, model):
    mean_score = 0

    cols = ['Class', 'Nb samples', 'Score']
    df = pd.DataFrame(columns=cols)
    df = df.astype({'Class': int, 'Nb samples': int, 'Score': float})

    for cluster in labels:
        idxs = np.argwhere(y_labels == cluster).flatten()
        score = model.score(x_labels[idxs], y_labels[idxs])

        df.loc[cluster] = [int(cluster), int(y_labels[idxs].size), score]
        mean_score += score

    display(df.T)
    return mean_score / labels.size
