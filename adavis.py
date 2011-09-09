#! /usr/bin/env python
# -*- coding: utf-8 -*-


#
#       adavis.py
#
#       Copyright 2011 Magnus Persson <magnusp@nbi.dk>
#
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 2 of the License, or
#       (at your option) any later version.
#
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#
#
#       ver 2.0
#
#
#

"""
Script with functions to perform different actions on interferometric/SD
radio fits cubes/arrays.

Needs : scipy (and numpy), 
        mpfit.py (optional, for Gaussian fitting), 
        congridding.py (optional, for regridding)

TODO : P-V diagram - rotatable 
       what happens with the coordinates?
       need to calc an offset, but call them x and y or something

TODO : RMS and other units, e.g. when using SD data, Kelvin instead of Jy.

TODO : Moment 2 maps - with MPFIT Gaussian fitting (check Jes mom2 IDL function)

TODO : Calculate common stuff in a function, use in moment 0/1/2 maps
       Perhaps calculate and store in the object?

TODO : What does the VELREF keyword in the GILDAS fits header mean? 
       Check GILDAS manual

TODO : Clean up code again, remove font handler, or inactivate it
       All fonts should be Times New Roman, to big of a hassle to change
       to Sans-serif font, i.e. for the tick labels mostly.

TODO : Tick locators are good for small regions/narrow spectra, but not for big/wide
       Perhaps change it with the 'box' keyword.
       Implemented a locator=[major,minor], this is perhaps better?

TODO : obj_dict -> source, for all functions
       Make this more unified, perhaps pass other info here, name etc?

TODO : When supplying source=dict(vsys=X) the DataObject velarr is changed, not good
       Check this for all function, so that it does not happens.
       The DataObject should be reusable, perhaps store vsys in DataObject?

TODO : Change to handle **kwargs and DataObject in all functions.

(TODO : Function to bin in spatial (2D) regime (congrid map), change ra/dec_delt etc)

TODO : Splatsearch in plot_spectra
       Integrate the splatsearch function in adavis.py?

TODO : Interactive splatsearch.

TODO : Interactive multiple Gaussian fitting

TODO : Check Jes functions how they work and try to merge/replace them.

TODO : How to divide it into a runnable program.

TODO : Implement it as command line program.

"""



# ASTRONOMY & ASTROPHYSICS figure width
#
# 255.76535 pt column width equals 88 mm (from aa.doc.pdf section 3.4)
# one inch in mm = 25.4 mm/inch
#one_col_fig_width_pt = 249.448819
one_col_fig_width_mm = 88
two_col_fig_width_mm = 180
side_caption_fig_width_mm = 120
inches_per_pt = 1.0/72.27                               # Convert pt to inches
inches_per_mm = 1/25.4                                  # Convert mm to inches
golden_mean = (5**0.5-1.0)/2.0                          # Aesthetic ratio
one_col_fig_width = one_col_fig_width_mm*inches_per_mm  # width in inches, roughly = 3.54
one_col_fig_height = one_col_fig_width*golden_mean      # height in inches
two_col_fig_width = two_col_fig_width_mm*inches_per_mm
side_caption_fig_width = side_caption_fig_width_mm*inches_per_mm
fig_size = [one_col_fig_width,one_col_fig_height]



###########################################
# ERRORS

# input parameter error
class ParError(Exception):
     def __init__(self, value):
         self.value = value
     def __str__(self):
         s1 = '\nWrong format/number of parameters. You input:\n    '
         s2 = '\nas parameters. Check it/them.'
         return s1+str(self.value)+s2
#
###########################################
# HELP FUNCTIONS
def print_warning(s):
    import sys
    sys.stderr.write(stylify('WARNING:',f='b',fg='r')+stylify(' '+s,f='b',fg='k'))
def print_error(s):
    # Dont know if this works as intended
    import sys
    sys.stderr.write(stylify('ERROR:',f='b',fg='r')+stylify(' '+s,f='b',fg='k'))
    sys.exit()
def calc_frequency(vlsr, freq0):
    """
    vlsr in kms
    freq0 in whatever you want out
    """
    from scipy import constants
    return (1-vlsr/(constants.c*1e-3))*freq0
def calc_vlsr (f,f0):
    """ calc vlsr in km/s from two freq """
    from scipy import constants
    return (1-f/f0)*constants.c*1e-3
def draw_beam(ax, data,loc=3, box=True):
    """
    function that draws the beam
    the attributes data.bmin, .bmaj and .bpa must exist in the data class
    """
    from mpl_toolkits.axes_grid.anchored_artists import AnchoredEllipse
    # the PA is calculated from N to E, that is +90 degrees from normal
    ae = AnchoredEllipse(transform=ax.transData,\
                            width=data.bmin,\
                            height=data.bmaj,\
                            angle=data.bpa+90,\
                            loc=loc,\
                            pad=0.15,\
                            borderpad=0.2,\
                            frameon=box)

    ax.add_artist(ae)
def stylify (s='Test text', f='n', fg='r', bg='d'):
    """ 
    
    Sends back the string 'txt' with the correct foreground unicode 
    color start and finish (reset color).
        
        Formatting style of text (f)
        f = 
            "n" normal
            "b" bold
            "u" underline
            "l" blinking
            "i" inverse
        Forground color of text (fg)
        fg = 
             "k" black
             "r" red
             "g" green
             "y" yellow
             "b" blue
             "m" magenta
             "c" cyan
             "a" gray
             "d" default
        Background color of text (fg)
        bg = 
            "k" black
            "r" red
            "g" green
            "y" yellow
            "b" blue
            "m" magenta
            "c" cyan
            "a" gray
            "d" default
    
    TODO : add a value for randomizing a color
    
    """
    
    # needed them in this order for it to work,
    # styles, fg color, bg color
    format_and_colors = {"n_f": 0, #
                         "b_f": 1, #
                         "u_f": 4,
                         "l_f": 5,
                         "i_f": 7,
                         "k": 30,
                         "r": 31,
                         "g": 32,
                         "y": 33,
                         "b": 34,
                         "m": 35,
                         "c": 36,
                         "a": 37,
                         "d": 39,
                         "k_bg": 40,
                         "r_bg": 41,
                         "g_bg": 42,
                         "y_bg": 43,
                         "b_bg": 44,
                         "m_bg": 45,
                         "c_bg": 46,
                         "a_bg": 47,
                         "d_bg": 49}

    CSI = "\x1B["
    end = CSI+'m'
    
    if f == 'b' and fg =='a':
        print stylify('\n Warning : This combination of colors/styles does not work\n','b','r','d')
        raise ParError((f,fg,bg))
    bg +='_bg' # append to the list, the "_bg" ending
    f += "_f" # append "_f" to the formatting list
    
    try:
        style = [format_and_colors[f.lower()],
                format_and_colors[fg.lower()],
                format_and_colors[bg.lower()]]
        style = [str(x) for x in style]
        formatted_text = CSI+';'.join(style)+'m'
        formatted_text += s + end
    except KeyError, ex:
        raise ParError((f,fg,bg))

    return formatted_text
def draw_fov(ax, data):
    """
    Function to draw the field of view into the
    plot with axes 'ax'.
    Assumes that the axes data is set to arcsec
    """
    from matplotlib.patches import Circle
    cir = Circle( (0,0), transform=ax.transData, fill=False, ec='k', lw=1, ls='dashed', radius=data.fov/2)
    ax.add_patch(cir)
def draw_sizebar(ax, data, dist=220, au=200):
    """
    distance in pc
    then theta = AU/(distance in pc)
    """
    from mpl_toolkits.axes_grid.anchored_artists import AnchoredSizeBar
    # draw horizontal bar with length of 10 in data coordinate
    # 10 arcs * 220pc = 2200
    asb = AnchoredSizeBar(ax.transData,
                            au/float(dist),
                            str(au)+" AU",
                            loc=8,
                            pad=0.1, borderpad=0.5, sep=5,
                            frameon=False)
    ax.add_artist(asb)
def draw_highlight_box(ax, xpos, xwidth):
    """
    adds a highlight box that spans whole y-axes space and specified data
    coordinates in x
    """
    from matplotlib.patches import Rectangle
    from matplotlib.transforms import blended_transform_factory

    trans = blended_transform_factory(ax.transData, ax.transAxes)
    # We want x to be in data coordinates and y to
    # span from 0..1 in axes coords
    xpos -= xwidth/float(2)
    print xpos, xwidth
    rect = Rectangle((xpos,0), width=xwidth, height=1,
                             transform=trans, color='yellow',
                             alpha=0.3)

    ax.add_patch(rect)
def put_line_indicator(ax, velocity, spect, xpos, text_string, \
            text_size=3, text_weight='extra bold', text_color='black',\
             lc='b', offset=0):
    """
    Put text in figure, the positon is in axes data coordinates
    additional kwargs are text_size, text_weight, text_color
    oset_bool is for lines at same places
    """
    # calculate position
    line_height = spect.max()*0.08
    try:
        maxval = spect[get_indices(velocity,[xpos-2,xpos+2])].max()
    except ValueError, ex:
        maxval = spect.max()
    except IndexError, ex:
        maxval = spect.max()
    line_ypos = maxval + maxval*0.15
    text_ypos = line_ypos + line_height + line_height*0.5
    text_ypos = text_ypos + len(text_string)*offset*3e-2
    # plot line
    ax.plot([xpos, xpos],[line_ypos,line_ypos+line_height],lc)
    # print text
    ax.text(xpos+0.1,text_ypos,\
    text_string,\
    size=text_size, weight=text_weight, color=text_color,\
    ha='center',va='bottom',rotation='vertical',\
    transform = ax.transData)
def calc_sigma(N,rms,vcdelt):
    from scipy import sqrt
    return sqrt(N)*rms*abs(vcdelt)
def calc_cooffset(ra,dec,offset):
    """ 
    calculates new coordinates from old ones
    ra,dec - string with coordinate
    offset - offsets in a tuple/list i.e. (dX,dY), [dX,dY]
    """
    from numpy import cos, pi, array
    ra_inp = ra
    ra = ra.split(':')
    ra = [float(i) for i in ra]
    ra_decimal = (ra[0] + ra[1]/60.0 + ra[2]/3600.0)*15.0 # convert to decimal number in degrees
    dec_inp = dec
    dec = dec.split(':')
    dec = [float(i) for i in dec]
    dec_decimal = dec[0] + dec[1]/60.0 + dec[2]/3600.0 # convert to decimal number
    offset_inp = offset
    offset = array(offset)/3600.0
    cosdec = cos(dec_decimal*pi/180.) # convert to radians
    new_ra = ra_decimal + offset[0]/cosdec
    new_dec = dec_decimal + offset[1]
    print 'Input coordinates:'
    print 'RA:\t%s\nDEC:\t%s' % (ra_inp,dec_inp)
    print 'Offset: %s, %s' % offset_inp
    print 'New coordinates:'
    print 'RA:\t%s\nDEC:\t%s' % ((parse_ra(new_ra,string=True),parse_dec(new_dec,string=True)))
def parse_region(data, region, f=False):
    """
    Parser for the region parameter, three different possibilities to supply
    the region command:

        o region = [i1, j1, i2, j2]
            The four corners of a square around the object, in offset from
            phase center position.

        o region = [i1, j1, a]
            The center coordinate (i1, j1) and the side (a) of a square around
            the center coordinate (i1, j1).

        o region = [d1, d2]
            Just the square sides length, will be centered on the phase center.

    All the coorinates are given in lenghts and offsets (in asec) from the
    data center as displayed normally in radio data.

    Inspired by the miriad 'region' parameter

    ---------------------------------------------------------------------------

                            oOO Changelog OOo

    *2010/06 Funciton created

    *2010/10(11) Doc written and some errors in the code corrected (+-1 in
    some places)

    *2010/12/09 in len(region)==3, changed the division with an abs()
    array([-region[2],region[2]])/(2*data.ra_cdelt) to abs(2*data.ra_cdelt).
    In len(region)==2 same change, now it is correct, I hope.

    *2010/12/13 the previous "fix" made the len=3 procedure to be erronous.
    corrected it

    """
    from scipy import ceil, floor, array
    if len(region)==4:
        xcheck = region[0]==region[2]
        ycheck = region[1]==region[3]
        #x1, x2 = (data.ra_npix+1)/2 + array([region[0],region[2]])/abs(data.ra_cdelt) + array([0,xcheck])
        #y1, y2 = (data.dec_npix+1)/2+ array([region[1],region[3]])/abs(data.dec_cdelt)+ array([0,ycheck])
        #
        x1, x2 = array([region[0],region[2]])/data.ra_cdelt+ data.ra_crpix - 1 + array([0,xcheck])
        y1, y2 = array([region[1],region[3]])/data.dec_cdelt+ data.dec_crpix - 1 + array([0,ycheck])
        #
    elif len(region)==3:
        check = region[2]==0
        #x1, x2 = (data.ra_npix+1)/2 + array([-region[2],region[2]])/(2*abs(data.ra_cdelt)) + region[0]/data.ra_cdelt + array([0,check])
        #y1, y2 = (data.dec_npix+1)/2+ array([-region[2],region[2]])/(2*abs(data.dec_cdelt)) +region[1]/data.dec_cdelt+ array([0,check])
        #
        x1, x2 = data.ra_crpix + region[0]/data.ra_cdelt + array([-region[2],region[2]])/abs(2*data.ra_cdelt) - 1 + array([0,check])
        y1, y2 = data.dec_crpix + region[1]/data.dec_cdelt + array([-region[2],region[2]])/abs(2*data.dec_cdelt) - 1 + array([0,check])
        #
    elif len(region)==2:
        xcheck = region[0]==0
        ycheck = region[1]==0
        #x1, x2 = (data.ra_npix+1)/2 + array([-1,1])*region[0]/abs(data.ra_cdelt)  + array([0,xcheck])
        #y1, y2 = (data.dec_npix+1)/2+ array([-1,1])*region[1]/abs(data.dec_cdelt) + array([0,ycheck])
        #
        x1, x2 = array([-region[0],region[0]])/(2*abs(data.ra_cdelt)) + data.ra_crpix - 1 + array([0,xcheck])
        y1, y2 = array([-region[1],region[1]])/(2*abs(data.dec_cdelt)) + data.dec_crpix - 1 + array([0,ycheck])
        #
    elif():
        print ('Error, region keyword malformed')
        sysexit(1)
        #
    # so that we are returning usable pixel coordinates
    if f==False:
        x1,x2,y1,y2 = array([x1,x2,y1,y2]).round().astype('int')
    return x1,x2,y1,y2
def parse_pxlcoord (data, x, y):
    """ Function doc """
    xoffset = (x-data.ra_crpix)*data.ra_cdelt
    yoffset = (y-data.dec_crpix)*data.dec_cdelt
    return xoffset, yoffset
def parse_ra (ra,string=False):
    """

    Parses a simple float coordinate and returns hours, minutes and seconds.
    Input
        ra : the right ascention coordinate to be parsed

    ---------------------------------------------------------------------------

                            oOO Changelog OOo

    *2010/09 Funciton created

    *2010/12/18 Added documentation


    """
    a = ra/15
    hours = int(a)
    b = (a-hours)*60
    minutes = int(b)
    seconds = (b-minutes)*60
    if string:
        return str(hours)+':'+str(minutes)+':'+str(seconds)
    return hours,minutes,seconds
def parse_dec (dec, string=False):
    """

    Parses a simple float coordinate and returns hours, minutes and seconds.
    Input
        dec: the declination coordinate to be parsed

    ---------------------------------------------------------------------------

                            oOO Changelog OOo

    *2010/09 Funciton created

    *2010/12/18 Added documentation


    """
    degrees = int(dec)
    b = (dec-degrees)*60
    minutes = int(b)
    seconds = (b-minutes)*60
    if string:
        return str(degrees)+':'+str(minutes)+':'+str(seconds)
    return degrees,minutes,seconds
def parse_linelist(linelist):
    """

    Parse a linelist/CSV file of the lines, so that it is easier to just
    use a lot of lines from Splatalogue or create a list with the lines.

    Input
        linelist : Can be formatted in three different ways

                1.  The path to a COLON separated table file from
                    Splatalogue,where the first two columns are as

                   ----------------------------
                   |   name   |   frequency   |
                   ----------------------------

                    The lines (rows/entries etc) can be commented out with a
                    hash '#'. Easy to get exported from Splatalogue.net.

                2.  A list in the format

                    linelist = ['name1', frequency1, 'name2', frequency2]

                3. A list of lists in the format

                    linelist = [[list_of_names], [list_of_frequencies]]


    ---------------------------------------------------------------------------

                            oOO Changelog OOo

    *2010/06
        Funciton created

    *2010/12
        Doc written

    TODO : when list is  [['Name'],[203.45654]] it cannot output the right format.
    
    

    """
    from scipy import size, arange, zeros, array
    def get_lines(linelist):
        # pars a list of lists scenario
        names = linelist[0]
        freqs = linelist[1]
        arr_len = len(names)+len(freqs)
        list = zeros((arr_len))
        return array([[names[i],freqs[i]] for i in arange(len(names))]).ravel()
    #
    if size(linelist[1])==1 and type(linelist)==type([]):
        # if it is just a list of lines
        # it is already in the disired format
        return linelist
    elif size(linelist[1])>1:
        # if it is a list with two lists in it
        # that is, the second element is (strictly) longer than 1
        return get_lines(linelist)
    elif size(linelist[1])==1 and type(linelist) == type(''):
        # in case it is the path to a CSV file
        # load the table with the load ascii table function loadatbl
        names, freqs = loadatbl(linelist, dtype='string', sep=':')[0:3:2]
        #
        f = []
        n = []
        for i,j in zip(freqs,names):
            if i != '':
                f.append(i)
                n.append(j)
        freqs=array(f)
        names = n
        freqs = freqs.astype('float64')
    return get_lines([names,freqs])
def get_indices (arr,vals,disp=False):
    """

    Get the indices of all the elements between vals[0] and vals[1].
    Alternatively also between vals[2] and vals[3] if they are given.

    Input:
        arr  : the array in which to look for the elements
        vals : a list with either 2 or 4 values that corresponds
               limits inbetween which the indices of the values

    Optional argument(s):
        disp : Bolean parameter, if True it displays start and end
               index and the number of channels inbetween. Only works
               for value lists of length 2.

    Assumes the values in 'arr' is the mid values and that it is evenly
    spaced for all values.


    ---------------------------------------------------------------------------

                            oOO Changelog OOo

    *2010/06
        Funciton created

    *2010/12
        Doc written

    """

    from scipy import concatenate, where, array, diff
    dx = abs(.5*diff(arr)[0])
    if len(vals)==4:
        v1,v2,v3,v4 = vals + array([-1,1,-1,1])*dx
        # if the user wants two velocity areas to calculate noise
        low = where((arr>=v1)*(arr<=v2))[0]
        high = where((arr>=v3)*(arr<=v4))[0]
        channels = concatenate((low,high))
    elif len(vals)==2:
        v1,v2 = vals + array([-1,1])*dx
        #  if input just want one velocity area to calculate noise
        # 28/07/2011 removed +1 here, why did I have that?
        #            seems to be more correct without +1
        #            changed arr<v2 to arr<=v2
        #channels = where((arr>=v1)*(arr<v2))[0]+1
        channels = where((arr>=v1)*(arr<=v2))[0]
    #
    if disp and len(vals)==2:
        first, last = channels.min(), channels.max()
        n = last-first+1
        print '\nFirst: %d,\n Last: %d\n Nchan: %d\n' % (first, last, n)
    return channels
def gauss1d(x, params=None, height=None):
    """

    NB: Use this for plotting, the gauss1dfit gaussian function should be
        faster for fitting.

    returns the function vector of input x with parameters p
    just a gaussian function, perhaps to plot a gaussian after the fitting

    fix is the fixed parameters array

    should have subtracted baseline of data before fitting
    i.e. not height is fitted


    gaussian of the form a[0]*exp(-(X-a[1])**2/(2*a[2]**2)*2*sqrt(2*log(2)))
    is fitted. Here a[2] is the FWHM, we multiply with  2*sqrt(2*log(2)) to
    transform it to sigma.
    For an astronomer the FWHM is much more interesting, right?

    TODO : be able to pass height as optional variable

    Changes:
    *using numpy instead of scipy

    """
    from numpy import exp, array, alen, array, log, sqrt, arange
    #
    # Check the input parameters, since this is for plotting, we check them
    #
    # params should always be a list of parameters
    # if it is a series of tuple(s)
    # ie params=((A1,x1,sig1),(A2,x2,sig2))
    if alen(params[0])==3:
        # just put them in a long array
        params = array([list(i) for i in params]).flatten()
        # or in their respective arrays directly?
        #a = params[arange(0,len(params),3)]
        #x = params[arange(1,len(params),3)]
        #dx = params[arange(2,len(params),3)]
    elif params==None:
        # add code to
        # calculate moments!
        raise ParError(params)
    #
    no_fits = len(params)/3
    #
    # check that all parameters are input
    if len(params)%3 != 0:
        raise ParError(params)
    #
    # 2*sqrt(2*log(2)) to convert to sigma (two is cancled out)
    if height==None:
        gaussian = lambda X, a : a[0]*exp(-(X-a[1])**2/(a[2]**2)*sqrt(2*log(2)))
    elif height!=None:
        gaussian = lambda X, a : height + a[0]*exp(-(X-a[1])**2/(a[2]**2)*sqrt(2*log(2)))
    #
    def func (X, p):
        S=0
        try:
            for i in arange(0,len(p),3):
                S += gaussian(X, p[i:i+3])
        except IndexError, ex:
            raise ParError(p)
        return S
    #
    #
    return func(x, params)
def fit_gauss1d((X,Y),\
                params,\
                err = None,\
                fixlist = None,\
                minbool = None,\
                minpar = None,\
                maxbool = None,\
                maxpar = None,\
                tie = None,\
                verbose = 1,\
                full_output=0):
    """
    X - the coordinates of the x-axis (array)
    Y - the data to be fitted (array)
    params - are the initial guesses of the parameters,
            the parameters are grouped in three, with order
            amplitude, peak position and distribution FWHM
            [[AMPL, POS, FWHM]] or ((AMPL, POS, FWHM))
    err - error of the Y data
    fixlist - a list of which parameters to be fixed during fit
            e.g. fixlist = [[0,0,1],[0,0,1]] to fix the width of two
            gaussians that are being fit
    minbool - if != None, will assume that you want to limit something with a
            minimum
    minpar - so then you must specify what that minimum limit is
    maxbool - here alseo, if != None you will have to specify a
    maxpar - which shows what that value is, you have to suply a value
            even if you are not limiting it so that the specific limiting
            value can be found
    verbose - 0 to be completely quiet
            1 to output final fit parameters (default)
            2 for full verbosity, output each iteration of the fit process
            AND the final fit parameters
    full_output - output the whole shebang?

    MPFIT status messages interpretation:
        0  Improper input parameters.
        1  Both actual and predicted relative reductions in the sum of squares
           are at most ftol.
        2  Relative error between two consecutive iterates is at most xtol
        3  Conditions for status = 1 and status = 2 both hold.
        4  The cosine of the angle between fvec and any column of the jacobian
           is at most gtol in absolute value.
        5  The maximum number of iterations has been reached.
        6  ftol is too small. No further reduction in the sum of squares is
           possible.
        7  xtol is too small. No further improvement in the approximate solution
           x is possible.
        8  gtol is too small. fvec is orthogonal to the columns of the jacobian
           to machine precision.


    TODO : initial guesses for params
                    o intereactive - point and clic
                    o 1D : add a 1 gaussian guessing alorithm
    TODO : minimum width >= X[1]-X[0]
    """
    #from scipy import optimize
    from numpy import exp, hstack, array, log, sqrt, diag, alen, zeros, \
                        where, arange
    from mpfit import mpfit
    print '\n Fitting Gaussians'
    #
    ## Checking the input parameters
    #
    print '\nChecking input parameters'
    # flatten the parameters, so it is readable for the gaussian fitting
    params = array(params).flatten()
    # number of gaussians to fit
    no_fits = (len(params))/3
    #
    # check the total number of params
    if len(params)%3 != 0:
        raise ParError(params.reshape((alen(params)/3,3)))

    # that was the most important parameters,
    # now on to the other
    # FIXLIST
    if fixlist != None:
        fixlist = array(fixlist).flatten()
        # length of fixlist must equal the number of parameters
        if alen(fixlist) != alen(params):
            raise ParError(fixlist)
    elif fixlist == None:
        fixlist = [False, False, False]*no_fits
    #
    # MINIMUM LIMITS
    #
    # first we define a minimum limit for the width
    xwidth = abs(X[1]-X[0]) # it is evenly space
    #
    # first case, it is not None, we are giving limits
    if minbool != None:
        # first the boolean array
        minbool = array(minbool).flatten()
        # then the minumum parameter array
        minpar = array(minpar).flatten()
        if alen(minbool) != alen(params) or alen(minbool) != alen(minpar):
            raise ParError((minbool,minpar))
        #
        # any width that need to be set?
        # we know that we are setting the limits, but which FWHM limits are
        # not set to True?
        index = where(minbool[arange(2,alen(minbool),3)]==False)[0]
        # go back to the full array indices

        index = (index+2)+2*index
        # set the bool array to True at the FWHM
        minbool[index] = True
        # set the FWHM minimum parameter to xwidth
        minpar[index] = xwidth
    #
    elif minbool == None:
        # it is not limited but,
        # here we still would want to limit the gaussian fwhm to the
        # width of one x axis data unit, can't be thinner than that, can it
        minbool = [False,False,True]*no_fits
        minpar = [0,0,xwidth]*no_fits
    #
    # MAXIMUM LIMITS
    if maxbool != None:
        maxbool = array(maxbool).flatten()
        # then the maximum parameter array
        maxpar = array(maxpar).flatten()
        if alen(maxbool) != alen(params) or alen(maxbool) != alen(maxpar):
            raise ParError((maxbool,maxpar))
    elif maxbool == None:
        # just setting them to False and zero
        maxbool = [False, False, False]*no_fits
        maxpar = [0,0,0]*no_fits
    #
    if tie != None:
        # parse the tied parameters
        tie = array(tie).flatten()
    elif tie == None:
        tie = ['','','']*no_fits
    #
    print '\nDefining fitting function and fitting'
    #
    ## Defining the fitting function and the error function
    # NB: we are fitting FWHM directly
    gaussian = lambda X, a : a[0]*exp(-(X-a[1])**2/(a[2]**2)*sqrt(2*log(2)))
    #
    def fitfunc (X, p):
        S=0
        for i in arange(0,len(p),3):
            S += gaussian(X, p[i:i+3])
        return S
    #
    def errfunc(x,y,err):
        if err == None:
            def f(p,fjac=None): return [0,(y-fitfunc(x,p))]
        else:
            def f(p,fjac=None): return [0,(y-fitfunc(x,p))/err]
        return f
    #
    # define the parameter dictionary
    PAR = ['Amplitude','Position','Fwhm']
    fitlist = []
    for i in xrange(alen(params)):
        # create the dictionary to be appended to the list=
        dictline = dict(n  = i,\
                        value   = params[i],\
                        limits  = [minpar[i],maxpar[i]],\
                        limited = [minbool[i],maxbool[i]],\
                        fixed   = fixlist[i],\
                        parname = PAR[i%3],\
                        tied = tie[i],\
                        err   = 0)
        fitlist.append(dictline)


    if verbose == 2:
        # verbose level 2, output all fit iterations and final fit params
        quiet = False
    else:
        quiet = True
    #
    mpfit_out = mpfit(errfunc(X,Y,err=err), parinfo=fitlist, quiet=quiet)
    pfit = mpfit_out.params
    pfit_err = mpfit_out.perror
    chi2 = mpfit_out.fnorm
    #
    # any errors
    if mpfit_out.status == 0:
        raise Exception(mpfit_out.errmsg)

    if verbose in [1,2]:
        print('\n')
        print '*'*40
        print 'Results of fitting:\n'
        j = 1
        for i,val in enumerate(pfit):
            fitlist[i]['value'] = val
            if i in arange(0,alen(pfit),3):
                print 'Fit number: %d' % j
                j+=1
            print u"%s :  %2.3f \u00b1 %2.3f" % (fitlist[i]['parname'],val, pfit_err[i])
        print '*'*40
        print u"\u03C7\u00B2 : %2.3f Red. \u03C7\u00B2 : %2.3f DOF : %d\n" % (chi2,(chi2/len(Y)),(len(Y)-len(pfit)))
    #
    #
    if full_output:
        return pfit, pfit_err, chi2, mpfit_out
    else:
       return pfit, pfit_err
def gauss2d (a, X, Y):
    """ Gaussian 2D """
    #
    from scipy import cos, sin, exp
    xp = X*cos(a[5]) - Y*sin(a[5])
    xp0 = a[1]*cos(a[5]) - a[2]*sin(a[5])
    yp = X*sin(a[5]) + Y*cos(a[5])
    yp0 = a[1]*sin(a[5]) + a[2]*cos(a[5])
    #
    f = a[0]*exp(-.5*(((xp - xp0)/a[3])**2 + ((yp - yp0)/a[4])**2))
    return f
def gaussfit2d((X,Y,Z), params=None, err=None):
    """

    params= (height, (amplitude, x, y, sig_x, sig_y, rota), (amplitude, x, y, sig_x, sig_y, rota)) etc


        xp = cos(rota) * x - sin(rota) * y
        yp = sin(rota) * x + cos(rota) * y
        (rota should be in degrees)
        g = b + a exp ( - ( ((xp - center_xp)/width_x)**2 +
        ((yp-center_yp)/width_y)**2 ) / 2 )

    TODO : move code over to MPFIT
    TODO : initial guesses for params
            o intereactive - point and clic
            o 1D : add a 1 gaussian guessing alorithm
        if(f1.lt.f2)then
          t = f1
          f1 = f2
          f2 = t
          t = sf1
          sf1 = sf2
          sf2 = t
          p = p + 90
        endif
        p = mod(p,180.)
        if(p.lt.-90) p = p + 180
        if(p.gt. 90) p = p - 180
        end

    TODO : Be able to lock a gaussfit parameter
    """

    from scipy import optimize, exp, hstack, array, cos, sin, indices, ravel
    from scipy import sqrt, arange, pi, ceil, diff
    #
    #
    if params==None:
        print '--> No parameters given, guestimates\n'
        from scipy.ndimage import center_of_mass as cmass
        from scipy.stats import mode
        y0,x0 = cmass(Z)
        row = Z[int(y0),:]
        xsig = sqrt(abs(((arange(row.size)-x0)**2*row).sum()/row.sum()))*diff(X[0,1:3])
        col = Z[:,int(x0)]
        ysig = sqrt(abs(((arange(col.size)-y0)**2*col).sum()/col.sum()))*diff(Y[1:3,0])
        height = mode(Z.ravel())[0][0]
        amplitude = Z.max() - height
        # guess the PA to be 0
        params = [height, amplitude, X[0,x0], Y[y0,0], xsig, ysig, 0]
        print('done.')
    elif params!=None:
        print '--> Parameters entered, using them\n'
        a = array(params[0])
        b = array([list(i) for i in params[1:]]).flatten()
        # switch to radians!
        index = arange(5,len(b),5)
        for i in index:
            b[i] = b[i]*pi/180
        params = hstack((a,b))
        if len(params[1:])%6 != 0:
            print ' '
            print 'wrong number of input parameters'
            print '(N*6)+1 parameters where N are the number of gaussians fited'
            print '  height,  amplitude, x0, y0, xisg, ysig, angle(deg)'
            print ' '
            return ; sysexit()
    #
    #
    no_fits = len(params[1:])/6

    # List of the indices (a):
    #   0   1   2    3    4      5
    #   B, x0, y0, xsig, ysig, theta
    #gau2d = lambda a, X, Y  : a[0]*exp(\
                    #-((X*cos(a[5])-Y*sin(a[5])) - \
                    #(a[1]*cos(a[5])-a[2]*sin(a[5])) )**2 / (2*a[3]**2)\
                    #-((X*sin(a[5])+Y*cos(a[5])) - \
                    #(a[1]*sin(a[5])+a[2]*cos(a[5])) )**2 / (2*a[4]**2))
    #
    #if no_fits == 1:
        #fitfunc = lambda p, X, Y: p[0] + gau2d(p[1:7],X,Y)
    #if no_fits == 2:
        #fitfunc = lambda p, X, Y: p[0] + gau2d(p[1:7],X,Y)\
                                        #+gau2d(p[7:13],X,Y)
    #if no_fits == 3:
        #fitfunc = lambda p, X, Y: p[0] + gau2d(p[1:7],X,Y)\
                                        #+gau2d(p[7:13],X,Y)\
                                        #+gau2d(p[13:19],X,Y)
    def fitfunc (p, X, Y):
        S = p[0] # first the baseline
        # then the gaussians
        for i in arange(1,len(p[1:]),6):
            S += gauss2d(p[i:i+6], X, Y)
        return S
    # error function
    # List of the indices (p):
    #   0   1   2   3   4      5     6
    #   A,  B, x0, y0, xsig, ysig, theta
    if err == None:
        errfunc = lambda p, X, Y, Z: (fitfunc(p, X, Y) - Z).ravel() # Distance to the target function
    else:
        errfunc = lambda p, X, Y, Z: ((fitfunc(p, X, Y) - Z)/err).ravel() # Distance to the target function
    # the fitting
    p1, success = optimize.leastsq(errfunc, params, args=(X,Y,Z))
    #
    #switch back to degrees and positive width
    # check so degrees betweem 0 and 180
    index = arange(4,len(p1),5) # start at xsig
    for i in index:
        p1[i] = abs(p1[i])
        p1[i+1] = abs(p1[i+1])
        # return degrees
        p1[i+2] = p1[i+2]*180/pi-90
        # removed this to not do it twice (is done in parse_gau2fit)
        #if p1[i+2]<0: p1[i+2] += ceil(abs(p1[i+2]/180))*180
        #if p1[i+2]>180: p1[i+2] -= ceil(abs(p1[i+2]/180))*180
    #
    return p1,success,no_fits
def parse_gau2dfit (fwhm1, fwhm2, sfwhm1, sfwhm2, pa, spa):
    """ Function doc

    fwhm in pixels, pa in degrees
    """
    from scipy import sqrt, log, append
    #from sys import exit as sysexit
    #if abs(DATA.ra_cdelt) != abs(DATA.dec_cdelt):
    #    print 'Not equal scale of x and y pixels'
    #    return ; sysexit()
    ##
    ## convert to asecs
    #delta = abs(DATA.ra_cdelt)
    #fwhm1 = fwhm1*delta
    #fwhm2 = fwhm2*delta
    #sfwhm1 = sfwhm1*delta
    #sfwhm2 = sfwhm2*delta
    #
    # check if major is in fact minor axis
    if fwhm1<fwhm2:
        # switch!
        fwhm1, fwhm2 = (fwhm2, fwhm1)
        sfwhm1, sfwhm2 = (sfwhm2, sfwhm1)
        pa = pa + 90
    #
    # now check the PA
    pa = pa%180
    if pa<-90: pa += 180
    if pa>90: pa -= 180

    return (fwhm1, fwhm2, sfwhm1, sfwhm2, pa, spa)
def gauss2d_decon ((bmaj1, bmin1, theta1, bmaj2, bmin2, theta2), ang='rad'):
    """
    Deconvolves one gaussian  with parameters bmaj1, bmin1, theta1 (major,
    minor, PA) with another (bmaj2,bmin2, theta2)
    all in FWHM and radians (if deg is wanted, set ang='deg')


    uses:
    pi, cos, sin, arctan2, sqrt, min,

    """
    from scipy import pi, cos, sin, arctan2, sqrt
    #
    # check the ang keyword, if deg, go over to radians from deg
    if ang=='deg':
        theta1 *= pi/180
        theta2 *= pi/180
    #
    # define some calculations
    alpha  = (bmaj1*cos(theta1))**2 + (bmin1*sin(theta1))**2 - \
             (bmaj2*cos(theta2))**2 - (bmin2*sin(theta2))**2
    beta   = (bmaj1*sin(theta1))**2 + (bmin1*cos(theta1))**2 - \
             (bmaj2*sin(theta2))**2 - (bmin2*cos(theta2))**2
    gamma  = 2 * ( (bmin1**2-bmaj1**2)*sin(theta1)*cos(theta1) -\
                   (bmin2**2-bmaj2**2)*sin(theta2)*cos(theta2) )
    #
    # calculate the intermediate results
    s = alpha + beta
    t = sqrt((alpha-beta)**2 + gamma**2)
    limit = 0.1*min(bmaj1,bmin1, bmaj2, bmin2)**2
    #
    # now check if result is illigal/close to a point source
    if alpha < 0 or beta < 0 or s < t:
        bmaj, bmin, bpa = [0, 0, 0]
        #
        # now check if result is close to a point source
        tmp_par =.5*(s-t)
        if tmp_par < limit and alpha > -limit and beta > -limit:
            success = 1
        #
        # it was not close to point source, but results are thus illigal
        else:
            success = 2
    #
    # since (if) everything is ok, go ahead and calculate the bmaj, bmin & bpa
    else:
        bmaj = sqrt(.5*(s+t))
        bmin = sqrt(.5*(s-t))
        #
        # bpa
        if (abs(gamma)+abs(alpha-beta)) == 0:
            bpa = 0
        else:
            bpa = 0.5 * arctan2(-gamma,(alpha-beta))
        success = 0
        #
        # go back to degrees if asked for
        if ang=='deg':
            bpa *= 180/pi
    #
    # send back the results
    return (bmaj, bmin, bpa, success)
def set_rc(font={'family':'serif', 'serif': ['Times New Roman'],
        'size':8},
        quality=[300, 300]):

    from matplotlib import rc
    ################################
    # setting global rc properties #
    ################################
    rc('text', usetex=True)
    rc('savefig', **{'dpi': quality[0]})
    rc('figure',**{'facecolor': '1', 'dpi': quality[1]})
    rc('image', **{'origin': 'lower'})
    #to set the global font properties
    rc('font', **font)
    # ticksize
    #rc('xtick',**{'minor.size':3, 'major.size':7})
    #rc('ytick',**{'minor.size':3, 'major.size':7})
    # linewidths
    rc('axes', linewidth=1)
    rc('patch', linewidth=0.5)
    rc('lines', linewidth=0.5, markeredgewidth=0.8)
def parse_tick_font (font):
    """
    You have to add your formatter yourself with:
    labels = label_X.replace('X',data_fmt)
    where data_fmt  eg = '%g'
    and also:
    formatted_labels = FormatStrFormatter(labels)

    and lastly:
    ax.xaxis.set_major_formatter(formatted_labels)

    """
    from scipy import array, where
    if font.has_key('family'):
        fformatters = array(['$\mathrm{X}$','$\mathsf{X}$','$\mathtt{X}$' , '$\mathit{X}$'])
        ffamilies = array(['serif', 'sans-serif', 'monospace', 'cursive'])
        label_X = fformatters[where(font['family']==ffamilies)][0]
    else:
        label_X = '$\mathrm{X}$'
    #return label_X
    return 'X'
def get_telescope_diameter(telescope):
    from string import upper
    from scipy import where, array
    name = array(['SMA', 'PDBI', 'JCMT', 'AP-H201-F102', 'IRAM30M'])
    dia = array([6, 15, 15, 12, 30])
    try:
        diameter = dia[where(upper(telescope)==name)][0]
    except IndexError, ex:
        diameter = 1
    return diameter
#
#########################################
# ASCII TABLE HELP FUNCTIONS
# table handling help functions. easily reads in
# simple ascii tables with # as comment character
def saveatbl(filename, dataList, names):
    """
    saves a list of data arrays ("dataList") in to a table with
    the coloumn names in "names" as an ASCII file with name
    "filename" (can be a path to a file as well)
    """

    def fileExists(f):
        try:
            file = open(f)
        except IOError:
            return False
        else:
            return True

    if type(dataList) != type([]):
        dataList = list(dataList) # if its not a list, make it one

    if len(dataList) != len(names):
        raise Exception('The number of column names does not match the number of data arrays')

    if fileExists(filename) == False:
        with open(filename,'w') as f: # force creating "filename"
            #first line, the column names
            out = "\t\t".join(['no']+names)
            f.write('#'+out+'\n')
            f.write('\n')

            for i in xrange(len(dataList[0])): # make the index as long as
                # the first array in the list
                out = "\t\t".join([str(i+1)]+[str(x[i]) for x in dataList])
                f.write(out+'\n') # add a line break

    elif fileExists(filename) == True:
        print(' ')
        print('FILE EXISTS ('+str(filename) +') - SKIPPING SAVE')
        print(' ')
def loadatbl(filename, dtype='float64', rtype='array',sep=None, c_char=['#', '!', '|', '/']):
    """
    loads a list of data arrays in "filename", returns an array of the
    whole shebang (loads arrays saved with the savetable command). just do:
    (not the number column...)
    a = loadtable(filename)
    and then a[0] for first column, a[1] for second column and so on.
    """
    from scipy import array
    try:
        with open(filename,'r') as f:
            values = []
            for line in f:
                start_test = [line.startswith(x) for x in c_char]
                if True in start_test or not line.strip():
                    continue # skip lines that are comments and empty
                line = line.strip('\n')
                cols = line.split(sep)
                values.append(cols)
    except IOError:
        raise IOError('file ' +str(filename)+' does NOT exist...')
    except ValueError:
        raise ValueError('Trying to convert to '+str(dtype)+' while it is a string\
                        try to change it to \'str\'')
    if rtype=='array':
        return array(values,dtype=dtype).transpose()
    elif rtype=='native':
        return values
def infoatbl(filename, sep=None, c_char=['#', '!', '|', '/']):
    """
    just returns the lines with comments (ie the column names) from a *.atbl file
    """
    try:
        with open(filename,'r') as f:
            strings = []
            for line in f:
                start_test = [line.startswith(x) for x in c_char]
                if True in start_test:
                    strings.append(line.split(sep))
    except IOError:
        raise IOError('file' + str(filename)+'does not exist...')

    return strings
#
#########################################
# MAIN DATA CLASS
# Main data object, needs fits file as input
# keywords can be appended to object later
# to complement fits header information

class DataObject:
    """
    ------------------------------------------
    Adavis DataObject
    
    Usage :
    ObjectName = DataObject(PathToFitsFile)
    
    ------------------------------------------
    
    Should be able to read:
    Maps, cubes, SD-spectra
    
    
    """
    def __init__(self, fitsfile, telescope=None):
        """
        TODO : loadcube - if the rotational matrice is non empty, load data and rotate it
        TODO : loadcube -what if add a function to grid it to a certain size, say 512x512?
                o so it is possible to combine data with different res.
                o better to do this when plotting?
        TODO : loadcube - More robust loading (detecting the axis etc)?
                o Minimum of different types of data
                    - Naxis 2 (Freq/Vel & Flux/Intensity) - 1D Spectra
                    - Naxis 2 (RA & DEC) - 2D map
                    - Naxis 3 (RA & DEC & Flux/Intensity) 3D Spectral map
                    - Polarization data?
                    (i.e, in SD spectra need to get rid of self.d = self.d[0][0][0])
        TODO : make loadcube delete an axis, along with the hdr keywords if all
               the axis keywords/values are empty/null
                    o only to loaded data, not save to raw data (fits file)
        """
        
        #imports
        from pyfits import open as fitsopen
        #from  sys import
        from os.path import getsize
        from scipy import where, array, nan
        #
    
        # create the class, but without any init script.
        # a class (object) the easy way
        print u'Loading fitsfile :  %s ' % stylify(str(fitsfile),fg='g')
        s  = getsize(fitsfile)
        print " Size %0.2f MB" % (s/(1024.*1024.))
        f = fitsopen(fitsfile)
        self.hdr, self.d = f[0].header, f[0].data
        #self.d = self.d[0] # this is if the stokes axis is present,
        # but it should not be there anymore
        f.close()
    
        #
        #
        # the telescope diameter
        # first check if there was keyword sent in
        if telescope!=None:
            self.hdr.update('TELESCOP', telescope)
            self.telescope = str(telescope)
        #
        if self.hdr.has_key('TELESCOP'):
            #~ name = array(['SMA', 'PDBI', 'JCMT', 'AP-H201-F102', 'IRAM30M'])
            #~ dia = array([6, 15, 15, 12, 30])
            #~ try:
                #~ self.diameter = dia[where(upper(self.hdr['TELESCOP'])==name)][0]
            #~ except IndexError, ex:
                #~ self.diameter = 1
            self.diameter = get_telescope_diameter(self.hdr['TELESCOP'])
            self.telescope = self.hdr['TELESCOP']
        else:
            self.diameter= 1
            self.telescope = None
        if self.hdr.has_key('LINE'):
            self.linename = self.hdr['LINE']
        #
        #
        # spectra: 3 axis and 3rd axis is >1 in size
        # image: 2 axis (or 3 axis, 3rd is =1 in size)
        #
        from numpy import diff, arange
        #naxis = self.hdr['NAXIS']
        #axshape = self.d.shape
        #if axshape[0] array([i>1 for i in a.shape[1:]]).all()
        # an image, only 2 dimensions
        if self.hdr['NAXIS']==2 and self.hdr['NAXIS1']>1 and self.hdr['NAXIS2']>1:
            #if self.hdr['NAXIS']==3 and self.hdr['NAXIS1']>1 and self.hdr['NAXIS2']>1 and self.hdr['NAXIS3']==1:
            # image, not SD spectra or anything,
            # really 2D and greater extent than 1x1
            self.datatype = 'IMAGE'
            pass
        #
        # spectral image cube (extra axis for frequency/velocity)
        elif self.hdr['NAXIS']==3 and self.hdr['NAXIS1']>1 and self.hdr['NAXIS2']>1 and self.hdr['NAXIS3']==1:
            self.datatype = 'IMAGE',2
            # extra if the continuum image has the freq and width
            self.freq = self.hdr['CRVAL3']
            self.freqwidth = self.hdr['CDELT3']
            # remove the extra axis in the data
            self.d = self.d[0]
        # a spectra! the 3rd axis is longer than 1
        elif self.hdr['NAXIS']>=3 and self.hdr['NAXIS3']>1:
            # spectral cube
            # only support for velo-lsr in 3rd axis
            self.datatype = 'CUBE',3
            # load the third axis
            velax = str([x for x in self.hdr.keys() if x[:-1]=='CTYPE' and 'VELO' in self.hdr[x]][0][-1:])
            #data = loadvelocity(data, velax)
            # loading velocity information
            self.veltype = velax
            self.vcrpix = self.hdr['CRPIX'+self.veltype]
            self.vcrval = self.hdr['CRVAL'+self.veltype]
            self.vctype = self.hdr['CTYPE'+self.veltype]
            self.vcdelt = self.hdr['CDELT'+self.veltype]
            self.vnaxis = self.hdr['NAXIS'+self.veltype]
            self.vcdeltkms = self.vcdelt/float(1e3)
            self.velarr = ((arange(1,self.vnaxis+1)-self.vcrpix)*self.vcdelt+self.vcrval)/float(1e3) # so it is i kms
            self.velrangekms = self.velarr.max()-self.velarr.min()
            # not good if vcdletkms has more than 3 significant digits.
            #self.velarr = self.velarr.round(3)
            #self.vcdeltkms = round(self.vcdeltkms,2)
    
            #start = self.vcrval-self.vcdelt*(self.vcrpix-1)
            #stop =  self.vcrval+self.vcdelt*(self.vnaxis-self.vcrpix)
            #arr = arange(start,stop-1,self.vcdelt)/float(1e3)
            #print self.velarr-arr
            # calculate the FOV = 58.4*lambda/D*3600 asec
            self.restfreq = self.hdr['RESTFREQ'] # in Hertz
            self.fov = 58.4*(3.e8/self.restfreq)/float(self.diameter)*3600.
            print 'Field of view: %.2f asecs, for dish size: %.1f m' % (self.fov, self.diameter)
            #print self.veltype, self.vcrpix, self.vcrval, self.vcdeltkms, self.vnaxis
            print 'Velocity range \t: %d km/s' % self.velrangekms
            print 'Velocity step \t: %2.4f km/s' % self.vcdeltkms
            #
            # now if we want to have the spectral array as well to use
            if self.hdr.has_key('RESTFREQ'):
                self.restfreq = self.hdr['RESTFREQ']
            if self.hdr['NAXIS']==4 and  self.hdr['NAXIS4']==1:
                self.d = self.d[0]
            #
            # this was just a test
            # SD pointing spectra
        elif self.hdr['NAXIS']>1 and self.hdr['NAXIS2']==1 and self.hdr['NAXIS3']==1:
            self.datatype = 'SDSPECT',1
            self.vcdelt = self.hdr['DELTAV']
            self.vcdeltkms = self.hdr['DELTAV']/float(1e3)
            self.vcrpix = self.hdr['CRPIX1']
            self.vnaxis = self.hdr['NAXIS1']
            self.vcrval = self.hdr['VELO-LSR']
            self.velarr = ((arange(1,self.vnaxis+1)-self.vcrpix)*self.vcdelt+self.vcrval)/float(1e3)
            self.restfreq = self.hdr['RESTFREQ'] # in Hertz
            self.fov = 58.4*(3e8/self.restfreq)/(self.diameter)*3600
            self.d = self.d[0][0][0] # specific for this data...
        else:
            # if it is not an image or a spectral cube
            print '\n ERROR\nThe dimensions of the data is wrong\n at least the header keywords indicate that.\n The data has '+str(self.hdr['NAXIS'])+' axes. \n\n Perhaps use the removeaxis script?\n\n'
            sysexit(1)
    
            #
            # FREQUENCY ARRAY
            #
            # construct the frequency array!
            # the 3rd axis longer than 1, and 4th axis is the frequency
            # if the data is constructed in gildas
            #
        # DEC
        self.dec_cdelt = self.hdr['CDELT2']*3600 # arcs
        self.dec_npix = self.hdr['NAXIS2']
        self.y_npix = self.hdr['NAXIS2']
        self.dec_crpix = self.hdr['CRPIX2']
        self.dec_crval = self.hdr['CRVAL2']
        # RA
        self.ra_cdelt = self.hdr['CDELT1']*3600 # arcs
        self.ra_npix = self.hdr['NAXIS1']
        self.x_npix = self.hdr['NAXIS1']
        self.ra_crpix = self.hdr['CRPIX1']
        self.ra_crval = self.hdr['CRVAL1']
        try:
            # Beam size in asecs
            self.bmaj = self.hdr['BMAJ']*3600
            self.bmin = self.hdr['BMIN']*3600
            self.bpa = self.hdr['BPA']
        except KeyError, ex:
            self.bmaj = None
            self.bmin = None
            self.bpa = None
        try:
            # Data units
            self.unit = self.hdr['BUNIT']
            self.obj = self.hdr['OBJECT']
        except Exception, ex:
            self.unit = None
        #
        # Object name
        self.obj = self.hdr['OBJECT']
        print '\n','='*40
        print ' '*8,'INFORMATION : FITS file\n'
        print 'Data type : %s' % str(self.datatype[0])
        print 'Object : %s' % self.obj
        if self.datatype[0] != 'SDSPECT':
            self.ra_size = abs(self.ra_cdelt)*self.ra_npix
            self.dec_size = abs(self.dec_cdelt)*self.dec_npix
            print 'Spatial size of image\n RA\t: %2.3f asec\n DEC\t: %2.3f asec' % (self.ra_size, self.dec_size)
        ra_h, ra_m, ra_s = parse_ra(self.ra_crval)
        dec_h, dec_m, dec_s = parse_dec(self.dec_crval)
        print 'Phase center '
        print ' RA : %2d:%2d:%2.4f' % (ra_h,ra_m,ra_s)
        print ' DEC : %2d:%2d:%2.4f' % (dec_h,dec_m,dec_s)
        #
        #return data

    def calc_fov(self):
        # method to calculate FOV after the correct telescope name/diameter
        # has been input and thus correcting the current FOV of 
        # the DataObject
        if self.telescope!=None:
            self.diameter = get_telescope_diameter(self.telescope)
        elif self.diameter == 1:
            print 'You have not changed either the diameter of the telescope or the telescope name'
        self.fov = 58.4*(3.e8/self.restfreq)/float(self.diameter)*3600.
    #~ def add_line(self, name, frequency=None, channels=None):
        #~ try:
            #~ 
        #~ except AttributeError, ex:
            


    
###########################################
# MAIN FUNCTIONS

def plot_spectrum (self,
                   chvals=None,
                   nvals=None,
                   region=[0,0,0,0],
                   source = dict(vsys=0),
                   show_freq=False,
                   font={'family':'serif', 'serif': ['Times New Roman'],
                   'size':8},
                   binning=1,
                   bintype='mean',
                   linefit = dict(type=None, params=[(0.09, 7.3, 3.6)],
                   guess=False, interactive=False, fixlist=None, error=None,
                   limmin=None, minpar=None, limmax=None, maxpar=None, tie=None,
                   lineid=False),
                   send=False,
                   quality=[300, 300],
                   plot_adjust= [0.15, 0.17, 0.98, 0.95],
                   lines = None,
                   axspace = [1., 1., 1., 1.],
                   ylimits=None,
                   telescope=None,
                   fsize=(fig_size)):
    """
    Plot the spectrum of a DataObject
    
    List of available parameters
    and their default value
    ----------
    DataObject
    chvals = None
    nvals = None
    region = [0,0,0,0]
    source = dict(vsys=0)
    show_freq = False
    font = {'family':'serif', 'serif': ['Times New Roman'],'size':8}
    bin = 1
    bintype ='mean'
    linefit = dict(type=None, params=[(0.09, 7.3, 3.6)],
        guess=False, interactive=False, fixlist=None, error=None,
        limmin=None, minpar=None, limmax=None, maxpar=None, tie=None)
    send = False
    quality = [300, 300]
    plot_adjust = [0.15, 0.17, 0.98, 0.95]
    lines = None
    axspace = [1.01, 1.01, 1.01, 1.05]
    ylimits = None
    telescope = None
    fsize = (fig_size)
    
    Description of parameters
    ----------
    DataObject : 
        Optional
        
    chvals : 
        Default : Default = None
        
    nvals : 
        Default : None
        
    region : 
        Default : [0,0,0,0]
        
    source :
        Default : dict(vsys=0)
        
    show_freq :
        Default : False
        
    font : 
        Default : {'family':'serif', 'serif': ['Times New Roman'],'size':8}
        
    bin :
        Default : 1
        
    bintype :
        Default : 'mean'
        
    linefit :
        Default : dict(type=None, params=[(0.09, 7.3, 3.6)],
        guess=False, interactive=False, fixlist=None, error=None,
        limmin=None, minpar=None, limmax=None, maxpar=None, tie=None)
    
    send :
        Default : False
        
    quality : [int. int]
        Default : [300, 300] 
        Set the quality of the saved figure (a) and the displayed figure (b), where [a, b]
        
    plot_adjust :
        Default : [0.15, 0.17, 0.98, 0.95]
        Set the left, bottom, right, top of the axes
    
    lines :
        Default : None
        draw lines with name 'a' & 'c' and rest frequencies b & d.
        if obj_dict=dict(vsys=x) is not null, then it will shift the positions
        of the lines accordingly.
    
    axspace :
        Default : [1.01, 1.01, 1.01, 1.05]
        
    ylimits :
        Default : None
        
    fsize :
        Default : (fig_size)
    
    lineid : boolean
        Default : False
        Use splatsearch module to search the splatalogue for lines?


    TODO : What is the RMS when binning and giving a area_region>1?
                    # RMS is not accounting for binning in vel. axis
                    # RMS is not correct when giving a are_region>1
            ie does the end unit change? yes-> fix it
                    # change x1,x2,y1,y2 to quarter region (line 2350)
                    # change so that when binning, the rms i calculated
            Remove the most weird font-settings
            
    TODO : RMS units, e.g. when using SD data, Kelvin instead of Jy...
    
    TODO : Fix the axspace implementation, must be a better way
    """
    # imports
    #import scipy as sp
    print 'importing...'
    from scipy import array, where, median, std, sign, arange, alen, vstack, \
                    concatenate, sqrt, log10, exp, log, ceil, floor, diff, \
                    flipud, pi, nan
    from string import lower
    import matplotlib.pyplot as pl
    from mpl_toolkits.axes_grid import AxesGrid
    #from matplotlib.patches import Circle
    from matplotlib.ticker import MultipleLocator, FormatStrFormatter
    from matplotlib import cm, rc, rc_params
    print 'done'
    
    #font={'family':'serif','serif':['Times', 'Palatino', 'New Century Schoolbook', 'Bookman', 'Computer Modern Roman'],'size':12, 'weight':'bold'}
    #font=['serif','Times',12,'bold'],\
    #font = {'family':'sans-serif','sans-serif':['Arial', 'Helvetica', 'Avant Garde', 'Computer Modern Sans Serif'], 'cursive':['Zapf Chancery']}
    #'monospace':['Courier','Computer Modern Typewriter'], },\
    #from matplotlib.font_manager import FontProperties
    #FontProperties(family=None, style=None, variant=None, weight=None, stretch=None, size=None, fname=None, _init=None)
    #### 
    #### PARSE INPUT
    #### 

    # formatting
    data_fmt = '%g'         # for normal y and x axis
    freq_data_fmt = '%5.2f' # for the frequency array
    label_X = parse_tick_font(font)
    tick_label_formatter = FormatStrFormatter(label_X.replace('X',data_fmt))
    freq_label_formatter = FormatStrFormatter(label_X.replace('X',freq_data_fmt))
    #rc('mathtext',**{'rm':'sans\\-serif'})
   
    # set the subplot_adjust parameters, if not given a standard set will
    # be used
    pl_left, pl_bottom, pl_right,pl_top = plot_adjust
    # save the channel values (in velocity)
    if chvals!=None:
        v1, v2 = chvals
    velocity = self.velarr - source['vsys'] #now all the velocities are based on the LSR
    velocity_delta = self.vcdeltkms
    #self.freqarr = calc_frequency(self.velarr,self.restfreq)
    #
    # parse the region parameter
    # does it exist?
    # now parse the region keyword
    x1,x2,y1,y2 = parse_region(self, region)
    #
    # now start the plotting
    ###################################
    #      extract the spectra        #
    ###################################
    """
    Extracting spectra, the region keyword gives the region to sum over.
    BUT we have to devide by that area to get back to the correct units(?).
    """
    if self.datatype[0] != 'SDSPECT':
        area_region = ((y2-y1)*(x2-x1))
        spect = (self.d[:,y1:y2,x1:x2].sum(axis=1).sum(axis=1))/float(area_region)
    elif self.datatype[0] == 'SDSPECT':
        area_region = 1
        print stylify("SD-SPECTRUM - region keyword not doing anything.",fg='r')
        spect = self.d
    ####################################
    #          binning of data         #
    ####################################
    # it has to be an integer, for now at least
    if binning != 1:
        binning = int(binning)
        if lower(bintype) == 'resample':
            from congridding import congrid
            # congridding, proper resampling of data
            spect = congrid(spect,(alen(spect)/binning,),centre=True, method='neighbour')
            velocity = congrid(velocity,(alen(velocity)/binning,))
            #
            velocity_delta = self.vcdeltkms*binning
        elif lower(bintype) == 'mean':
            if alen(spect)%binning!=0:
                print 'Bin has to be evenly devide the number of channels: %d' % alen(spect)
                sysexit()
            #  Old method - simple binning, just average
            indices = arange(0,alen(spect),binning)
            spect = array([spect[x:x+binning].sum(axis=0)/binning for x in indices])
            velocity = array([velocity[x:x+binning].sum(axis=0)/binning for x in indices])
            #
            velocity_delta = self.vcdeltkms*binning
        elif binning == 0 or binning <0:
            print stylify("\nERROR:\n Variable \"bin\" has to be 1 for no binning, or above 1 \n\
            for the number of channels to bin")
        # print out information about the binning
        print '='*40
        print ' '*11,"Binning of data\n"
        print "No channels to bin : %d" % binning
        print "Velocity step : %f" % velocity_delta
        if bintype=='mean':
            print 'Type of binning : Simple mean over selected no. bin channels'
        elif bintype=='resample':
            print 'Type of binning : Resampling - 1D interpolation'
    ####################################
    #            return data           #
    ####################################
    if send:
        if nvals!=None and linefit['type']!=None: # send everything!
            txt = '\n sending you spectra, velarr, data, noise-spectra'
            print stylify(txt,fg='g')
            return spect,velocity, data, spect[get_indices(velocity,nvals)]
        elif nvals==None and linefit['type']=='gauss': # no noise channels supplied
            txt = '\n sending you spect, velarr, data'
            print stylify(txt,fg='g')
            return spect,velocity, data
        elif nvals!=None and linefit['type']==None: # no fit but noise
            txt =  '\n sending you spect, velarr, data, noise-spectra'
            print stylify(txt,fg='g')
            return spect, velocity, data, spect[get_indices(velocity,nvals)]
        else: # well non of them are supplied
            txt =  '\n sending you spectra, velarr, data'
            print stylify(txt,fg='g')
            return spect, velocity, data
    # use set_rc here!
    #set_rc

    ################################
    # setting global rc properties #
    ################################
    #rc('savefig', **{'dpi': quality[0]})
    #rc('text', usetex=True)
    #rc('figure',**{'facecolor': '1', 'dpi': quality[1]})
    #to set the global font properties
    #rc('font', **font)
    #rc('axes',linewidth=1)
    #rc('lines', linewidth=0.5, markeredgewidth=0.8)
    #rc('patch',linewidth=0.5)
    # ticksize
    #rc('xtick',**{'minor.size':2, 'major.size':4, 'major.pad': 3})
    #rc('ytick',**{'minor.size':2, 'major.size':4, 'major.pad': 1})
    set_rc()
    ### done!
    pl.ion()
    pl.close()
    fig = pl.figure(1,figsize=fsize)
    #fig = pl.figure(1,figsize=(10.5,4.5))
    fig.clf()
    ax_kms = fig.add_subplot(111)

    # now correct so that negative values are to the left
    if self.vcdelt<0:
        ax_kms.step(flipud(velocity), flipud(spect), 'k',  where='mid')
    elif self.vcdelt>=0:
        ax_kms.step(velocity, spect, 'k', where='mid')
    # if we want som space in the figure
    cx1 = axspace[0]
    cx2 = axspace[1]
    cy1 = axspace[2]
    cy2 = axspace[3]
    xmin, xmax = round(velocity.min()), round(velocity.max())
    ymin, ymax = round(spect.min(),3), round(spect.max(),3)
    sxmin,sxmax = sign(xmin)<0, sign(xmax)<0
    symin,symax = sign(ymin)<0, sign(ymax)<0
    xmin, xmax = xmin*[1/cx1,cx1][sxmin], xmax*[cx2,1/cx2][sxmax]
    ymin, ymax = ymin*[1/cy1,cy1][symin], ymax*[cy2,1/cy2][symax]
    
    if nvals!=None:
        print '='*40
        print ' '*11,'Noise statistics\n'
        # calculate the rms from the channels in the spectra
        # accounts for it even if it is binned
        #
        # image rms
        # change x1,x2,y1,y2 to quarter region
        # change so that when binning, the rms i calculated
        # x1,x2
        if self.datatype[0] == 'SDSPECT':
            rms = sqrt(((self.d[get_indices(velocity,nvals)])**2).mean()/float(binning))
        else:
            zlen, ylen, xlen = self.d.shape
            ydelt = ylen/6
            xdelt = xlen/6
            i1,i2 = xlen/2-xdelt, xlen/2+xdelt
            j1,j2 = ylen/2-ydelt, ylen/2+ydelt
            rms = sqrt(((self.d[get_indices(velocity,nvals),j1:j2,i1:i2])**2).mean()/float(binning))
        rms_mjy = rms*1e3
        #rms_0 = sqrt(((spect[get_indices(velocity,nvals)])**2).mean())
        #rms_2 = sqrt(((self.d[get_indices(velocity,nvals),:,:])**2).mean())

        #rms_0= rms/sqrt(abs(self.vcdeltkms))
        #print rms_0
        #print 'rms_0 =', rms_0*1e3
        #print 'rms_2 =', rms_2*1e3
        #
        # the sensitivity
        s = rms/sqrt(abs(velocity_delta))
        s_mjy = s*1e3
        # the channels used
        ind = get_indices(velocity,nvals)
        ind1, ind2 = ind.min(), ind.max()
        print u'RMS \t\t: %2.3f mJy\u00b7beam\u207b\u00b9\u00b7channel\u207b\u00b9' % rms_mjy
        print u' Sensitivity \t: %2.3f mJy\u00b7beam\u207b\u00b9\u00b7km\u207b\u00b9\u00b7s' % s_mjy
        print u' Channels used \t: %d, %d (%s km\u00b7s\u207b\u00b9)' % (ind1, ind2, str(nvals))
        print u' Region \t: %s arcsec' % (str(region))
        print u' Channel width \t: %2.3f km\u00b7s\u207b\u00b9' % abs(velocity_delta)
        ax_kms.plot([xmin, xmax],[3*rms,3*rms],'b--', alpha=0.7)
        ax_kms.plot([xmin, xmax],[-3*rms,-3*rms],'b--', alpha=0.7)
    #
    # plot dotted lines at y=0 and x=0
    if (velocity<0).any()*(velocity>0).any() or (velocity==0).any():
        ax_kms.plot([xmin-10,xmax+10],[0,0],'g:',[0,0],[ymin-1,ymax+1],'g:')
    else:
        ax_kms.plot([xmin-10,xmax+10],[0,0],'g:')
    #####################
    #   Ticklocations   #
    #####################
    #xmajorLocator = MultipleLocator(5)
    #xminorLocator = MultipleLocator(2.5)
    #ymajorLocator = MultipleLocator(0.05)
    #yminorLocator = MultipleLocator(0.025)

    #ax_kms.xaxis.set_major_locator(xmajorLocator)
    #ax_kms.xaxis.set_minor_locator(xminorLocator)
    #ax_kms.yaxis.set_major_locator(ymajorLocator)
    #ax_kms.yaxis.set_minor_locator(yminorLocator)

    if linefit['type']=='gauss':
        """
        TODO : calculate errors for the fit etc, look at Kaper et al (1966)\
                and Condon (1996).
        TODO : guess parameters?
        TODO : calculate mean and std of the FWHM for the fits
        """
        print '='*40
        print ' '*11,"Line fitting\n"
        #
        fit = linefit.copy()
        if not linefit.has_key('error'):
            if nvals!=None:
                fit['error'] = rms
                print 'No error supplied, but nvals given and rms calculated.\n\
                using rms = %2.3f Jy beam-1 channel-1' % rms
            elif nvals==None:
                errmsg='You have to supply an error to the fit, they\'re kind of important you know.'
                print stylify(errmsg)
                return ; sysexit()

        fwhmfromsig = 2*sqrt(2*log(2)) # the constant
        fwhm = lambda x: fwhmfromsig*x
        sigma = lambda x: x/fwhmfromsig

        # fits up to five (5) 1D gaussian(s) to the spectral data
        if chvals!=None: # if we supplied limits for the fit
            ch = where((velocity>v1)*(velocity<v2))[0]
            Fx = spect[ch]
            X = velocity[ch]
        else: # else use the eveything
            Fx = spect
            X = velocity
        #
        #
        p = fit['params'] # parameters for the fit
        #
        if not fit.has_key('limmin'):
            fit['limmin'] = None
            fit['minpar'] = None
        if not fit.has_key('limmax'):
            fit['limmax'] = None
            fit['maxpar'] = None
        if not fit.has_key('fixlist'):
            fit['fixlist'] = None
        if not fit.has_key('tie'):
            fit['tie'] = None
        #
        from time import time
        t1= time()
        #
        params, errors, chi2, mp = fit_gauss1d((X,Fx), params=p, fixlist=fit['fixlist'], \
                minbool=fit['limmin'], minpar=fit['minpar'], \
                maxbool=fit['limmax'], maxpar=fit['maxpar'], \
                err=fit['error'], tie=fit['tie'], verbose=0, full_output=1)
        #
        print ' Done in %2.3f seconds \n' % (time()-t1)

        #
        print ' Number of fits : ', alen(params)/3
        print ' Fit status : ', mp.status, '(if 0, it should have halted)\n'
        # now, parse output of fitting and print it out on screen
        j = 1
        line_widths = []
        frequencies = []
        for i in arange(0,len(params),3):
            # add 1 because channel 1 is in pos 0
            half_fwhm = params[i+2]/2
            fwhm = params[i+2]
            line_widths.append(fwhm)
            # first figure out the extent of the gaussian (the line)
            # jump half a channel down and up so that it finds the correct channels
            lower_half, upper_half = (params[i+1] + array([-1,1])*half_fwhm)
            lower,upper = (params[i+1] + array([-1,1])*fwhm)
            #
            #channels = where((velocity>lower)*(velocity<upper))[0]+1
            channels_half_nobin = get_indices(velocity,[lower_half,upper_half])
            channels_nobin = get_indices(velocity,[lower,upper])
            channels_half = get_indices(velocity,[lower_half,upper_half])
            channels = get_indices(velocity,[lower,upper])
            frequency = calc_frequency(params[i+1],self.restfreq/1e9)
            frequencies.append(frequency)
            print  'Fit number : %i' % j
            print  ' Intensity : %2.4f \t=calculate it=' % (sqrt(2*pi)*sigma(params[i+2])*params[i]) # the area under the 1D Gaussian
            print u' Amplitude : %2.3f (\u00b1%2.3f) \t Jy\u00b7Beam\u207b\u00b9' % (params[i],errors[i])
            print u' Position  : %2.3f (\u00b1%2.3f) \t km\u00b7s\u207b\u00b9' % (params[i+1],errors[i+1])
            print u' Width     : %2.3f (\u00b1%2.3f) \t km\u00b7s\u207b\u00b9 (FWHM, \u03c3=%2.3f)' % (params[i+2],errors[i+2], sigma(params[i+2]))
            print  ' Frequency : %3.9f GHz' % frequency
            print u' \u00b1FWHM     : %d to %d (%d) [%.2f to %.2f km/s]'% (channels_half_nobin.min(), channels_half_nobin.max(),(channels_half_nobin.max()-channels_half_nobin.min()+1), lower_half, upper_half)
            print u' \u00b12*FWHM   : %d to %d (%d) [%.2f to %.2f km/s]' % (channels_nobin.min(), channels_nobin.max(), (channels_nobin.max()-channels_nobin.min()+1), lower,upper)
            if bin!=1:
                print u' Rebinned channels :\n \t FWHM width  : %d to %d (\u00b1FWHM)' % (channels_half.min(), channels_half.max())
                print  ' \t 2*FWHM width : %d to %d (%d)  \n' % (channels.min(), channels.max(),(channels.max()-channels.min()+1))
            j+=1
        #
        line_widths = array(line_widths)
        print 20*'- '
        print u'Mean FWHM : %2.1f \u00b1%2.2f km\u00b7s\u207b\u00b9' % (line_widths.mean(),line_widths.std())
        if send: # does this clause do anything? sending this way earlier...
            j = 1
            f = []
            for i in arange(1,len(params),3):
                nu = calc_frequency(params[i],self.restfreq/1e9)
                f.append(nu)
                print '%3.9f' % nu
                j+=1
        # draw the fit(s) into the figure
        # X is the velocity array
        # xarr has more 3 times more datapoints than velocity array
        # the plotted lines looks smoother and nicer that way
        xarr = arange(X[0],X[-1],(diff(X)[0]/3))
        for i in arange(0,len(params),3):
            lower,upper = (params[i+1] + array([-1,1])*fwhm*4)
            channels = get_indices(xarr,[lower,upper])
            ax_kms.plot(xarr[channels], gauss1d(xarr[channels],params[i:i+3]))
        ax_kms.plot(xarr, gauss1d(xarr,params), color='0.2', lw=1, alpha=0.6)
        #
        if linefit.has_key('lineid'):
            if linefit['lineid']:
                # later when the kwargs is implemented...
                # checks that we have done a fit first
                #if not kwargs['linefit']:
                #    print 'If you want lineid you need linefit'
                #    raise ParError(kwargs['lineid'], kwargs['linefit'])
                import splatsearch as spl
                print 'Trying to indentify candidates for the fitted lines.'
                frequency_pairs = []
                for i in arange(0,len(params),3):
                    vel_lower, vel_upper = (params[i+1] + array([-1,1])*fwhm*1.5)
                    # frequency increases when velocity decreases...
                    freq_lower = calc_frequency(vel_upper,self.restfreq/1e9)
                    freq_upper = calc_frequency(vel_lower,self.restfreq/1e9)
                    frequency_pairs.append([freq_lower,freq_upper])
                list_of_species = []
                list_of_frequencies = []
                number = 1
                for i in arange(len(frequency_pairs)):
                    df=8e-3 # range to find line
                    CSI = "\x1b["
                    start =CSI+'1m'+CSI+'32m'+CSI+'40m'
                    end = CSI+'m'
                    print '\n'+start+'Line number : '+str(number)+'\t\t\t\t'+end
                    print 'Frequency : %f  GHz' % (frequencies[i])
                    result = spl.splatsearch(freq=frequency_pairs[i], send=1, display=1, linelist=['jpl','cdms'], e_to=500)
                    if result!=None:  
                        species, freq = result[1],result[3]
                        for i in arange(len(freq)):
                            list_of_species.append(species[i])
                            list_of_frequencies.append(freq[i])
                        #~ for i in arange(len(freq)):
                            #~ if i>0 and freq[i]!=freq[i-1]: # remove duplicates
                                #~ list_of_species.append(species[i])
                                #~ list_of_frequencies.append(freq[i])
                            #~ elif i==0:
                                #~ list_of_species.append(species[i])
                                #~ list_of_frequencies.append(freq[i])
                            #~ else:
                                #~ pass
                    
                    number+=1
                # done now define the linelist
                lines=[list_of_species,list_of_frequencies]
            else:
                print ('Not identifying lines...')
        
    #
    if lines!=None:
        print u'Marking the lines, using %2.2f km\u00b7s\u207b\u00b9' % source['vsys']
        if type(lines[-1]) in [type(1),type(1.0)]:
            # to be able to add a frequency shift to the linelist
            # to move the markings
            print ('this is very crude implemented, change/remove if it conflicts.')
            lines_vobs = lines[-1]
            lines = lines[0]
        else:
            # so that we do not have to think about if we created it later
            lines_vobs = 0
        lines = parse_linelist(lines)
        v = array([calc_vlsr(float(lines[i+1])*1e9,self.restfreq) for i in arange(0, len(lines), 2)]) + lines_vobs
        colors8 = ['#95B200','#2A3702','#71AEDB','#6D001D','#4B8618', '#DDB61D', '#DC3A0C', '#003B73']
        colors7 = ['#95B200','#71AEDB','#6D001D','#4B8618', '#DDB61D', '#DC3A0C', '#003B73']
        if len(lines)/2 == 8:
            colors = colors8
        elif len(lines)/2 == 7:
            colors = colors7
        elif len(lines)/2 not in [6, 8]:
            colors = ['k']*len(lines)
        x = 0
        for i,j in zip(arange(0, len(lines), 2), arange(0, len(lines),1)):
            # only check for lines behind the new line
            no_dbl = len(where(array(v)[0:j].round(0) == round(v[j],0))[0])
            put_line_indicator(ax_kms, velocity, spect, v[j], lines[i],lc=colors[x], offset=no_dbl, text_color=colors[x])
            #put_line_indicator(ax_kms, velocity, spect, v[j], lines[i],lc='k', offset=no_dbl)
            # verbose output
            #print u'Line %1d : %2.2f\t km\u00b7s\u207b\u00b9 (%2.3f)' % (j+1,v[j],v[j]+obj_dict['vsys'])
            x+=1
    #
    ax_kms.set_xlim(xmin,xmax)
    if lines!=[]:
        ax_kms.set_ylim(ymin,ymax+ymax*0.4)
    else:
        ax_kms.set_ylim(ymin,ymax)
    if ylimits!=None:
        ax_kms.set_ylim(ylimits)
    #ax_kms.set_title(self.obj)
    ax_kms.text(0.07,0.87 ,self.obj, transform=ax_kms.transAxes)
    ax_kms.set_xlabel('$v$ [km s$^{-1}$]')
    if self.unit=='Jy/beam':
        ax_kms.set_ylabel('$I$ [Jy beam$^{-1}$]')
    else:
        ax_kms.set_ylabel('$I$ ['+self.unit+']')
    # to show the channel numbers
    if show_freq==True:
        # create the frequency axis
        ax_hz = ax_kms.twiny()
        # change the font of the ticks
        # this messes things up!
        #ax_hz.set_xticklabels(ax_hz.get_xticks(),ffont)
        #ax_hz.set_yticklabels(ax_hz.get_yticks(),ffont)

        # to load special fonts
        # rc('text.latex',preamble='\usepackage[bitstream-charter]{mathdesign}')
        ax_hz.xaxis.set_major_formatter(freq_label_formatter)
        # removed the set_minor_locator settings below because there
        #   where to many ticks (wide spectra)
        #ax_hz.xaxis.set_minor_locator(MultipleLocator(0.001))

        x_1, x_2 = ax_kms.get_xlim()
        # i want the frequency in GHz so, divide by 1e9
        ax_hz.set_xlim(calc_frequency(x_1,self.restfreq/1e9), calc_frequency(x_2,self.restfreq/1e9))
        pl_top -= 0.1
        pl.xticks(rotation=40,horizontalalignment ='left')
    #
    #elif lines!=[] and obj_par['vsys']==0:
    #    print('please, input a vsys!=0')
    #    return ; sysexit()
    #ax_kms.xaxis.set_major_formatter(tick_label_formatter)
    #ax_kms.yaxis.set_major_formatter(tick_label_formatter)

    #ax_kms.set_xticklabels(ax_kms.get_xticks(),ffont)
    #ax_kms.set_yticklabels(ax_kms.get_yticks(),ffont)
    ax_kms.minorticks_on()
    #for tick in ax_kms.xaxis.get_major_ticks():
    #    tick.label.set_family('Arial')
    #pl.show()
    #pl.draw()
    pl.subplots_adjust(left=pl_left, bottom=pl_bottom, right=pl_right, top=pl_top)

    #pl.show()

    #pl.ioff()
    #
#
def plot_moment0 (self,
                cfile=None,
                chvals=None,
                nvals=None,
                region=[0,0,0,0],
                nx=6,
                filled=True,
                box=[0,0],
                nsig=3,
                nsjump=2,
                source = dict(vsys=0,dist=250),
                font={'family':'serif', 'serif': ['Times New Roman'],
                'size':8},
                fit = dict(gauss = None, params = None, continuum = False,
                    interactive = False),
                send=False,
                quality=[300, 300],
                cbar=True,
                colormap=True,
                plot_adjust= [0.13, 0.06, 0.75, 0.99],
                cpeak=[0,0,'k'],
                ccol='k',
                sbar=dict(au=200),
                locators = [2,1],
                telescope=None,
                negcontours=True,
                fsize=(one_col_fig_width,one_col_fig_width*0.8)):
    """

    Function doc

    params = [height, amplitude, x0, y0, width_x, width_y, rota]
    TODO : For drawing size bar, add keywords to control it
    TODO : Change fit-routine to MPFIT
    TODO : Fix the RMS/sensitivity/sigma calculation units
    cpeak, continuum peak
    """


    # imports
    #import scipy as sp
    from scipy import array, where, median, std, sign, arange, alen, vstack, \
    concatenate, sqrt, log10, ones, sqrt, flipud
    #import pyfits as pf
    from time import sleep
    import matplotlib.pyplot as pl
    #from matplotlib.patches import Circle
    from matplotlib.ticker import MultipleLocator, FormatStrFormatter
    from matplotlib import cm, rc
    #


    ################################
    # setting the tick label font  #
    ################################
    # we are using latex formatting here!
    # following sets the ticklabel format string
    data_fmt = '%g'         # for normal y and x axis
    cbar_data_fmt = '%2.2f'         # for normal y and x axis
    label_X = parse_tick_font(font)
    tick_label_formatter = FormatStrFormatter(label_X.replace('X',data_fmt))
    cbar_tick_label_formatter = FormatStrFormatter(label_X.replace('X',cbar_data_fmt))


    pl_left, pl_bottom, pl_right,pl_top = plot_adjust

    #
    # first get the fitsfile
    #~ linedata = loadcube(filename,telescope)
    linedata = self
    #
    if not source.has_key('vsys'):
        source['vsys'] = 0
    # this will make it add vsys to the object everytime, not good!!
    linedata.velarr = linedata.velarr - source['vsys'] #now all the velocities are based on the LSR

    # and the continuum data, if existent
    if cfile != None:
        contdata = loadcube(cfile)
    # parse the channel values
    if chvals!=None:
        v1, v2 = chvals
    # parse the region, get the area for the spectra
    x1,x2,y1,y2 = parse_region(linedata, region)
    # if any is limits are None, draw spectra and ask for them/it
    # INTERACTIVE
    if nvals==None or chvals==None:
        # draw spectrum
        plot_spectrum(linedata,region=region, source= {'vsys': source['vsys']})
        #
        # if there is no channels supplied
        if chvals==None:
            v1, v2 = array(raw_input('input the limits, comma separated: ').split(','), dtype ='float')
        if nvals==None:
            # ask for noise calculation velocity limits
            try:
                nvals = array(raw_input('input the noise limits (velocity). comma separated: ').split(','), dtype='float')
                if len(nvals)==4:
                    n1, n2, n3, n4 = nvals
                elif len(nvals)==2:
                    n1, n2 = nvals
            except (ValueError):
                print_warning('Since you did not input any values\n or input was wrong we will guess some values...\n')
                sleep(1)
                nvals = None
        pl.close(1)

    # calculate common stuff
    ### for the plotting box
    ylen, xlen = linedata.d[0].shape
    ycoords = arange(-ylen/2,ylen/2,1)*linedata.dec_cdelt
    xcoords = arange(-xlen/2,xlen/2,1)*linedata.ra_cdelt
    #
    # for the extent keyword
    left, right = xcoords[0],xcoords[-1]
    bottom, top = ycoords[0],ycoords[-1]
    #
    # parse the noise channel values
    if nvals!=None:
        # if noise has been input
        noise_channels = get_indices(linedata.velarr, nvals)
    #
    else:
        # if user didnt input noise velocity limits
        # choose channels away from the choosen (red blue) lines
        low = where((linedata.velarr>(linedata.velarr.min()+10))*(linedata.velarr<(v1-10)))[0]
        high = where((linedata.velarr>(v2+10))*(linedata.velarr<(linedata.velarr.max()-10)))[0]
        noise_channels = concatenate((low, high))
    #
    # the region to calculate the rms in
    i1,i2 = xlen/2+array([-1,1])*xlen/4
    j1,j2 = ylen/2+array([-1,1])*ylen/4

    # the noise, rms
    noise = linedata.d[noise_channels]
    rms = sqrt(((noise[:,j1:j2,i1:i2])**2).mean())

    # set boundaries
    if box == [0,0]:
        i1,i2 = left,right
        j1,j2 = bottom,top
    elif box != [0,0]:
        i1,i2 = array([-1,1])*box[0]/2.*sign(linedata.ra_cdelt)
        j1,j2 = array([-1,1])*box[1]/2.*sign(linedata.dec_cdelt)

    # get the channels
    #img_channels = where((linedata.velarr>v1)*(linedata.velarr<v2))[0]
    img_channels = get_indices(linedata.velarr,[v1,v2])
    imgs = linedata.d[img_channels]
    #
    # do the summing
    #
    # M1 = dv * sum(I(a,b,vi))_x1^x2
    #
    img = imgs.sum(axis=0)*abs(linedata.vcdeltkms)
    img_sigma = calc_sigma(alen(imgs), rms, linedata.vcdeltkms)
    #
    img_max = img.max()
    img_min = img.min()
    #
    # now create the levels for the contours
    if negcontours:
        levs = concatenate((-1*flipud(arange(nsig*img_sigma,abs(img_min)+img_sigma,nsjump*img_sigma)), arange(nsig*img_sigma,img_max+img_sigma,nsjump*img_sigma)))
        levs_contour = concatenate((-1*flipud(arange(nsig*img_sigma,abs(img_min)+img_sigma,2*nsjump*img_sigma)), arange(nsig*img_sigma,img_max+img_sigma,2*nsjump*img_sigma)))
    else:
        levs = arange(nsig*img_sigma,img_max+img_sigma,nsjump*img_sigma)
        levs_contour = arange(nsig*img_sigma,img_max+img_sigma,2*nsjump*img_sigma)
    #levs = arange(nsig*img_sigma, img_max, nsjump*img_sigma)
    # print some info out
    print '\n','='*40
    print ' '*8,'INFORMATION : Line data'
    print '='*40
    print '\n Summing from channel %3d to %3d' % (img_channels.min(), img_channels.max())
    print ' RMS \t\t: %2.3f \tmJy/beam/channel\n Sigma \t\t: %2.3f \tmJy/beam/km/s' % (1e3*rms, 1e3*img_sigma)
    print ' Map min/max \t: %2.2f/%2.2f \tmJy/beam/km/s' % (1e3*img_min, 1e3*img_max)
    print ' Start sigma \t: %2.3f (%1.1f) \tmJy/beam/km/s\n Sigma step \t: %2.3f (%1.1f) \tmJy/beam/km/s\n' % (1e3*nsig*img_sigma, nsig, 1e3*nsjump*img_sigma, nsjump)
    #
    # tick density
    majorLocator = MultipleLocator(locators[0])
    minorLocator = MultipleLocator(locators[1])

    if send==True:
        if cfile!=None:
            print 'sending you things'
            return img, levs,levs_contour, img_sigma, (left,right,bottom,top), linedata, contdata
        if cfile==None:
            print 'sending you : img, levs,levs_contour, imgs_sigma, extent, data'
            return img, levs, levs_contour,img_sigma, (left,right,bottom,top), linedata

    ################################
    # setting global rc properties #
    ################################
    set_rc()



    pl.ion()
    pl.close()
    fig = pl.figure(1, figsize=fsize)
    fig.clf()
    #
    ax = fig.add_subplot(111)
    #
    # print beam parameters for the data
    gain = 8.168e-25*(linedata.restfreq)**2*linedata.bmin*linedata.bmaj
    print '='*40
    print ' '*15,'BEAM(S)'
    print '='*40
    print 'Line cube:'
    print u' Minor (FWHM)\t: %2.3f \tasec' % linedata.bmin
    print u' Major (FWHM)\t: %2.3f  \tasec' % linedata.bmaj
    print ' PA \t\t: %2.3f \tDegrees (0<theta<180)' % linedata.bpa
    print u' Gain\t\t: %2.4f \tJy\u00b7K\u207b\u00b9\n' % gain
    #
    #
    if cfile != None:
        cont = ax.imshow(contdata.d, cmap=cm.gray_r, extent=(left,right,bottom,top))
        if cbar:
            cb = pl.colorbar(cont)
            cb.ax.set_ylabel(str(contdata.unit))

        print '-'*40
        print 'Continuum data:'
        print u' Minor (FWHM)\t: %2.3f \tasec' % contdata.bmin
        print u' Major (FWHM)\t: %2.3f  \tasec' % contdata.bmaj
        print ' PA \t\t: %2.3f Degrees (0<theta<180) \n' % contdata.bpa
    #
    #
    if colormap and filled==True:
        colormap = cm.bone_r
    if colormap == None or filled==False:
        # just contours
        levs = levs.round(3)
        levs_contour = levs_contour.round(3)
        cs = ax.contour(img, levs_contour, colors=ccol, extent=(left,right,bottom,top))
    elif cfile == None and colormap!=None:
        levs = levs.round(3)
        levs_contour = levs_contour.round(3)
        cs1 = ax.contourf(img, levs, cmap=colormap, extent=(left,right,bottom,top))
        #cs2 = ax.contour(img, cs1.levels[::2], colors=ccol, extent=(left,right,bottom,top))
        #return cs1 
        cs2 = ax.contour(img, levs_contour, colors=ccol, extent=(left,right,bottom,top))
        cbar = pl.colorbar(cs1, ticks=levs_contour, format=cbar_tick_label_formatter)#label_X.replace('X','%2.2f'))
        cbar.add_lines(cs2)
        if str(linedata.unit) == 'Jy/beam':
            cbar.ax.set_ylabel(r'Jy\,beam$^{-1}$')
        else:
            cbar.ax.set_ylabel(str(linedata.unit))
    else:
        line = ax.contour(img, levels=levs, colors='r', extent=(left,right,bottom,top))
    
    #ax.text(0.5,0.5,'test',transform = ax.transAxes)
    draw_beam(ax, linedata)
    draw_fov(ax, linedata)

    if 'au' in sbar.keys() and 'dist' in source.keys():
        draw_sizebar(ax,linedata,dist=source['dist'],au=sbar['au'])
    elif 'dist' in source.keys():
        draw_sizebar(ax,linedata,dist=source['dist'])
    else :
        raise ParError(sbar)
    if len(cpeak) == 3:
        mark = cpeak[2]
        xmark, ymark = cpeak[0:2]
    elif len(cpeak) >4:
        xmark = cpeak[0:-1:2]
        ymark = cpeak[1:-1:2]
        mark = cpeak[-1]
    else:
        mark = '+k'
    cross = ax.plot(xmark, ymark, mark, ms=6)#, mew=3, alpha=0.9)



    #
    ax.xaxis.set_major_formatter(tick_label_formatter)
    ax.yaxis.set_major_formatter(tick_label_formatter)

    ax.xaxis.set_major_locator(majorLocator)
    ax.xaxis.set_minor_locator(minorLocator)
    ax.yaxis.set_major_locator(majorLocator)
    ax.yaxis.set_minor_locator(minorLocator)

    #pl.setp(ax.get_xticklabels(),family='sans-serif')
    #pl.setp(ax.get_yticklabels(),family='sans-serif')

    ax.set_xlabel('RA Offset ($^{\prime\prime}$)')
    ax.set_ylabel('Dec Offset ($^{\prime\prime}$)')
    #fig.suptitle(linedata.obj+' (%s km s$^{-1}$)'% str(linedata.unit))
    #if cfile!=None:
    #    fig.subplots_adjust(bottom=0.08, right=0.77, top=0.90)
    if source.has_key('source'):
        ax.text(0.05,0.93, source['source'], transform = ax.transAxes)
    else:
        ax.text(0.05,0.93, linedata.obj, transform = ax.transAxes)
    ax.set_xlim(i1,i2)
    ax.set_ylim(j1,j2)
    ax.set_aspect(1)
    #
    #
    pl.subplots_adjust(left=pl_left, bottom=pl_bottom, right=pl_right, top=pl_top)

    if fit['gauss'] == '2d':
        #from gaussfitter2 import gaussfit
        """

        OLD FITTING ROUTINE, GAUSSFIT2D.PY
        SHOULD BE MOVED TO THE NEW ROUTINE MPFIT

        gaussfit(data,err=None,params=[],autoderiv=1,return_all=0,circle=0,rotate=1,vheight=1)
        params = [height, amplitude, x0, y0, width_x, width_y, rota]

        """
        print '\n-------------------------------\n2D Gaussian(s) fitting...\n'
        from scipy import sqrt, log, pi, tan, rot90, meshgrid

        #a = gaussfit(img) # fits xsig wrong in rel to x0
        if cfile != None and fit['continuum'] == True:
            print' Fitting to continuum data\n'
            Z = contdata.d[y1:y2,x1:x2]
            D = contdata
        else:
            print' Fitting to integrated line data'
            Z = img[y1:y2,x1:x2]
            D = linedata

        try:
            p = fit['params']
        except KeyError:
            p = None

        #
        # get the data coordinates, to fit over them!
        X, Y = meshgrid(array(xcoords)[x1:x2],array(ycoords)[y1:y2])

        #X = ones(Z.shape)*array(xcoords)[x1:x2]
        #Y = ones(Z.shape)*array(ycoords)[y1:y2]
        #return xcoords, ycoords, Z
        #print X,Y
        #u = indices(Z.shape)[1]
        #v = indices(Z.shape)[0]
        #
        # now do the fitting
        #
        params, success, no_fits = gaussfit2d((X,Y,Z), params=p)
        #
        # what we get in params is now
        # params[0] = the baseline
        # params[1] = peak
        # params[2] = x0
        # params[3] = y0
        # params[4] = xsig
        # params[5] = ysig
        #
        # some help functions to go to/from fwhm and sigma
        fwhmfromsig = 2*sqrt(2*log(2)) # the constant
        fwhm = lambda x: fwhmfromsig*x
        sigma = lambda x: x/fwhmfromsig
        #
        print ' Number of fits\t: %d' % no_fits
        print ' Success \t: %d \t(if over 4, not good)' % success
        print u' Baseline \t: %2.3e\tJy\u00b7beam\u207b\u00b9\u00b7km\u00b7s\u207b\u00b9\n' % params[0]
        #
        j = 1
        for i in arange(1,len(params),6):
            #
            #
            # parse the fit stuff to asec, maj/min axis etc
            # the errors are 0 here, for the future implementation of errors
            fwhm1, fwhm2, sfwhm1, sfwhm2, pa, spa = parse_gau2dfit(fwhm(params[i+3]),fwhm(params[i+4]),0,0,params[i+5],0)
            #
            # peak flux, S_peak
            s_peak = params[i]
            #
            # transform to pixel coordinates, not data coordinates
            # in data coordinates
            xoset, yoset  = (params[i+1], params[i+2])
            # get the pixel coordinates, needed to calc RA & DEC
            # f=True for returning the sub-pixel position
            x0, t1, y0,t2 = parse_region(D, [xoset, yoset, 0],f=True)
            # parse the coordinates into offsets
            #xoset, yoset = parse_pxlcoord(D, x0, y0)

            #xsigpxl = params[i+3]
            #ysigpxl = params[i+4]
            #
            # sigma
            sigmaj = sigma(fwhm1)
            sigmin = sigma(fwhm2)

            #
            # calculate the ra & dec coord
            # convert to degrees
            ra = (x0+1-D.ra_crpix)*D.ra_cdelt/3600 + D.ra_crval
            #ra = (D.ra_npix/2 - D.ra_crpix+1)*D.ra_cdelt/3600 + D.ra_crval + xoset
            a1,a2,a3 = parse_ra(ra)
            dec = (y0+1-D.dec_crpix)*D.dec_cdelt/3600 + D.dec_crval
            b1,b2,b3 = parse_dec(dec)
            #
            # the total flux (keep track of units)
            ftot = (s_peak*fwhm1*fwhm2/(D.bmaj*D.bmaj))

            print 'Fit no. : ', j
            print u' Flux \t\t: %2.5f \tJy\u00b7km\u00b7s\u207b\u00b9' % ftot
            print u' Peak \t\t: %2.5f \tJy\u00b7beam\u207b\u00b9\u00b7km\u00b7s\u207b\u00b9' % s_peak
            print ' RA Offset \t: %2.5f \tasec  RA: %02d:%2d:%2.3f' % (xoset, a1, a2, a3)
            print ' DEC Offset \t: %2.5f \tasec DEC: %02d:%2d:%2.3f' % (yoset, b1, b2, b3)
            print u' Major (FWHM)\t: %2.3f \tasec (\u03c3=%2.3f)' % (fwhm1, sigmaj)
            print u' Minor (FWHM)\t: %2.3f \tasec (\u03c3=%2.3f)' % (fwhm2, sigmin)
            print ' PA \t\t: %2.3f \tdegrees (-90<theta<+90) \n' % pa

            a, b, c, ok = gauss2d_decon ((fwhm1, fwhm2, pa, D.bmaj, D.bmin, D.bpa), ang='deg')

            print 'Deconvolved sizes:'
            print ' Major axes \t: %2.3f (asec)' % a
            print ' Minor axes \t: %2.3f (asec)' % b
            print ' PA \t\t: %2.3f (degrees)\n' % c
            j+=1
#
def plot_moment1 (self,
                cfile=None,
                chvals=None,
                nvals=None,
                region=[0,0,0,0],
                nx=6,
                filled=True,
                box=[0,0],
                nsig=3,
                nsjump=2,
                obj_dict = dict(vsys=0),
                font={'family':'serif', 'serif': ['Times New Roman'],
                'size':17},
                fit = dict(gauss = None, params = None, continuum = False,
                interactive = False),
                send=False,
                quality=[150, 72],
                plot_adjust= [0.12, 0.01, 0.74, 0.99],
                cpeak=[0,0,'k'],
                ccol='r',
                sbar=dict(dist=250,au=200),
                locators = [2,1],
                telescope=None,
                type=1,
                fsize=(9.,7.),
                negcontours=True,):
    """
    Plot moment1 map of an area

    M1 = sum(vi * )



    ddir=substwid('~/')+"work/data/iram/h218o/"

    ; This block simply to read-in the data...
    va_l=[1.0]
    line=readfits(ddir+"line.fits",header)
    map_head,header,xa_l,ya_l,vaxis=va_l

    ; Select which part of the velocity axis to consider
    vx=where(va_l ge 6.0 and va_l le 8.0)

    ; Here we calculate the zeroth and first moments.
    dmom=fltarr(n_elements(xa_l),n_elements(ya_l),2)
    for i=0,n_elements(xa_l)-1 do begin
      for j=0,n_elements(ya_l)-1 do begin
        dmom(i,j,0)=total(line(i,j,vx)) ; Calculate moment-0.
        if dmom(i,j,0) ge 0.1           # if enough signal calculate moment-1
            then
            dmom(i,j,1)=total(reform(line(i,j,vx))*va_l(vx))/dmom(i,j,0)
        else
            dmom(i,j,1)=-99.0
      end
    end

    ; Do the plotting.
    set_plot,'ps'
    device,file=substwid("~/")+"work/ps/iram/iras4b/h218o_mom1.eps",xsize=6.0*0.8/0.6,ysize=6.0,/inch,/color,/cmyk & presentation
    loadct,6
    !P.POSITION=[0.15,0.15,0.75,0.95]
    lvls=0.15*findgen(61)/60.0+6.8

    ; The actual image and contours.
    contour,dmom(*,*,1),xa_l,ya_l,xrange=[1,-1],yrange=[-1,1],levels=lvls,/fill,c_color=250-findgen(61)*4.0,charsize=1.5,xtitle='!5RA offset ["]',ytitle='DEC offset ["]',xstyle=1,ystyle=1
    contour,dmom(*,*,0),xa_l,ya_l,xrange=[1,-1],yrange=[-1,1],levels=(0.05*findgen(20)+0.1),/over

    colorbar,ncolors=250,bottom=1,minrange=min(lvls),maxrange=max(lvls),position=[0.80,0.15,0.85,0.95],/vertical,charsize=1.5,divisions=6,FORMAT='(F5.2)',/right,/reverse
    """


    # imports
    #import scipy as sp
    from scipy import array, where, median, std, sign, arange, alen, vstack, \
    concatenate, sqrt, log10, ones, nan, flipud
    #import pyfits as pf
    import matplotlib.pyplot as pl
    #from matplotlib.patches import Circle
    from matplotlib.ticker import MultipleLocator, FormatStrFormatter
    from matplotlib import cm, rc
    #

    ################################
    # setting the tick label font  #
    ################################
    # we are using latex formatting here!
    # following sets the ticklabel format string
    data_fmt = '%g'         # for normal y and x axis
    cbar_data_fmt = '%2.2f'         # for normal y and x axis
    label_X = parse_tick_font(font)
    tick_label_formatter = FormatStrFormatter(label_X.replace('X',data_fmt))
    cbar_tick_label_formatter = FormatStrFormatter(label_X.replace('X',cbar_data_fmt))

    pl_left, pl_bottom, pl_right,pl_top = plot_adjust

    #
    # first get the fitsfile
    #~ linedata = loadcube(filename,telescope)
    linedata = self
    #
    linedata.velarr = linedata.velarr - obj_dict['vsys'] #now all the velocities are based on the LSR

    # parse the channel values
    if chvals!=None:
        v1, v2 = chvals
    # parse the region, get the area for the spectra
    x1,x2,y1,y2 = parse_region(linedata, region)
    # if any is limits are None, draw spectra and ask for them/it
    # INTERACTIVE
    if nvals==None or chvals==None:
        # draw spectrum
        plot_spectrum(filename,region=region, obj_dict= {'vsys': obj_dict['vsys']})
        #
        # if there is no channels supplied
        if chvals==None:
            v1, v2 = array(raw_input('input the limits, comma separated: ').split(','), dtype ='float')
        if nvals==None:
            # ask for noise calculation velocity limits
            try:
                nvals = array(raw_input('input the noise limits (velocity). comma separated: ').split(','), dtype='float')
                if len(nvals)==4:
                    n1, n2, n3, n4 = nvals
                elif len(nvals)==2:
                    n1, n2 = nvals
            except (ValueError):
                print "Since you did not input any or input was wrong we will guess some values..."
                nvals = None
        pl.close(1)

    # calculate common stuff
    ### for the plotting box
    ylen, xlen = linedata.d[0].shape
    ycoords = arange(-ylen/2,ylen/2,1)*linedata.dec_cdelt
    xcoords = arange(-xlen/2,xlen/2,1)*linedata.ra_cdelt
    #
    # for the extent keyword
    left, right = xcoords[0],xcoords[-1]
    bottom, top = ycoords[0],ycoords[-1]
    #
    # parse the noise channel values
    if nvals!=None:
        # if noise has been input
        noise_channels = get_indices(linedata.velarr, nvals)
    #
    else:
        # if user didnt input noise velocity limits
        # choose channels away from the choosen (red blue) lines
        low = where((linedata.velarr>(linedata.velarr.min()+10))*(linedata.velarr<(v1-10)))[0]
        high = where((linedata.velarr>(v2+10))*(linedata.velarr<(linedata.velarr.max()-10)))[0]
        noise_channels = concatenate((low, high))
    #
    # the region to calculate the rms in
    i1,i2 = xlen/2+array([-1,1])*xlen/4
    j1,j2 = ylen/2+array([-1,1])*ylen/4

    # the noise, rms
    noise = linedata.d[noise_channels]
    rms = sqrt(((noise[:,j1:j2,i1:i2])**2).mean())

    # set boundaries
    if box == [0,0]:
        i1,i2 = left,right
        j1,j2 = bottom,top
    elif box != [0,0]:
        i1,i2 = array([-1,1])*box[0]/2.*sign(linedata.ra_cdelt)
        j1,j2 = array([-1,1])*box[1]/2.*sign(linedata.dec_cdelt)

    img_channels = get_indices(linedata.velarr,[v1,v2])
    imgs = linedata.d[img_channels]
    #
    # do the summing
    #
    # M1 = dv * sum(I(a,b,vi))_x1^x2
    # or perhaps without dv to save calc?
    moment0 = imgs.sum(axis=0)*abs(linedata.vcdeltkms)
    moment0_sigma = sqrt(alen(imgs))*rms*abs(linedata.vcdeltkms)
    moment0_max = moment0.max()
    moment0_min = moment0.min()
    
    # levels
    if negcontours:        
        levels = concatenate((-1*flipud(arange(nsig*moment0_sigma,abs(moment0_min+moment0_sigma),nsjump*moment0_sigma)), arange(nsig*moment0_sigma,moment0_max+moment0_sigma,nsjump*moment0_sigma)))
    else:
        levels = arange(nsig*moment0_sigma,moment0_max+moment0_sigma,nsjump*moment0_sigma)
        
    # calculate moment 1 map

    velocities = linedata.velarr[img_channels]
    # calculate the denominator
    Isum = imgs.sum(axis=0)
    # create array that matches imgs array, so they can be multiplied
    velocities_matrix = array([ones(imgs.shape[1:])*i for i in velocities])
    # set values which are lower than 3 sigma to 'nan' i.e. mask the array
    # use the moment0 to determine where, but the Isum to set it
    Isum[where(moment0<(nsig*moment0_sigma))] = nan
    # now, calculate the numerator of the division
    Ivsum = (imgs*velocities_matrix).sum(axis=0)
    # division
    moment1 = Ivsum/Isum


    ###
    ###
    ###
    # tick density
    majorLocator = MultipleLocator(locators[0])
    minorLocator = MultipleLocator(locators[1])
    if send==True:
        #~ return {'moment0': moment0,
                #~ 'moment1': moment1,
                #~ 'levels':levels,
                #~ 'moment0_sigma':moment0_sigma,
                #~ 'extent':(left,right,bottom,top),
                #~ 'lims': (i1,i2,j1,j2),
                #~ 'data':linedata}
        return moment0, moment1, levels, moment0_sigma, (left,right,bottom,top), linedata
    #
    #
    # calculating the velocity for vmin and vmax
    #
    #
    # remember it uses the region keyword, so
    print('remember that the calculation for vmin and vmax uses the region keyword')
    from string import lower
    arr = array([line for line in moment1[y1:y2,x1:x2].flatten() if lower(str(line)) != 'nan'])
    w = arr.std()
    from scipy import median
    m = median(arr)
    """

    here you should add a histogram calculation, and fit a gaussian or something
    and take some representative width for vmin to vmax
    """
    
    set_rc(font=font, quality=quality)

    # linewidths
    rc('axes', linewidth=1)
    rc('lines', linewidth=1, markeredgewidth=1)
    
    pl.ion()
    pl.close()
    fig = pl.figure(1, figsize=fsize)
    fig.clf()
    #
    ax = fig.add_subplot(111)
    #
    # print beam parameters for the data
    gain = 8.168e-25*(linedata.restfreq)**2*linedata.bmin*linedata.bmaj
    print '='*40
    print ' '*15,'BEAM(S)'
    print '='*40
    print 'Line cube:'
    print u' Minor (FWHM)\t: %2.3f \tasec' % linedata.bmin
    print u' Major (FWHM)\t: %2.3f  \tasec' % linedata.bmaj
    print ' PA \t\t: %2.3f \tDegrees (0<theta<180)' % linedata.bpa
    print u' Gain\t\t: %2.4f \tJy\u00b7K\u207b\u00b9\n' % gain

    #levs=levs.round(2)
    #cs1 = ax.contourf(img, levels=levs, cmap=cm.bone_r, extent=(left,right,bottom,top))
    #cs2 = ax.contour(cs1, levels=cs1.levels[::2], colors=ccol, extent=(left,right,bottom,top))
    #im = pl.imshow(moment1,vmin=6.79,vmax=7,extent=(left,right,bottom,top))
    if type:
        im = pl.imshow(moment1,cmap=cm.jet,vmin=m-2*w,vmax=m+2*w,extent=(left,right,bottom,top),interpolation='nearest')
    elif not type:
        im = ax.contourf(moment1, levels=arange(m-2*w,m+2*w,4*w/20), cmap=cm.jet, extent=(left,right,bottom,top))
    cs2 = ax.contour(moment0, levels=levels, colors='k', extent=(left,right,bottom,top))
    cbar = pl.colorbar(im,format=cbar_tick_label_formatter) #label_X.replace('X','%2.2f'))

    cbar.ax.set_ylabel(r'km\,s$^{\sf -1}$')



    #draw_beam(ax, linedata,box=0)
    draw_fov(ax, linedata)

    if 'dist' and 'au' in sbar.keys():
        draw_sizebar(ax,linedata,dist=sbar['dist'],au=sbar['au'])
    elif 'dist' in sbar.keys():
        draw_sizebar(ax,linedata,dist=sbar['dist'])
    else :
        raise ParError(sbar)
    if len(cpeak) == 3:
        mark = cpeak[2]
        xmark, ymark = cpeak[0:2]
    elif len(cpeak) >4:
        xmark = cpeak[0:-1:2]
        ymark = cpeak[1:-1:2]
        mark = cpeak[-1]
    else:
        mark = '+k'
    cross = ax.plot(xmark, ymark, mark, ms=13, mew=3, alpha=0.9)

    #
    ax.xaxis.set_major_formatter(tick_label_formatter)
    ax.yaxis.set_major_formatter(tick_label_formatter)

    ax.xaxis.set_major_locator(majorLocator)
    ax.xaxis.set_minor_locator(minorLocator)
    ax.yaxis.set_major_locator(majorLocator)
    ax.yaxis.set_minor_locator(minorLocator)

    #pl.setp(ax.get_xticklabels(),family='sans-serif')
    #pl.setp(ax.get_yticklabels(),family='sans-serif')

    ax.set_xlabel('RA Offset ($^{\prime\prime}$)')
    ax.set_ylabel('Dec Offset ($^{\prime\prime}$)')

    #fig.suptitle(linedata.obj+' (%s km s$^{-1}$)'% str(linedata.unit))
    #if cfile!=None:
    #    fig.subplots_adjust(bottom=0.08, right=0.77, top=0.90)
    ax.text(0.05,0.93,
    linedata.obj,
    transform = ax.transAxes,
    backgroundcolor='w')
    ax.set_xlim(i1,i2)
    ax.set_ylim(j1,j2)
    ax.set_aspect(1)
    #
    #
    pl.subplots_adjust(left=pl_left, bottom=pl_bottom, right=pl_right, top=pl_top)
#
def plot_moment2 (self,
                cfile=None,
                chvals=None,
                nvals=None,
                region=[0,0,0,0],
                nx=6,
                filled=True,
                box=[0,0],
                nsig=3,
                nsjump=2,
                obj_dict = dict(vsys=0),
                font={'family':'sans-serif', 'sans-serif': ['Arial', 'Helvetica'],
                'size':22, 'weight':'bold'},
                fit = dict(gauss = None, params = None, continuum = False,
                interactive = False),
                send=False,
                quality=[150, 72],
                cbar=True,
                plot_adjust= [0.12, 0.01, 0.74, 0.99],
                cpeak=[0,0,'k'],
                ccol='r',
                sbar=dict(dist=250,au=200),
                locators = [2,1],
                telescope=None,
                type=1):
    """ Function doc """

    # imports
    #import scipy as sp
    from scipy import array, where, median, std, sign, arange, alen, vstack, \
    concatenate, sqrt, log10, ones, nan
    #import pyfits as pf
    import matplotlib.pyplot as pl
    #from matplotlib.patches import Circle
    from matplotlib.ticker import MultipleLocator, FormatStrFormatter
    from matplotlib import cm
    #

    set_rc(font=font, quality=quality)


    ################################
    # setting the tick label font  #
    ################################
    # we are using latex formatting here!
    # following sets the ticklabel format string
    data_fmt = '%g'         # for normal y and x axis
    cbar_data_fmt = '%2.2f'         # for normal y and x axis
    label_X = parse_tick_font(font)
    tick_label_formatter = FormatStrFormatter(label_X.replace('X',data_fmt))
    cbar_tick_label_formatter = FormatStrFormatter(label_X.replace('X',cbar_data_fmt))


    pl_left, pl_bottom, pl_right,pl_top = plot_adjust


    #
    # first get the fitsfile
    #~ linedata = loadcube(filename,telescope)
    linedata = self
    #
    linedata.velarr = linedata.velarr - obj_dict['vsys'] #now all the velocities are based on the LSR

    # parse the channel values
    if chvals!=None:
        v1, v2 = chvals
    # parse the region, get the area for the spectra
    x1,x2,y1,y2 = parse_region(linedata, region)
    # if any is limits are None, draw spectra and ask for them/it
    # INTERACTIVE
    if nvals==None or chvals==None:
        # draw spectrum
        plot_spectrum(filename,region=region, obj_dict= {'vsys': obj_dict['vsys']})
        #
        # if there is no channels supplied
        if chvals==None:
            v1, v2 = array(raw_input('input the limits, comma separated: ').split(','), dtype ='float')
        if nvals==None:
            # ask for noise calculation velocity limits
            try:
                nvals = array(raw_input('input the noise limits (velocity). comma separated: ').split(','), dtype='float')
                if len(nvals)==4:
                    n1, n2, n3, n4 = nvals
                elif len(nvals)==2:
                    n1, n2 = nvals
            except (ValueError):
                print "Since you did not input any or input was wrong we will guess some values..."
                nvals = None
        pl.close(1)

    # calculate common stuff
    ### for the plotting box
    ylen, xlen = linedata.d[0].shape
    ycoords = arange(-ylen/2,ylen/2,1)*linedata.dec_cdelt
    xcoords = arange(-xlen/2,xlen/2,1)*linedata.ra_cdelt
    #
    # for the extent keyword
    left, right = xcoords[0],xcoords[-1]
    bottom, top = ycoords[0],ycoords[-1]
    #
    # parse the noise channel values
    if nvals!=None:
        # if noise has been input
        noise_channels = get_indices(linedata.velarr, nvals)
    #
    else:
        # if user didnt input noise velocity limits
        # choose channels away from the choosen (red blue) lines
        low = where((linedata.velarr>(linedata.velarr.min()+10))*(linedata.velarr<(v1-10)))[0]
        high = where((linedata.velarr>(v2+10))*(linedata.velarr<(linedata.velarr.max()-10)))[0]
        noise_channels = concatenate((low, high))
    #
    # the region to calculate the rms in
    i1,i2 = xlen/2+array([-1,1])*xlen/4
    j1,j2 = ylen/2+array([-1,1])*ylen/4

    # the noise, rms
    noise = linedata.d[noise_channels]
    rms = sqrt(((noise[:,j1:j2,i1:i2])**2).mean())

    # set boundaries
    if box == [0,0]:
        i1,i2 = left,right
        j1,j2 = bottom,top
    elif box != [0,0]:
        i1,i2 = array([-1,1])*box[0]/2.*sign(linedata.ra_cdelt)
        j1,j2 = array([-1,1])*box[1]/2.*sign(linedata.dec_cdelt)

    img_channels = get_indices(linedata.velarr,[v1,v2])
    imgs = linedata.d[img_channels]
    #
    # do the summing
    #
    # M1 = dv * sum(I(a,b,vi))_x1^x2
    # or perhaps without dv to save calc?
    moment0 = imgs.sum(axis=0)*abs(linedata.vcdeltkms)
    moment0_sigma = sqrt(alen(imgs))*rms*abs(linedata.vcdeltkms)

    """
    Fit gaussian in the chvals interval, using velocity and cut out spectra
    in all pixels in region/box.
    Plot it!



    # levels
    moment0_max = moment0.max()
    moment0_min = moment0.min()
    levels = concatenate((-1*flipud(arange(nsig*moment0_sigma,abs(moment0_min+moment0_sigma),nsjump*moment0_sigma)), arange(nsig*moment0_sigma,moment0_max+moment0_sigma,nsjump*moment0_sigma)))

    # calculate moment 1 map

    velocities = linedata.velarr[img_channels]
    # calculate the denominator
    Isum = imgs.sum(axis=0)

    minpar =
    limmin =
    maxpar =
    limmax =

    HAVE TO ESTIMATE LINE CENTER FOR ALL PIXELS
fit = dict(type=None, params=[(0.09, 7.3, 3.6)],
                guess=False, interactive=False, fixlist=None, error=None,
                limmin=None, minpar=None, limmax=None, maxpar=None, tie=None)

            if not fit.has_key('error'):
            errmsg='You have to supply an error to the fit, they\'re kind of important you know.'
            print stylify(errmsg)
            return ; sysexit()

        fwhmfromsig = 2*sqrt(2*log(2)) # the constant
        fwhm = lambda x: fwhmfromsig*x
        sigma = lambda x: x/fwhmfromsig

        # fits up to five (5) 1D gaussian(s) to the spectral data
        if chvals!=None: # if we supplied limits for the fit
            ch = where((velocity>v1)*(velocity<v2))[0]
            Fx = spect[ch]
            X = velocity[ch]
        else: # else use the eveything
            Fx = spect
            X = velocity
        #
        #
        p = fit['params'] # parameters for the fit

        #
        if not fit.has_key('limmin'):
            fit['limmin'] = None
            fit['minpar'] = None
        if not fit.has_key('limmax'):
            fit['limmax'] = None
            fit['maxpar'] = None
        if not fit.has_key('fixlist'):
            fit['fixlist'] = None
        if not fit.has_key('tie'):
            fit['tie'] = None
        #
        from time import time
        t1= time()
        #
        params, errors, chi2, mp = fit_gauss1d((X,Fx), params=p, fixlist=fit['fixlist'], \
                minbool=fit['limmin'], minpar=fit['minpar'], \
                maxbool=fit['limmax'], maxpar=fit['maxpar'], \
                err=fit['error'], tie=fit['tie'], verbose=0, full_output=1)
        #
        print ' Done in %2.3f seconds \n' % (time()-t1)

        #
        print ' Number of fits : ', alen(params)/3
        print ' Fit status : ', mp.status, '(if 0, it should have halted)\n'


            'value' - the starting parameter value (but see the START_PARAMS
                             parameter for more information).

            'fixed' - a boolean value, whether the parameter is to be held
                             fixed or not.  Fixed parameters are not varied by
                             MPFIT, but are passed on to MYFUNCT for evaluation.

            'limited' - a two-element boolean array.  If the first/second
                               element is set, then the parameter is bounded on the
                               lower/upper side.  A parameter can be bounded on both
                               sides.  Both LIMITED and LIMITS must be given
                               together.

            'limits' - a two-element float array.  Gives the
                              parameter limits on the lower and upper sides,
                              respectively.  Zero, one or two of these values can be
                              set, depending on the values of LIMITED.  Both LIMITED
                              and LIMITS must be given together.

            'parname' - a string, giving the name of the parameter.  The
                               fitting code of MPFIT does not use this tag in any
                               way.  However, the default iterfunct will print the
                               parameter name if available.

            'step' - the step size to be used in calculating the numerical
                            derivatives.  If set to zero, then the step size is
                            computed automatically.  Ignored when AUTODERIVATIVE=0.

            'mpside' - the sidedness of the finite difference when computing
                              numerical derivatives.  This field can take four
                              values:

                                     0 - one-sided derivative computed automatically
                                     1 - one-sided derivative (f(x+h) - f(x)  )/h
                                    -1 - one-sided derivative (f(x)   - f(x-h))/h
                                     2 - two-sided derivative (f(x+h) - f(x-h))/(2*h)

                             Where H is the STEP parameter described above.  The
                             "automatic" one-sided derivative method will chose a
                             direction for the finite difference which does not
                             violate any constraints.  The other methods do not
                             perform this check.  The two-sided method is in
                             principle more precise, but requires twice as many
                             function evaluations.  Default: 0.

            'mpmaxstep' - the maximum change to be made in the parameter
                                     value.  During the fitting process, the parameter
                                     will never be changed by more than this value in
                                     one iteration.

                                     A value of 0 indicates no maximum.  Default: 0.

            'tied' - a string expression which "ties" the parameter to other
                            free or fixed parameters.  Any expression involving
                            constants and the parameter array P are permitted.
                            Example: if parameter 2 is always to be twice parameter
                            1 then use the following: parinfo(2).tied = '2 * p(1)'.
                            Since they are totally constrained, tied parameters are
                            considered to be fixed; no errors are computed for them.
                            [ NOTE: the PARNAME can't be used in expressions. ]

            'mpprint' - if set to 1, then the default iterfunct will print the
                               parameter value.  If set to 0, the parameter value
                               will not be printed.  This tag can be used to
                               selectively print only a few parameter values out of
                               many.  Default: 1 (all parameters printed)

Future modifications to the PARINFO structure, if any, will involve
     adding dictionary tags beginning with the two letters "MP".
     Therefore programmers are urged to avoid using tags starting with
     the same letters; otherwise they are free to include their own
     fields within the PARINFO structure, and they will be ignored.

     PARINFO Example:
     parinfo = [{'value':0., 'fixed':0, 'limited':[0,0], 'limits':[0.,0.]}
                                                                                                    for i in range(5)]
     parinfo[0]['fixed'] = 1
     parinfo[4]['limited'][0] = 1
     parinfo[4]['limits'][0]  = 50.
     values = [5.7, 2.2, 500., 1.5, 2000.]
     for i in range(5): parinfo[i]['value']=values[i]

     A total of 5 parameters, with starting values of 5.7,
     2.2, 500, 1.5, and 2000 are given.  The first parameter
     is fixed at a value of 5.7, and the last parameter is
     constrained to be above 50.




    """
    # create array that matches imgs array, so they can be multiplied
    velocities_matrix = array([ones(imgs.shape[1:])*i for i in velocities])
    # set values which are lower than 3 sigma to 'nan' i.e. mask the array
    # use the moment0 to determine where, but the Isum to set it
    Isum[where(moment0<(nsig*moment0_sigma))] = nan
    # now, calculate the numerator of the division
    Ivsum = (imgs*velocities_matrix).sum(axis=0)
    # division
    moment1 = Ivsum/Isum


    ###
    ###
    ###
    # tick density
    majorLocator = MultipleLocator(locators[0])
    minorLocator = MultipleLocator(locators[1])


    if send==True:
        return {'moment0': moment0,
                'moment1': moment1,
                'levels':levels,
                'moment0_sigma':moment0_sigma,
                'extent':(left,right,bottom,top),
                'lims': (i1,i2,j1,j2),
                'data':linedata}
    #
    #
    # calculating the velocity for vmin and vmax
    #
    #
    # remember it uses the region keyword, so
    print('remember that the calculation for vmin and vmax uses the region keyword')
    from string import lower
    arr = array([line for line in moment1[y1:y2,x1:x2].flatten() if lower(str(line)) != 'nan'])
    w = arr.std()
    from scipy import median
    m = median(arr)

    """

    here you should add a histogram calculation, and fit a gaussian or something
    and take some representative width for vmin to vmax
    """
    pl.ion()
    pl.close()
    if cbar:
        fig = pl.figure(1, (9., 7.))
    elif not cbar:
        fig = pl.figure(1, (9.,7.))
    fig.clf()
    #
    ax = fig.add_subplot(111)
    #
    # print beam parameters for the data
    gain = 8.168e-25*(linedata.restfreq)**2*linedata.bmin*linedata.bmaj
    print '='*40
    print ' '*15,'BEAM(S)'
    print '='*40
    print 'Line cube:'
    print u' Minor (FWHM)\t: %2.3f \tasec' % linedata.bmin
    print u' Major (FWHM)\t: %2.3f  \tasec' % linedata.bmaj
    print ' PA \t\t: %2.3f \tDegrees (0<theta<180)' % linedata.bpa
    print u' Gain\t\t: %2.4f \tJy\u00b7K\u207b\u00b9\n' % gain

    #levs=levs.round(2)
    #cs1 = ax.contourf(img, levels=levs, cmap=cm.bone_r, extent=(left,right,bottom,top))
    #cs2 = ax.contour(cs1, levels=cs1.levels[::2], colors=ccol, extent=(left,right,bottom,top))
    #im = pl.imshow(moment1,vmin=6.79,vmax=7,extent=(left,right,bottom,top))
    if type:
        im = pl.imshow(moment1,cmap=cm.jet,vmin=m-2*w,vmax=m+2*w,extent=(left,right,bottom,top),interpolation='nearest')
    elif not type:
        im = ax.contourf(moment1, levels=arange(m-2*w,m+2*w,4*w/20), cmap=cm.jet, extent=(left,right,bottom,top))
    cs2 = ax.contour(moment0, levels=levels, colors='k', extent=(left,right,bottom,top))
    cbar = pl.colorbar(im,format=cbar_tick_label_formatter) #label_X.replace('X','%2.2f'))

    if str(linedata.unit) == 'Jy/beam':
        cbar.ax.set_ylabel(r'Jy\,beam$^{\sf-1}$')
    else:
        cbar.ax.set_ylabel(str(linedata.unit))

    ax.set_xlim(i1,i2)
    ax.set_ylim(j1,j2)

    #draw_beam(ax, linedata,box=0)
    draw_fov(ax, linedata)

    if 'dist' and 'au' in sbar.keys():
        draw_sizebar(ax,linedata,dist=sbar['dist'],au=sbar['au'])
    elif 'dist' in sbar.keys():
        draw_sizebar(ax,linedata,dist=sbar['dist'])
    else :
        raise ParError(sbar)
    if len(cpeak) == 3:
        mark = cpeak[2]
        xmark, ymark = cpeak[0:2]
    elif len(cpeak) == 5:
        xmark = cpeak[0:-1:2]
        ymark = cpeak[1:-1:2]
        mark = cpeak[-1]
    else:
        mark = '+k'
    cross = ax.plot(xmark, ymark, mark, ms=13, mew=2, alpha=0.8)

    #
    ax.xaxis.set_major_formatter(tick_label_formatter)
    ax.yaxis.set_major_formatter(tick_label_formatter)

    ax.xaxis.set_major_locator(majorLocator)
    ax.xaxis.set_minor_locator(minorLocator)
    ax.yaxis.set_major_locator(majorLocator)
    ax.yaxis.set_minor_locator(minorLocator)

    #pl.setp(ax.get_xticklabels(),family='sans-serif')
    #pl.setp(ax.get_yticklabels(),family='sans-serif')

    ax.set_xlabel('RA offset ($^{\prime\prime}$)')
    ax.set_ylabel('DEC offset ($^{\prime\prime}$)')

    #fig.suptitle(linedata.obj+' (%s km s$^{-1}$)'% str(linedata.unit))
    #if cfile!=None:
    #    fig.subplots_adjust(bottom=0.08, right=0.77, top=0.90)
    ax.text(0.05,0.93,
    linedata.obj,
    transform = ax.transAxes,
    backgroundcolor='w')
    ax.set_aspect(1)
    #
    #
    pl.subplots_adjust(left=pl_left, bottom=pl_bottom, right=pl_right, top=pl_top)
#
def plot_vgradient(radecfile,
                fitsfile=None,
                rms=None,
                chvals=None,
                nvals=None,
                xy_cont = None,
                region=[0,0,0,0],
                obj_dict = dict(vsys=0),
                freq=False,
                font={'family':'serif', 'serif': ['Times', 'Times New Roman'],
                'size': 20, 'weight':'bold'},
                bin=False,
                fit = dict(type=None, params=[(0.09, 7.3, 3.6)],
                guess=False, interactive=False, fixlist=None, error=None,
                limmin=None, minpar=None, limmax=None, maxpar=None, tie=None),
                send=False,
                quality=[150, 72],
                plot_adjust= [0.12, 0.09, 0.99, 0.99],
                lines = [],\
                axspace = [1.01, 1.01, 1.01, 1.05],
                ylimits=None):
    """
    
    
    
    TODO: add a plot of the fit perpendicular to the gradient!
    
    
    """
            
    # imports
    #import scipy as sp
    from scipy import array, where, median, std, sign, arange, alen, vstack, \
    concatenate, sqrt, log10, ones, nan
    #import pyfits as pf
    import matplotlib.pyplot as pl
    #from matplotlib.patches import Circle
    from matplotlib.ticker import MultipleLocator, FormatStrFormatter
    from matplotlib import cm, rc
    #

    ################################
    # setting global rc properties #
    ################################
    rc('savefig', **{'dpi': 300})
    rc('text', usetex=True)
    rc('savefig', **{'dpi': quality[0]})
    rc('figure',**{'facecolor': '1', 'dpi': quality[1]})

    #to set the global font properties
    rc('font', **font)

    ################################
    # setting the tick label font  #
    ################################
    # we are using latex formatting here!
    # following sets the ticklabel format string
    data_fmt = '%g'         # for normal y and x axis
    cbar_data_fmt = '%2.2f'         # for normal y and x axis
    label_X = parse_tick_font(font)
    tick_label_formatter = FormatStrFormatter(label_X.replace('X',data_fmt))
    cbar_tick_label_formatter = FormatStrFormatter(label_X.replace('X',cbar_data_fmt))
    # ticksize
    rc('xtick',**{'minor.size':3, 'major.size':7})
    rc('ytick',**{'minor.size':3, 'major.size':7})

    # linewidths
    rc('axes', linewidth=1)
    rc('lines', linewidth=1.5, markeredgewidth=1)

    pl_left, pl_bottom, pl_right,pl_top = plot_adjust
    
    
    #
    # TODO: be able to add RMS directly, instead of loading fits-file all the time
    #
    if fitsfile!=None and nvals!=None:
        # first get the fitsfile
        linedata = loadcube(filename,telescope)
        #
        linedata.velarr = linedata.velarr - obj_dict['vsys'] #now all the velocities are based on the LSR
         # parse the region, get the area for the spectra
        x1,x2,y1,y2 = parse_region(linedata, region)
    elif fitsfile==None and rms==None:
        print 'If you do not supply a fitsfile or rms value the calculations cannot proceed.'
        sysexit()
    elif nvals==None and rms==None:
        print 'Need eiter a RMS value, or a fitsfile and velocities over\
        which to calculate the RMS.'
        sysexit()
    elif rms!=None:
        pass
   
    if nvals!=None:
        ## get the nvals and calculate RMS etc
        print '='*40
        print ' '*11,'Noise statistics'
        # calculate the rms from the channels in the spectra
        # accounts for it even if it is binned
        #
        # image rms
        # change x1,x2,y1,y2 to quarter region
        # change so that when binning, the rms i calculated
        # x1,x2
        zlen, ylen, xlen = data.d.shape
        ydelt = ylen/6
        xdelt = xlen/6
        i1,i2 = xlen/2-xdelt, xlen/2+xdelt
        j1,j2 = ylen/2-ydelt, ylen/2+ydelt
        rms = sqrt(((data.d[get_indices(velocity,nvals),j1:j2,i1:i2])**2).mean())
        rms_mjy = rms*1e3
    
        xlen = data.d.shape
        #rms_0 = sqrt(((spect[get_indices(velocity,nvals)])**2).mean())
        #rms_2 = sqrt(((data.d[get_indices(velocity,nvals),:,:])**2).mean())
    
        #rms_0= rms/sqrt(abs(data.vcdeltkms))
        #print rms_0
        #print 'rms_0 =', rms_0*1e3
        #print 'rms_2 =', rms_2*1e3
        #
        # the sensitivity
        s = rms/sqrt(abs(velocity_delta))
        s_mjy = s*1e3
        # the channels used
        ind = get_indices(velocity,nvals)
        ind1, ind2 = ind.min(), ind.max()
        print u'\n RMS \t\t: %2.3f mJy\u00b7beam\u207b\u00b9\u00b7channel\u207b\u00b9' % rms_mjy
        print u' Sensitivity \t: %2.3f mJy\u00b7beam\u207b\u00b9\u00b7km\u207b\u00b9\u00b7s' % s_mjy
        print u' Channels used \t: %d, %d (%s km\u00b7s\u207b\u00b9)' % (ind1, ind2, str(nvals))
        print u' Region \t: %s arcsec offset' % (str(region))
        print u' Channel width \t: %2.3f km\u00b7s\u207b\u00b9' % abs(velocity_delta)
        #ax_kms.plot([xmin, xmax],[3*rms,3*rms],'b--', lw=2, alpha=0.7)
        #ax_kms.plot([xmin, xmax],[-3*rms,-3*rms],'b--', lw=2, alpha=0.7)
    
    
    ####################################################################
    # need to load the data into the arrays
    # need ra, d_ra, dec, d_dec, channel numbers, flux from the radecfile
    
    try:
        f=open(radecfile, mode='r')
    except (IOError):
        print 'File %s does not exist!' % radecfile
        sysexit()
    lines = [line for line in f]
    f.close()
    linebyline = [lines[i].split() for i in arange(len(lines))]
    ch = []
    rapos = []
    d_ra = []
    decpos = []
    d_dec = []
    ch = []
    flux = []
    d_flux = []
    vel = []
    
    for i in arange(len(linebyline)):
        # have to get the chvals here if they where not input?
        # i.e. if chvals==None
        # if I just use output from GILDAS POINT uv_fit
        if linebyline[i][1:5] == ['No', 'data', 'for', 'channel']:
            ch.append(linebyline[i][5])
            rapos.append(nan)
            d_ra.append(nan)
            decpos.append(nan)
            d_dec.append(nan)
            flux.append(nan)
        elif linebyline[i][2:6] == ['data', 'points', 'for', 'channel']:
            if linebyline[i+4][0] != 'POINT':
                print 'Only supports POINT fits for now'
                sysexit()
            ch.append(linebyline[i][6])
            vel.append(linebyline[i+1][7])
            rapos.append(linebyline[i+4][3])
            d_ra.append(linebyline[i+4][5].strip(')'))
            if linebyline[i+5][0] == 'STOP':
                i+=1
            decpos.append(linebyline[i+5][3])
            d_dec.append(linebyline[i+5][5].strip(')'))
            if linebyline[i+6][0] == 'STOP':
                i+=1
            flux.append(linebyline[i+6][3])
            d_flux.append(linebyline[i+6][5].strip(')'))
    #
    # done getting all the values!
    
    ch = array(ch).astype('i')
    rapos = array(rapos).astype('float')
    d_ra = array(d_ra).astype('float')
    decpos = array(decpos).astype('float')
    d_dec = array(d_dec).astype('float')
    flux = array(flux).astype('float')
    d_flux = array(d_flux).astype('float')
    vel = array(vel).astype('float')

    # First get all values 3*RMS above
    rms3 = 3*rms
    i_3sigma = where(flux>=rms3)[0]
    #pl.plot(flux)
    #pl.plot([0, len(flux)],[rms3,rms3])
    if chvals==None:
        # take what is given, all of it
        # parse the channel values
        print 'You did not input any velocity values (chvals=[v1, v2])\n\
        So will try to take what is given in the radecpos-file'
        i_vel = arange(0,alen(vel),1).astype('int')
    elif chvals!=None:
        # slice!
        v1, v2 = chvals
        i_vel = where((vel>=v1)*(vel<=v2))[0]
    i = [a for a in i_3sigma if a in i_vel]
    x = rapos[i]
    dx = d_ra[i]
    y = decpos[i]
    dy = d_dec[i]
    z = vel[i]
    channels = ch[i]
    f = flux[i]
    df = d_flux[i]
    # need to slice the arrays according to chvals now and set below 
    # do not includ values with flux<=3sigma
    
    ####################################################################
    """
        find the strongest velocity gradient in data.
        input either ra, and dec lists, or just the STDOUT of uvfit 
        in GILDAS MAPPING
    
        Fit a plane to a cloud of points
        From
        http://www.geometrictools.com/Documentation/LeastSquaresFitting.pdf
    """
    from scipy import pi, arange, tan, array, dot, arctan, alen, meshgrid, arcsin, cos, sin
    
    from matplotlib import cm
    import matplotlib.pyplot as pl
    from scipy.optimize import leastsq
    pl.ion()
    
    # TODO: include errors. 
    #       i.e. need equation which include varance-covariance matrix for x and y
    #       -> the orthogonal 3D regression
    def fit_plane_to_cloud((x,y,z), err=None):
        """
        Fit a plane Ax + By + C = z, to a cloud of points
        Input:
            (x,y,z) - the coordinates of the points to be fit
            err     - the error, in (dx, dy)
            
        Output:
            G       - (A, B, C) of the fit, ie the normal is (A, B, -1)
        """
        from scipy.linalg import solve
        #x = rapos
        #y = decpos
        #z = arange(alen(decpos)) # for now, need the exact channel numbers
        # can fit all channels of the cube, and then define velocity to fit over!
        
        if not x.size == y.size == z.size:
            print 'input not same size'
            import sys
            sys.exit(1)
        
        a11 = (x**2).sum()
        a12 = (x*y).sum()
        a13 = x.sum()
        
        a21 = (x*y).sum()
        a22 = (y**2).sum()
        a23 = y.sum()
        
        a31 = x.sum()
        a32 = y.sum()
        a33 = alen(y)
        
        A = array([[a11, a21, a31],[a12, a22, a32],[a13, a23, a33]])
        
        
        b1 = (x*z).sum()
        b2 = (y*z).sum()
        b3 = z.sum()
        
        B = array([[b1],[b2],[b3]])
        
        
        G = solve(A,B)
        return G
    #
    #
    G = fit_plane_to_cloud((x,y,z))
    grad = G[0:2] # the projected gradient (normal of the plane) onto the xy-plane
    
    # only in the positive side of the y-axis
    # the direction of the gradient is obvious from figures etc
    # this makes the y-axis the same for all angles
    # we essentailly move the vector up to positive y-values, mirror it
    if grad[1]<0:
        grad[1] = grad[1]*(-1)
    
    # the angle with which we incline the coordinate system
    theta = arcsin(grad[0]/((grad**2).sum())**.5)[0]
    
    # the new y axis is called "s" (s,t)-plane
    s_offsets = []
    t_offsets = []
    for x,y in zip(x,y):
        x_prime = x*cos(theta) - y*sin(theta)
        y_prime = x*sin(theta) + y*cos(theta)
        t_offsets.append(x_prime)
        s_offsets.append(y_prime)
    
    # convert to array
    t_offsets = array(t_offsets,dtype='float')
    s_offsets = array(s_offsets,dtype='float')
    #
    #ab = (G[0]**2+G[1]**2)**.5
    #v = z/ab - G[2]/ab
    
    ## plot the best fit model
    from scipy import polyfit
    p = polyfit(z,s_offsets,deg=1)
    s = lambda x: p[0]*x + p[1]
    
    fig1 = pl.figure(1,figsize=(10,5))
    #ax1 = fig1.add_subplot(111)
    ax1 = fig1.add_subplot(121)
    ax1.plot(z,s_offsets,'x')
    ax1.plot(z,s(z))
    if xy_cont!=None:
        #new position in (s,t) coordinate system of the continuum
        s_cont = xy_cont[0]*sin(theta) + xy_cont[1]*cos(theta)
        ax1.plot([z[0],z[-1]],[s_cont, s_cont])
    else:
        print '\nINFO: No continuum position (rel to phase center) given\n\
        ->skipping...\n'
    ax1.set_xlabel('Velocity [km~s$^{-1}$]')
    ax1.set_ylabel('s-offset[$\prime\prime$]')
    #ax.set_xlim(5.8,8.2)
    #ax.set_ylim(-0.205,0.305)
    #fig1.subplots_adjust(left=0.17,bottom=0.14,right=0.98,top=0.97)
    print '\n','*'*40
    print '\t\tResults for the parallell s-axis:\n'
    print u'Velocity gradient: %2.2f km\u00b7s\u207b\u00b9\u00b7arcsec\u207b\u00b9' % p[0]**-1
    
    
    ## plot perpendicular to the best fit model
    #from scipy import polyfit
    #p = polyfit(z,t_offsets,deg=1)
    #t = lambda x: p[0]*x + p[1]
    
    #fig2 = pl.figure(2,figsize=(7,6))
    #ax2 = fig2.add_subplot(111)
    ax2 = fig1.add_subplot(122)
    ax2.plot(z,t_offsets,'x')
    #ax2.plot(z,t(z))
    if xy_cont!=None:
        #new position in (s,t) coordinate system of the continuum
        t_cont = xy_cont[0]*cos(theta) - xy_cont[1]*sin(theta)
        ax2.plot([z[0],z[-1]],[t_cont, t_cont])
    else:
        print '\nINFO: No continuum position (rel to phase center) given\n\
        ->skipping...\n'
    ax2.set_xlabel('Velocity [km~s$^{-1}$]')
    ax2.set_ylabel('t-offset[$\prime\prime$]')
    #ax.set_xlim(5.8,8.2)
    #ax.set_ylim(-0.205,0.305)
    #fig2.subplots_adjust(left=0.17,bottom=0.14,right=0.98,top=0.97)
    fig1.subplots_adjust(left=0.12,bottom=0.14,right=0.97,top=0.95,wspace=0.31)
    print '\n','*'*40
    print '\t\tResults for the perpendicular t-axis:\n'
    print u'Velocity gradient: %2.2f km\u00b7s\u207b\u00b9\u00b7arcsec\u207b\u00b9' % p[0]**-1
#
def plot_pv (self,
                cfile=None,
                chvals=None,
                nvals=None,
                region=[0,0,0,0],
                nx=6,
                filled=True,
                box=[0,0],
                nsig=3,
                nsjump=2,
                object=dict(vsys=0),
                font= dict(family='serif', serif=['Times', 'Palatino',
                'New Century Schoolbook', 'Bookman', 'Computer Modern Roman'],
                 size=12, weight='bold'),\
                fit = dict(gauss = None, params = None, continuum = False,
                interactive = False),
                send=False,
                quality=[150, 72],
                cbar=True):
    """ Function doc """

    # TODO : change the contour level calculation, use RMS?
    # TODO : being able to specify rotation
    #           perhaps draw a line of where the pv-diag is
    #
    #       1 translate center to the given center (region)
    #       2 rotate by given angle
    #           - new x,y pixel scale
    #       3 cut out box
    #       4 produce pv-diagram as before

    print 'importing modules...'
    from scipy import median,zeros
    from scipy.ndimage import rotate
    from matplotlib import cm, rc
    print 'done'
    #

    ################################
    # setting global rc properties #
    ################################
    rc('savefig', **{'dpi': 300})
    rc('text', usetex=True)
    rc('savefig', **{'dpi': quality[0]})
    rc('figure',**{'facecolor': '1', 'dpi': quality[1]})

    #to set the global font properties
    rc('font', **font)

    rc('axes',linewidth=2)
    rc('lines', linewidth=1)


    ################################
    # setting the tick label font  #
    ################################
    # we are using latex formatting here!
    # following sets the ticklabel format string
    data_fmt = '%g'         # for normal y and x axis
    label_X = parse_tick_font(font)
    tick_label_formatter = FormatStrFormatter(label_X.replace('X',data_fmt))
    # ticksize
    rc('xtick',**{'minor.size':5, 'major.size':7})
    rc('ytick',**{'minor.size':5, 'major.size':7})

    # linewidths
    rc('axes', linewidth=2)
    rc('lines', linewidth=1.2, markeredgewidth=2)

    #
    # first get the fitsfile
    #~ linedata = loadcube(filename)
    linedata = self

    ############## P-V diagram
    v1, v2 = chvals
    pl.ion()
    linedata.velarr = linedata.velarr - object['vsys'] #now all the velocities are based on the LSR
    #
    #sum along x-axis ie axis=2
    # parse the region, get the area for the spectra
    x1,x2,y1,y2 = parse_region(linedata, region)
    #x1,x2,y1,y2  = 245,265,245,265
    #axis=2 because I sum along x axis, ie naxis1
    d_arr = linedata.d[:,y1:y2,x1:x2].sum(axis=2)*linedata.vcdeltkms
    # now we have 2D data that has velocity as Y-axis
    # the increment in arcs along declination-axis

    # statistics
    dstd = d_arr.std()
    dmid = median(d_arr)
    dmin = d_arr.min()
    dmax = d_arr.max()
    up = arange(dmid+dstd,dmax,(dmid+dstd+dmax)/12)
    down = arange(abs(dmid-dstd),abs(dmin),(abs(dmid-dstd)+abs(dmin))/12)*(-1)
    levs = zeros(len(down)+len(up))
    levs[0:len(down)] = flipud(down)
    levs[len(down):len(down)+len(up)] = up
    levs= levs.round(1)
    # get the y-axis (declination) coordinates in arcs
    dec = ((arange(0,linedata.dec_npix,1)-linedata.dec_npix/2.)*linedata.dec_cdelt)[y1:y2]
    # get the x-axis (ra) coordinates in arcs
    ra = ((arange(0,linedata.ra_npix,1)-linedata.ra_npix/2.)*linedata.ra_cdelt)[x1:x2]

    fig1 = pl.figure(1)
    ax1 = pl.axes()
    # transpose it so that the velocity s on the X-axis
    channels = get_indices(linedata.velarr,[v1,v2])
    im = ax1.contourf(linedata.velarr[channels], dec, d_arr.transpose()[:, channels], levs)
    cb = pl.colorbar(im)
    pl.xlim(v1,v2) # kms boundaries
    pl.ylim(dec.min(),dec.max())
    pl.xlabel(r'$v_{lsr}$')
    pl.ylabel(r'asec')

    fig2 = pl.figure(2)
    ax2 = pl.axes()
    im = ax2.imshow(linedata.d[channels,y1:y2,x1:x2].sum(axis=0)*linedata.vcdeltkms,
                    interpolation='nearest',cmap=cm.Greys)
    #im = ax2.pcolor(flipud(ra), dec, linedata.d[channels,y1:y2,x1:x2].sum(axis=0)*linedata.vcdeltkms)
    cb = pl.colorbar(im)
    ax2.axis('image')
    pl.xlabel(r'asec')
    pl.ylabel(r'asec')
#
def plot_chmap (self,
                chvals=None,
                nvals=None,
                region=[0,0,0,0],
                nx=6,
                filled=True,
                box=[0,0],
                nsig=3,
                nsjump=2,
                source={'vsys':0},
                font={'family':'serif', 'serif': ['Times New Roman', 'Times'],
                'size':22},
                nsum=False,
                plot_adjust= [0.12, 0.09, 0.99, 0.99],
                quality=[300, 300],
                send=False,
                color_map='jet',
                cpeak = [0,0],
                locators = [1,0.2],
                levs_global=True,
                fsize=(3, 4)):
    # imports
    #import scipy as sp
    print 'importing...'
    from scipy import array, where, median, std, sign, arange, alen, vstack, \
    concatenate, sqrt, log10, exp, flipud, ceil
    import pyfits as pf
    import matplotlib.pyplot as pl
    from matplotlib.pyplot import contour, contourf
    from mpl_toolkits.axes_grid import AxesGrid
    from matplotlib.ticker import MultipleLocator, FormatStrFormatter
    from matplotlib import cm, rc
    print 'done'
    #


    ################################
    # setting the tick label font  #
    ################################
    # we are using latex formatting here!
    # the following set the ticklabel format string
    data_fmt = '%g'         # for normal y and x axis
    #freq_data_fmt = '%5.5f' # for the frequency array
    label_XY = parse_tick_font(font)
    tick_label_formatter = FormatStrFormatter(label_XY.replace('X',data_fmt))
    #freq_label_formatter = FormatStrFormatter(label_X.replace('X',freq_data_fmt))

    #rc('mathtext',**{'rm':'sans\\-serif'})


    ################################
    # parsing input                #
    ################################
    # set the subplot_adjust parameters, if not given a standard set will
    # be used
    pl_left, pl_bottom, pl_right,pl_top = plot_adjust
    #
    color_map = pl.get_cmap(color_map)

    #sigma levels etc
    nsig = nsig
    nsjump = nsjump
    # now check the type3 plots
    if chvals==None:
        ion=True
    elif chvals!=None:
        ion=False
        v1, v2 = chvals
    else: # input error
        raise ParError(chvals)
    #

    ################################
    #       get data               #
    ################################
    # first get the fitsfile
    #~ linedata = loadcube(filename)
    linedata = self
    linedata.velarr = linedata.velarr - source['vsys'] #so that now all the velocities are based on the objects
    #if cfile!=None:
    #    contdata= loadcube(cfile)
    cfile=None
    #
    # parse the region parameter
    x1, x2, y1, y2 = parse_region(linedata, region)

    if ion==True:
        plot_spectrum(filename, region=region)
        #
        # if it is just a channel map
        v1, v2 = array(raw_input('input the limits, comma separated: ').split(','), dtype ='float')
        if nvals==None:
            # ask for noise calculation velocity limits
            try:
                nvals = array(raw_input('input the noise limits (velocity). comma separated: ').split(','), dtype='float')
                if len(nvals)==4:
                    n1, n2, n3, n4 = nvals
                elif len(nvals)==2:
                    n1, n2 = nvals
            except (ValueError):
                print "Since you did not input any or input was wrong we will guess some values..."
                nvals = None
        pl.close(1)
    #######################################
    #######################################
    #

    # if we are to sum channels
    if nsum!=False:
        """
        blue[x:x+y].sum(axis=0)*abs(data.vcdeltkms)
        calc_sigma(nchans,rms,vcdelt)


        # give chvals=[v1,v2] and nsum > 1
        # nsum is number of channels to sum together
        # get the channels
        """
        print '\nParameter \'nsum\' is set to %d.' % nsum
        print colorify('Summing channels for better signal.',c='g')
        # check if it is a integer
        if type(nsum) != type(1) or nsum<1: raise ParError(nsum)
        #
        channels = get_indices(linedata.velarr, chvals)
        # can we divide it into the correct number of channels directly?
        print ' *Checking if we have to add some channels for the channel map to even up.'
        rest = alen(channels)%nsum
        print ' *%d channels, with nsum=%d we have a rest of %d' % (alen(channels),nsum,rest)
        to_add = nsum-rest
        if rest == 0:
            print '  Everything is fine, continuing.'
            pass
        elif to_add == 1:
            print '  Adding one channel'
            start = channels.min()
            end = channels.max()+to_add+1 # add one extra for python convention
        elif to_add%2 == 0:
            half = to_add/2
            print '  Going down/up %d in channel indices' % half
            start = channels.min()-half
            end = channels.max()+half+1 # add one extra for python convention
        elif to_add%2 != 0:
            half = (to_add-1)/2
            print '  Going down %d and up %d in channel indices' % (half, half+1)
            start = channels.min()-half
            end = channels.max()+(half+1)+1 # add one extra for python convention
        else:
            raise ParError(nsum)
        # now change the channel indices, so we get more channels
        if rest != 0:
            channels = arange(start,end,1)
        #
        # so now the channels are adapted to evenly divide with nsum
        #
        # getting the data to sum
        indices = arange(0, alen(channels), nsum)
        data = linedata.d[channels]
        velocity = linedata.velarr[channels]
        # the mean velocity is the middle one
        velocity = array([velocity[x:x+nsum].mean() for x in indices])
        velocity_delta = linedata.vcdeltkms*nsum
        print u'The velocity interval over which you create the maps is %2.3f to %2.3f km\u207b\u00b9\u00b7s' % (velocity.min()-abs(velocity_delta)/2,velocity.max()+abs(velocity_delta)/2)
        maps = array([data[x:x+nsum].sum(axis=0)*abs(linedata.vcdeltkms) for x in indices])
        N_channels = alen(channels)/nsum
        print stylify('Done, remember that it can change the velocity interval that you specified in chvals. \n',c='g')
        #
    else :
        # normal procedure here
        #
        #we are making a channel map
        channels = get_indices(linedata.velarr, chvals)
        N_channels = alen(channels)
        velocity = linedata.velarr[channels]
        velocity_delta = linedata.vcdeltkms
        # units of Jy/beam kms
        data = linedata.d[channels]*abs(velocity_delta)
        maps = data

    #
    if nvals!=None:
        noise_channels = get_indices(linedata.velarr,nvals)
    elif nvals==None:
        # if user didnt input noise velocity limits
        # choose channels away from the choosen (red blue) lines
        #
        # if you have choosen just a min and max to plot all channels
        low = where((linedata.velarr>(linedata.velarr.min()+10))*(linedata.velarr<(v1-10)))[0]
        high = where((linedata.velarr>(v2+10))*(linedata.velarr<(linedata.velarr.max()-10)))[0]
        noise_channels = concatenate((low, high))

    # calculate common stuff
    ### for the plotting box
    zlen, ylen, xlen = data.shape
    ycoords = arange(-(linedata.dec_crpix-1),(linedata.dec_npix-linedata.dec_crpix),1)*linedata.dec_cdelt
    xcoords = arange(-(linedata.ra_crpix-1),(linedata.ra_npix-linedata.ra_crpix),1)*linedata.ra_cdelt

    # for the extent keyword
    left, right = xcoords[0],xcoords[-1]
    bottom, top = ycoords[0],ycoords[-1]
    #
    # calculate the RMS
    noise = linedata.d[noise_channels]
    #
    # the region to calculate the RMS in
    i1,i2 = xlen/2+array([-1,1])*xlen/4
    j1,j2 = ylen/2+array([-1,1])*ylen/4
    #
    # RMS
    # since nsum might not be defined i.e. =False
    # dont really know if it is used later on,
    # so this is just to be sure 
    # the rms used above changes with a factor of 1/sqrt(nsunm) for the
    # new channels in the channel map (since they are summed)
    nchansum = [1,nsum][nsum != False]
    rms = sqrt(((noise[:,j1:j2,i1:i2])**2).mean()/nchansum)
    #
    #
    if box == [0,0]:
        x1,x2 = left,right
        y1,y2 = bottom,top
    elif box != [0,0]:
        x1,x2 = array([-1,1])*box[0]/2.*sign(linedata.ra_cdelt)
        y1,y2 = array([-1,1])*box[1]/2.*sign(linedata.dec_cdelt)
    # calculate the correct rms and sigma
    # the rms is per channel, ie with the new
    # channel widht "velocity_delta"
    # so the sigma is just rms*abs(velocity_delta) ie. N=1 
    sigma =  calc_sigma(1,rms,velocity_delta)
    #
    chans_min = array([i.min() for i in maps])
    chans_max = array([i.max() for i in maps])

    # calculate the levels of the contours
    if levs_global:
        f = 0.7
        vmin, vmax = f*chans_min.min(),f*chans_max.max()
        # levs_stat, i.e. contourf starts and end at global min/max
        levs_stat = concatenate((arange(vmin,-nsig*sigma,nsjump*sigma), arange(nsig*sigma,vmax,nsjump*sigma)))
        levs = [levs_stat for x in arange(N_channels)]
    elif not levs_global:
        # levs, i.e. contour starts and ends at local min/max
        levs = [concatenate((arange(x,-nsig*sigma,nsjump*sigma), arange(nsig*sigma,y,nsjump*sigma))) for x,y in zip(chans_min, chans_max)]

    ##########
    majorLocator = MultipleLocator(locators[0])
    minorLocator = MultipleLocator(locators[1])

    print u'RMS \t: %2.2f mJy\u00b7beam\u207b\u00b9\u00b7channel\u207b\u00b9' % (rms*1e3)
    print u'1 sigma : %2.2f mJy\u00b7beam\u207b\u00b9\u00b7km\u00b7s\u207b\u00b9' % (sigma*1e3)
    print u'\u0394 vel \t : %2.3f km\u00b7s\u207b\u00b9 (channel width in km\u00b7s\u207b\u00b9)' % abs(velocity_delta)
    if send==True:
        if cfile!=None:
            return {'ch_map data': maps, 'levs':levs, 'chans_sig':sigma, 'vels':velocity, 'extent':[left,right,bottom,top], 'data':linedata, 'continuum':contdata}
        if cfile==None:
            return {'ch_map data': maps, 'levs':levs, 'chans_sig':sigma, 'vels':velocity, 'extent':[left,right,bottom,top], 'data':linedata}


    if velocity_delta<0:
        maps = flipud(maps)
        levs.reverse()
        velocity = flipud(velocity)
    #
    def print_vel(ax,x,fc='w'):
        ax.text(0.03,.91,
        str(round(velocity[x],2)),
        fontsize=6,
        bbox=dict(edgecolor='k',facecolor=fc, pad=4, lw=0.5),
        transform = ax.transAxes)


    ################################
    # setting global rc properties #
    ################################
    rc('savefig', **{'dpi': quality[0]})
    rc('text', usetex=1)
    rc('figure',**{'facecolor': '1', 'dpi': quality[1]})
    #to set the global font properties
    rc('font', **font)
    rc('axes',linewidth=0.7)
    rc('patch', linewidth=0.5)
    rc('lines', linewidth=0.3, markeredgewidth=0.6)
    rc('font', family='serif', serif='Times New Roman', size=8)
    rc('text', usetex=True)  
    # ticksize
    rc('xtick',**{'minor.size':2, 'major.size':4, 'major.pad': -3})
    rc('ytick',**{'minor.size':2, 'major.size':4, 'major.pad': 1})



    pl.ion()
    pl.close()
    fig = pl.figure(1, fsize)

    fig.clf()
    
    ny = int(ceil(N_channels/float(nx)))
    if filled==False:
        grid = AxesGrid(fig, 111, # similar to subplot(111)
                nrows_ncols = (ny, nx), # creates nyx6 grid of axes
                axes_pad=0, # pad between axes in inch.
                label_mode = "L",
                share_all=True,
                )
            # plot data contours
        for i in range(N_channels):
            grid[i].set_aspect('equal')
            im = grid[i].contour(maps[i],
                                levs_stat,
                                colors=('k'),
                                extent=(left,right,bottom,top))
    #
    elif filled==True:
        grid = AxesGrid(fig, 111, # similar to subplot(111)
                nrows_ncols = (ny, nx), # creates 2x3 grid of axes
                axes_pad=0, # pad between axes in inch.
                label_mode = "L",
                share_all=True,
                cbar_mode="single",
                cbar_location="top",
                cbar_size="2%",)
        # plot data contours
        for i in range(N_channels):
            grid[i].set_aspect('equal')
            im = grid[i].contourf(maps[i],
                                levs[i],
                                extent=(left,right,bottom,top),
                                cmap=color_map)
        grid.cbar_axes[0].colorbar(im)
        # add a unit to the colorbar
        grid.cbar_axes[0].set_xlabel(str(linedata.unit)+r'\,kms$^{-1}$')
        grid.cbar_axes[0].axis["top"].toggle(label=True, ticks=True, ticklabels=True)
    #
    for i in range(N_channels):
        # plot a cross at pointing centre
        plt = grid[i].plot(cpeak[0],cpeak[1],'r+', ms=3, mew=0.7, alpha=0.7)
        # set the locator spacings
        grid[i].xaxis.set_major_locator(majorLocator)
        grid[i].xaxis.set_minor_locator(minorLocator)
        grid[i].yaxis.set_major_locator(majorLocator)
        grid[i].yaxis.set_minor_locator(minorLocator)

        draw_fov(grid[i].axes, linedata)
        if i in [0,1,2]:
            print_vel(grid[i].axes, i,fc='#FFAAAA')
        elif i in [12,13,14]:
            print_vel(grid[i].axes, i,fc='0.8')
        else:
            print_vel(grid[i].axes, i)
    fig.text(0.95,0.14,r'SO$_2$', rotation=90)
    fig.text(0.95,0.86,r'H$_2^{18}$O', rotation=90)
    
    grid[2].plot([21,-2], [-1.8,-1.3],'-', color='#FFAAAA', lw=3, alpha=0.7 ,clip_on=False)
    #grid[2].plot([21,-2], [-1.8-1.7,-1.3-1.7],'-', color='0.5', lw=3, alpha=0.7 ,clip_on=False)
    grid[8].plot([21,-2], [-3.76,-2.53],'-', color='0.5', lw=3, alpha=0.7 ,clip_on=False)
    grid[11].plot([21,-2], [-2.16,-0.93],'-', color='0.5', lw=3, alpha=0.7 ,clip_on=False)
    grid[14].plot([21,-2], [-0.56,0.67],'-', color='0.5', lw=3, alpha=0.7 ,clip_on=False)
    #grid[12].axhline(y=-2.64, xmin=0.1, xmax=1.4 ,clip_on=False )
    
    draw_beam(grid[0].axes, linedata, box=1)
    
    #
    #grid.axes_llc.set_major_formatter(tick_label_formatter)
    #grid.axes_llc.set_major_formatter(tick_label_formatter)

    pl.subplots_adjust(left=pl_left, bottom=pl_bottom, right=pl_right, top=pl_top)
    

    grid.axes_llc.set_xlim(x1,x2)
    grid.axes_llc.set_ylim(y1,y2)

    fig.text(0.53,0.02,r'RA offset ($^{\prime\prime}$)', ha='center',va='center')
    fig.text(0.03,0.53,r'Dec offset ($^{\prime\prime}$)', rotation='vertical', va='center', ha='center')
    #fig.suptitle(linedata.obj)
    #pl.show()

    """
    from showmoment the 3range procedure.
    Use this to correct the binning!
        ### blue
        # if divided by 3, any rest?
        brest = len(blue)%3
        inc = (len(blue)-brest)/3
        bincrement = array([inc, inc, inc+brest])
        if data.vcdelt>0:
            bincrement = flipud(bincrement)
        bindices = arange(0,(len(blue)-brest),bincrement[0])

        # create the first 2 maps
        bmaps = array([blue[x:x+y].sum(axis=0)*abs(data.vcdeltkms) for x,y in zip(bindices,bincrement)])
        # calculate the center positions and their width
        bwidth = bincrement*abs(data.vcdeltkms)*.5
        bcenter = [data.velarr[x:x+y].mean() for x,y in zip(blue_channels[bindices],bincrement)]
        if data.vcdelt>0:
            bmaps = flipud(bmaps)
            bwidth = flipud(bwidth)
            bcenter = flipud(bcenter)
        # calculate the sigmas for each set of data
        bsigma = calc_sigma(bincrement, rms, data.vcdeltkms)

        ### red
        rrest = len(red)%3
        inc = (len(red)-rrest)/3

        # now flip the arrays (if vcdelt<0) so that the highest speeds swallow the
        # most channels, if  multiple of 3 no channels
        rincrement = array([inc, inc, inc+rrest])
        if data.vcdelt<0: # so that the last channel is still the one with the rest
            rincrement = flipud(rincrement)
        # the two middle indices
        # a bit tricky with the first being the biggest here
        rindices = array([0, rincrement[0], rincrement[0]+rincrement[1]])

        # get the maps, the last one (first if vcelt<0) takes the leftovers
        rmaps = array([red[x:x+y].sum(axis=0)*abs(data.vcdeltkms) for x,y in zip(rindices,rincrement)])

        #get the widht & center of each channelsum
        # flipud so that the channels are the same in blue and red (ie low med high velocity)
        rwidth = rincrement*abs(data.vcdeltkms)*.5
        rcenter = array([data.velarr[x:x+y].mean() for x,y in zip(red_channels[rindices],rincrement)])
        if data.vcdelt<0:
            rmaps = flipud(rmaps)
            rwidth = flipud(rwidth)
            rcenter = flipud(rcenter)

        rsigma = calc_sigma(rincrement,rms,data.vcdeltkms)

        ### put them together now
        centers = concatenate((bcenter,rcenter)).round(2)
        widths = concatenate((bwidth,rwidth)).round(2)
        maps_sigma = concatenate((bsigma,rsigma))

        maps = vstack((bmaps,rmaps))

        maps_max = array([i.max() for i in maps])
        maps_min = array([i.min() for i in maps])

        # now create the levels for each image


        levs = [concatenate((arange(x,-nsig*z,nsjump*z),arange(nsig*z,y,nsjump*z))) for x,y,z in zip(maps_min, maps_max, maps_sigma)]
    """
#
def cubetracking (self,box=False, nsum=False):
    import matplotlib.pyplot as pl
    from matplotlib import cm
    from scipy import clip, array, sign, alen, arange
    pl.ion()
    class IndexTracker:
        def __init__(self, ax, data, velocity):
            self.ax = ax
            ax.set_title('Use scroll wheel to navigate images')
            self.X = data
            self.vel = velocity
            #self.data = dobject
            self.slices,cols,rows = data.shape
            self.ind  = self.slices/2
            self.im = ax.imshow(self.X[self.ind,:,:],interpolation='nearest',origin='lower', cmap=cm.jet)
            pl.show()
            self.update()

        def onscroll(self, event):
            #print event.button, event.step
            if event.button=='up':
                self.ind = clip(self.ind+1, 0, self.slices-1)
            elif event.button=='down':
                self.ind = clip(self.ind-1, 0, self.slices-1)
            self.update()

        def update(self):
            self.im.set_data(self.X[self.ind,:,:])
            ax.set_title(r'vel: '+str(round(self.vel[self.ind],2))+' kms$^{-1}$')
            self.im.axes.figure.canvas.draw()
    #
    pl.ioff()
    X = self
    if box!=False:
        i1,i2 = array([-1,1])*box[0]/2.*sign(self.ra_cdelt)
        j1,j2 = array([-1,1])*box[1]/2.*sign(self.dec_cdelt)
        i1, i2, j1, j2 = parse_region(self,[i1,i2,j1,j2])
        data = self.d[:, j1:j2, i1:i2]
    else:
        data = self.d
    if nsum!=False:
        if alen(data)%nsum!=0:
            raise ParError(nsum)
        channels = arange(0,alen(data),1)
        #
        # getting the data to sum
        indices = arange(0, alen(data), nsum)
        #data = linedata.d[channels]
        velocity = self.velarr
        # the mean velocity is the middle one
        velocity = array([velocity[x:x+nsum].mean() for x in indices])
        velocity_delta = self.vcdeltkms*nsum
        print u'The velocity interval over which you create the maps is %2.3f to %2.3f km\u207b\u00b9\u00b7s' % (velocity.min()-abs(velocity_delta)/2,velocity.max()+abs(velocity_delta)/2)
        print 'Velocity delta : %2.3f' % velocity_delta
        data = array([data[x:x+nsum].sum(axis=0)*abs(self.vcdeltkms) for x in indices])
        N_channels = alen(data)/nsum
    else:
        velocity = self.velarr
    fig = pl.figure(1)
    ax = fig.add_subplot(111)
    #ax = pwg.axes(header=X.hdr)
    tracker = IndexTracker(ax, data, velocity)
    #
    fig.canvas.mpl_connect('scroll_event', tracker.onscroll)
#
#
# CMD line implementation
if __name__ == '__main__':
    # statements that you want to be executed only when the
    # module is executed from the command line
    # (not when importing the code by an import statement)
    # wee hooo...
    
    print '\nThe ADAVIS program was run from the command line\n'
    import os
    import sys
    from optparse import OptionParser as op
    import pyfits as pf
    from string import lower
    
    #version
    ver = 1.0
    
    desc="""Add a keyword and value to fitsheader"""
    usage = "usage: %prog [options] fitsfile"
    epilog = """usage: %prog [options] fitsfile, \'fitsfile\' \n\
    should contain the relative path to the file as well"""
    
    parser = op(usage=usage,description=desc,epilog=epilog, version="%prog " + str(ver))
    
    # the options permitted
    parser.add_option("-f", "--function", dest="f", help="function to run on fits file" , metavar="FUNCTION")
    parser.add_option("-v", "--velocities", dest="v", help="between what velocities to plot", metavar="VELOCITIES")
    parser.add_option("-b", "--box", dest="b", help="zoom to a box X,Y size", metavar="BOX")
    parser.add_option("-l", "--list", action="store_true", dest="l", help="list the header", metavar="LIST")
    parser.add_option("-k", "--force", action="store_true", dest="k", help="force overwriting of keyword", metavar="FORCE")
    
    # time to parse
    (options, args) = parser.parse_args()
    
    # if no filename is supplied
    if len(args) != 1:
        parser.error("Incorrect number of arguments")
        parser.print_usage()
    # the options
    f = str(options.f)
    
    def convert_to_list(a):
        return [float(x) for x in (a).split(',')]
    #
    #
    # create a dictionary!
    # have to change the functions, to handle **kwargs first
    # the everything except infile and type of plotting function can be **kwargs
    #
    
    if options.v != None:
        v = convert_to_list(options.v)
    else:
        v = options.v
    if options.b != None:
        b = convert_to_list(options.b)
    else:
        b = options.b
    listhdr = options.l
    force = options.f
    # and the file...
    filename = str(args[0])
    print v, b
    if lower(f) in ['spectrum', 'sectrum', 'stectrum', 'spectraum', 'spectarum']:
        # tries to pick up miss-spellings
        plot_spectrum(filename)
    
    if lower(f) in ['moment0','mom0','m0']:
        if b!=None:
            plot_moment0(filename,box=b)
        else:
            plot_moment0(filename)
    if lower(f) in ['moment1','mom1','m1']:
        if b!=None:
            plot_moment1(filename,box=b)
        else:
            plot_moment1(filename)


    #
    a = str(raw_input('Press any key to exit...'))
    # put Jes, optparser here!
    











