import cv2
from matplotlib import pyplot as plt
import numpy as np
from skimage import morphology, measure
from scipy.spatial.distance import cdist as cdist

def template_matching(img: np.array,
                      template: np.array,
                      template_max_y: float,
                      bottom: bool = True) -> tuple:
    """Find the position of the template in image

    Parameters
    ----------

    img, template: array_like
        the image and the template image

    template_max_y: int
        the maximum of minimum position to match the template

    bottom: bool
        match template from 0 - template_max_y row if False,
        match template from template_max_y - img.shape[0] row if True

    Returns
    -------

    bottom_left, top_right: array_like
        the bottom left and top right pixel coordinate of template in img

    """

    methods = ['cv2.TM_CCOEFF', 'cv2.TM_CCOEFF_NORMED', 'cv2.TM_CCORR',
            'cv2.TM_CCORR_NORMED', 'cv2.TM_SQDIFF', 'cv2.TM_SQDIFF_NORMED']
    h, w = template.shape
    method = eval(methods[0])
    img_min = np.min(img)
    img_max = np.max(img)
    template_min = np.min(template)
    template_max = np.max(template)
    min_val = min(template_min, img_min)
    max_val = max(template_max, img_max)
    template = (255*(template - min_val)/(max_val - min_val)).astype(np.uint8)
    img = (255*(img - min_val)/(max_val - min_val)).astype(np.uint8)
    if bottom:
        res = cv2.matchTemplate(img[template_max_y:,:],template,method)
    else:
        res = cv2.matchTemplate(img[:template_max_y,:],template,method)

    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
        bottom_left = min_loc
    else:
        bottom_left = max_loc
    if bottom:
        bottom_left = (bottom_left[0], bottom_left[1]+template_max_y)
    top_right = (bottom_left[0]+w, bottom_left[1]+h)
    '''fig, ax = plt.subplots()
    ax.imshow(img, cmap='gray')
    rect = matplotlib.patches.Rectangle(bottom_left,w, h, linewidth=1, edgecolor='r', facecolor='none')
    ax.add_patch(rect)
    plt.show()'''
    return np.array(bottom_left), np.array(top_right)

def blob_detection(img: np.array) -> tuple:
    """Detect atoms with BlobDetector from cv2

    Parameters
    ----------

    img: array_like
        the image

    Return
    ------

    atoms_pixel, atoms_size: array_like
        the atom coordinates and sizes in pixel

    """
    ###set BlobDetector params https://learnopencv.com/blob-detection-using-opencv-python-c/
    img = np.array(img)
    img = (255*((img-np.min(img))/(np.max(img)-np.min(img)))).astype('uint8')
    #kernel = np.ones((3,3),np.float32)/9
    #img = cv2.filter2D(img,-1,kernel)
    #pdb.set_trace()
    #plt.imshow(img)
    params = cv2.SimpleBlobDetector_Params()
    params.filterByInertia = False
    params.filterByCircularity = False
    params.filterByConvexity = False
    #params.minInertiaRatio = 0.7
    params.maxThreshold = 255
    params.minThreshold = 40
    params.blobColor = 255
    params.filterByArea = True
    params.minArea = 10
    params.maxArea = 120
    params.minDistBetweenBlobs = 5
    ###create BlobDetector
    detector = cv2.SimpleBlobDetector_create(params)
    ###Detect
    keypoints = detector.detect(img)
    #im_with_keypoints = cv2.drawKeypoints(img, keypoints, np.array([]), (0,0,255), cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)

    atoms_pixel = []
    atoms_size = []
    for k in keypoints:
        atoms_pixel.append(k.pt)
        atoms_size.append(k.size)
    atoms_pixel = np.array(atoms_pixel)
    atoms_size = np.array(atoms_size)
    return atoms_pixel, atoms_size

def atom_detection(img: np.array,
                   bottom_left: np.array,
                   top_right: np.array) -> tuple:
    """Detect atoms by combining blob_detection and get_region_centroids outside the template region

    Parameters
    ----------

    img : array_like
        the image

    bottom_left, top_right : array_like
        the bottom left and top right pixel coordinates of the template

    Returns
    -------

    atoms_pixel : array_like
        the atom coordinates in pixel

    """

    atom_pixel, atom_size = blob_detection(img)
    max_pos = get_region_centroids(img)
    s = np.any(cdist(atom_pixel, max_pos)<1*atom_size.reshape(atom_size.shape[0],1),axis = 1)
    #print('updated atom detection')
    #if len(s)!=len(atom_pixel) or len(s)!=max_pos:
    #    s = np.any(cdist(atom_pixel, max_pos)<1*atom_size.reshape(atom_size.shape[0],1),axis = 1)
    atom_pixel = atom_pixel[s,:]
    filter = np.any((atom_pixel-bottom_left)*(atom_pixel - top_right)>0, axis=-1)
    atom_pixel = atom_pixel[filter]
    return atom_pixel

def pixel_to_nm(pixel: np.array,
                img: np.array,
                offset_nm: np.array,
                len_nm: np.array) -> np.array:
    """Convert pixel coordinates to STM coordinates in nm

    Parameters
    ----------

    pixel : array_like
        pixel coordinates

    img : array_like
        image

    offset_nm : array_like
        XY offset in nm

    len_nm : array_like
        XY length of the image in nm

    Returns
    -------

    nm : array_like
        STM coordinates in nm
    """
    offsets = np.array([offset_nm[0]-len_nm[0]/2, offset_nm[1]])
    nm_per_pixel = np.array([len_nm[0]/img.shape[0],len_nm[1]/img.shape[1]])
    nm = pixel*nm_per_pixel + offsets
    return nm

def get_atom_coordinate_nm(img: np.array,
                           offset_nm: np.array,
                           len_nm: np.array,
                           template: np.array,
                           template_max_y: np.array,
                           bottom: bool = True) -> tuple:
    """Use template_matching, atom_detection, and pixel_to_nm
    to get the STM coordinates of atoms in nm

    Parameters
    ----------

    img: array_like
        image

    offset_nm: array_like
        XY offset in nm

    len_nm: array_like
        XY length of the image in nm

    template: array_like
        the template image

    template_max_y: int
        the maximum of minimum position to match the template

    bottom: bool
        match template from 0 - template_max_y row if False
        match template from template_max_y - img.shape[0] row if True

    Returns
    -------

    atom_nm : array_like
        STM coordinates of the atoms in nm

    (atom_nm - bottom_left_nm) : array_like

    bottom_left_nm : array_like
        the bottom left STM coordinates of the template in nm

    wh : array_like
        the width and height of the template in nm

    """
    if template is not None:
        args = img, template,template_max_y, bottom
        bottom_left_pixel, top_right_pixel = template_matching(*args)
        atom_pixel = atom_detection(img, bottom_left_pixel, top_right_pixel)
        bottom_left_nm = pixel_to_nm(bottom_left_pixel, img, offset_nm, len_nm)
        top_right_nm = pixel_to_nm(top_right_pixel, img, offset_nm, len_nm)
        wh = top_right_nm - bottom_left_nm
        atom_nm = pixel_to_nm(atom_pixel, img, offset_nm, len_nm)[0]
    else:
        atom_pixel = atom_detection(img, np.array([0,0]), np.array([0,0]))
        bottom_left_nm, wh = np.array([0,0]), np.array([0,0])
        atom_nm = pixel_to_nm(atom_pixel, img, offset_nm, len_nm)
        dist = cdist(atom_nm.reshape((-1,2)), (offset_nm+np.array([0, 0.5*len_nm[0]])).reshape((-1,2)))
        atom_nm = atom_nm[np.argmin(dist),:]
    return atom_nm, (atom_nm - bottom_left_nm), bottom_left_nm, wh

def get_atom_coordinate_nm_with_anchor(img: np.array,
                                       offset_nm: np.array,
                                       len_nm: np.array,
                                       anchor_nm: np.array,
                                       obstacle_list: bool = None) -> tuple:
    """Get STM coordinates (nm) of atoms and anchors that are not in the obstacle_list using atom_detection, and pixel_to_nm

    Parameters
    ----------

    img: array_like
        image

    offset_nm: array_like
        XY offset in nm

    len_nm: array_like
        XY length of the image in nm

    anchor_nm: array_like
        the STM coordinates of anchors

    obstacle_list: array_like
        the STM coordinates of obstacles

    Return
    ------

    atom_nm: array_like
        STM coordinates of the atoms in nm

    anchor_nm_: array_like
        STM coordinates of the anchors in nm

    """
    atom_pixel = atom_detection(img, np.array([0,0]), np.array([0,0]))
    atoms_nm = pixel_to_nm(atom_pixel, img, offset_nm, len_nm)
    if anchor_nm is not None:
        dist = cdist(atoms_nm.reshape((-1,2)), anchor_nm.reshape((-1,2)))
        anchor_nm_ = atoms_nm[np.argmin(dist),:]
    else:
        anchor_nm_ = None
    if obstacle_list is not None:
        i = np.argmax(cdist(atoms_nm, obstacle_list).min(axis = 1))
        atom_nm = atoms_nm[i,:]
    else:
        center = offset_nm + np.array([0, 0.5*len_nm[0]])
        dist = cdist(atoms_nm.reshape((-1,2)), center.reshape((-1,2)))
        atom_nm = atoms_nm[np.argmin(dist),:]
    return atom_nm, anchor_nm_

def get_all_atom_coordinate_nm(img: np.array,
                               offset_nm: np.array,
                               len_nm: np.array) -> np.array:
    """Get STM coords (nm) of multiple atoms using atom_detection, and pixel_to_nm

    Parameters
    ----------

    img : array_like
        image

    offset_nm : array_like
        XY offset in nm

    len_nm : array_like
        XY length of the image in nm

    Returns
    -------

    atom_nm : array_like
        STM coordinates of the atoms in nm

    """
    atom_pixel = atom_detection(img, np.array([0,0]), np.array([0,0]))
    atom_nm = pixel_to_nm(atom_pixel, img, offset_nm, len_nm)
    return atom_nm

def subtract_plane(im: np.array):
    """
    Plane subtract data

    Parameters
    ----------

    im : array_like
        2D array of z values

    Returns:
    --------

    im : array_like
        2D array of z values with planar fit subtracted

    """
    xPix, yPix = im.shape
    X1, X2 = np.mgrid[:xPix, :yPix]
    nxny = xPix*yPix
    X = np.hstack((np.reshape(X1, (nxny, 1)), np.reshape(X2, (nxny, 1))))
    X = np.hstack((np.ones((nxny, 1)), X))
    YY = np.reshape(im, (nxny,1))
    inv = np.linalg.pinv(np.dot(X.transpose(), X))
    theta = np.dot(np.dot(inv, X.transpose()), YY)
    plane = np.reshape(np.dot(X, theta), (xPix, yPix))
    im = im.astype(float)
    im -= np.array(plane).astype(float)
    return im

def get_region_centroids(im: np.array,
                         diamond_size: int=3,
                         sigmaclip: float=3,
                         show: bool=False):
    """Get pixels with height above sigma_clip standard deviations of the mean

    Parameters
    ----------

    im : array_like

    diamond_size : int

    sigmaclip : float

    show : bool

    Returns
    -------

    c : array_like
        list of centroid positions [[x1, y1], [x2, y2], ...]

    """
    im = subtract_plane(im)
    #plt.imshow(im)
    #plt.show()
    diamond = morphology.diamond(diamond_size)
    print(im,  sigmaclip*np.std(im))
    maxima = morphology.h_maxima(im, sigmaclip*np.std(im))
    r = morphology.binary_dilation(maxima, selem=diamond)
    #plt.imshow(maxima)
    xim = morphology.label(r)
    regions = measure.regionprops(xim)
    if show:
        plt.figure()
        plt.imshow(xim)
        plt.show()
       # plt.close()
    regions_areas = [r.area for r in regions]
    regions_area_max = max(regions_areas)

    # all regions might be same size, in which case we're spot on
    allsame = np.all([r==regions_areas[0] for r in regions_areas])

    # if we have the 'background' as a region, remove it
    # if not allsame:
    #     regions = [r for r in regions if (r.area != regions_area_max)]

    c = [list(reversed(r.centroid)) for r in regions]

    # remove centroids close to the edge
    return c
