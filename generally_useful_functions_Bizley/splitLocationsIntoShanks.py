### the goal of this function is to take the horizontal location values of spikes and split them into specified shank numbers.
import numpy as np

def splitLocationsIntoShanks(data,BoundariesToUse=None):
    shankLabel = np.zeros(data.shape[0],dtype=int)
    if BoundariesToUse == None:
        BoundariesToUse = [[-100,100],[150,350],[400,600],[650,850]] # the default boundaries.
    for i,boundary in enumerate(BoundariesToUse):
        currentShankSet = (data[:,0] > boundary[0])&(data[:,0] < boundary[1])
        shankLabel[currentShankSet] = i
        pass
    return shankLabel