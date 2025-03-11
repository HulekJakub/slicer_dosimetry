import numpy as np
import json
import math

def read_json(fname):
    # Load data from JSON file
    with open(fname, 'r') as f:
        data = json.load(f)
    return data

def rational_func(x, a, b, c):
    return (a + b*x) / (c + x)

def inverse_rational_func(x, a, b, c):
    # given channel value x calculates dose
    return (a - c*x) / (x - b) 
    
def omega(densities,coefs):
    def f(x):
        a,b,c = coefs[0]
        r = -np.log(rational_func(x, a, b, c))
        delta_r = densities[0]/r

        a,b,c = coefs[1]
        g = -np.log(rational_func(x, a, b, c))
        delta_g = densities[1]/g

        a,b,c = coefs[2]
        b = -np.log(rational_func(x, a, b, c))
        delta_b = densities[2]/b

        return (delta_r-delta_g)**2 + (delta_r-delta_b)**2 + (delta_b-delta_g)**2

    return f

def omega_with_normalizations(densities,coefs,norms):
    def f(x):
        x1 = norms[0]['dose']
        x2 = norms[1]['dose']
        
        a,b,c = coefs[0]
        cr1 = norms[0]['means'][0]
        cr2 = norms[1]['means'][0]
        cp1 = rational_func(x1, a, b, c)
        cp2 = rational_func(x2, a, b, c)
        c = rational_func(x, a, b, c)
        cn = (cr1-cr2)/(cp1-cp2)*(c-cp2) + cr2
        r = -np.log(cn)
        delta_r = densities[0]/r

        a,b,c = coefs[1]
        cr1 = norms[0]['means'][1]
        cr2 = norms[1]['means'][1]
        cp1 = rational_func(x1, a, b, c)
        cp2 = rational_func(x2, a, b, c)
        c = rational_func(x, a, b, c)
        cn = (cr1-cr2)/(cp1-cp2)*(c-cp2) + cr2
        g = -np.log(cn)
        delta_g = densities[1]/g

        a,b,c = coefs[2]
        cr1 = norms[0]['means'][2]
        cr2 = norms[1]['means'][2]
        cp1 = rational_func(x1, a, b, c)
        cp2 = rational_func(x2, a, b, c)
        c = rational_func(x, a, b, c)
        cn = (cr1-cr2)/(cp1-cp2)*(c-cp2) + cr2
        b = -np.log(cn)
        delta_b = densities[2]/b

        return (delta_r-delta_g)**2 + (delta_r-delta_b)**2 + (delta_b-delta_g)**2

    return f


def optimize(img, parameters):
    MINIMIZE_SEARCH_SPACE = False

    TOL = parameters['tolerance']
    MAX_ITER = parameters['max_iterations']
    NORM_FACTOR = parameters['normalization_factor']
    DOSE_MAX = parameters['max_dose']

    ZERO_DOSE_THRESHOLD = 62000


    red_parameters = parameters['calibration_parameters']['r']
    green_parameters = parameters['calibration_parameters']['g']
    blue_parameters = parameters['calibration_parameters']['b']
    calibrationCoefficients = [
        [red_parameters['a'], red_parameters['b'], red_parameters['c']],
        [green_parameters['a'], green_parameters['b'], green_parameters['c']],
        [blue_parameters['a'], blue_parameters['b'], blue_parameters['c']]    
    ]
    
    flag_normalization = 0 if "control_stripe_dose" not in parameters else 1
    if flag_normalization:
        normalizations = [
            {
                'dose': parameters['control_stripe_dose'],
                'means': [parameters['control_rgb_mean']['r'] / NORM_FACTOR, parameters['control_rgb_mean']['g'] / NORM_FACTOR, parameters['control_rgb_mean']['b'] / NORM_FACTOR]
            },
            {
                'dose': parameters['recalibration_stripe_dose'],
                'means': [parameters['recalibration_rgb_mean']['r'] / NORM_FACTOR, parameters['recalibration_rgb_mean']['g'] / NORM_FACTOR, parameters['recalibration_rgb_mean']['b'] / NORM_FACTOR]
            }
        ]

    ###################################

    calibrated_image = np.zeros(img.shape[0:1],dtype=np.float32)
    for column in range(calibrated_image.shape[0]):

        if np.min(img[column]) >=ZERO_DOSE_THRESHOLD:
            calibrated_image[column] = 0
        else:
            values = img[column]/NORM_FACTOR
            opt_densities = -np.log(values)
            
            if flag_normalization==0: 
                function_to_minimize = omega(opt_densities,calibrationCoefficients)
            else:
                function_to_minimize = omega_with_normalizations(opt_densities,calibrationCoefficients,normalizations)
            a,b,c = calibrationCoefficients[0]
            
            if MINIMIZE_SEARCH_SPACE:
                doses = inverse_rational_func(values, a, b, c)
                a = doses.min()
                b = doses.max()
            else:
                a = 0
                b = DOSE_MAX
            k=(math.sqrt(5)-1)/2
            xL=b-k*(b-a)
            xR=a+k*(b-a)
            numIter = 0
            while (b-a)>TOL:
                if function_to_minimize(xL)<function_to_minimize(xR):
                    b=xR
                    xR=xL
                    xL=b-k*(b-a)
                else:
                    a=xL
                    xL=xR
                    xR=a+k*(b-a)
                numIter += 1
                if numIter > MAX_ITER:
                    break
                    
            calibrated_image[column] = max(0,round((a+b)/2))

            if calibrated_image[column] >= DOSE_MAX-1:
                a = 0
                b = 0.05*DOSE_MAX
                k=(math.sqrt(5)-1)/2
                xL=b-k*(b-a)
                xR=a+k*(b-a)
                numIter = 0
                while (b-a)>TOL:
                    if function_to_minimize(xL)<function_to_minimize(xR):
                        b=xR
                        xR=xL
                        xL=b-k*(b-a)
                    else:
                        a=xL
                        xL=xR
                        xR=a+k*(b-a)
                    numIter += 1
                    if numIter > MAX_ITER:
                        break
                        
                calibrated_image[column] = max(0,round((a+b)/2))

    calibrated_image = np.asarray(calibrated_image,dtype=np.uint16)

    return calibrated_image
