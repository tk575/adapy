
from .helpers import *
from .libs.date import jd2gd
import scipy as _sp
from datetime import datetime as _dt

import astropy.units as u
import astropy.units as un
import astropy.constants as co
from uvfits_helpers import *
import numpy as np


########################################################################
# STRINGS
KMS = u"km\u00b7s\u207b\u00b9"



########################################################################
# DATA HANDLING CLASSES
# to adacore.py
# classes etc
#
# FITS DATA CLASS
# Main data object, needs fits file as input
# keywords can be appended to object later
# to complement fits header information
class Fits:
    """
    ------------------------------------------
    Adavis Fits Object (Data object)

    Usage :
    ObjectName = FITS(PathToFitsFile)

    ------------------------------------------

    Should be able to read:
    Map, Cube and SD

    TODO : for DataObject loading, learn it to parse the FITS type INDEX
       that Class can output for -32 Bits, (single dish data)

    TODO : maybe change the velocity attr, so that it follows naming
    similar to ra and dec, e.g. self.v_delt, self.v_arr

    TODO : Create a frequency array as well, much simpler later on then

    """
    def __init__(self, fitsfile, telescope=None, vsys=0, distance=0, endian=None, **kwargs):
        """

        attributes
        ------------------------
        datatype
            possible values : 'SDSPECT', 'CUBE', 'IMAGE'
        telescope
            supported values : 'SMA', 'PDBI', 'IRAM30M', 'APEX, 'ALMA'
            the name of the telescope
        diameter
            diameter of the telescope
        v_arr
            array with every channels velocity, not corrected for the systemic velocity
        dist
            distance to the source

        TODO : If the rotational matrice is non empty, load data and rotate it (?)
        TODO : What if add a function to grid it to a certain size, say 512x512?
                o So it is possible to combine data with different res.
                    - If extent keyword is given for both datasets, what happens?
                o Better to do this when plotting (se above comment)?
        TODO : More robust loading (detecting the axis etc)?
                o Minimum of different types of data
                    - NAXIS==2 (Freq/Vel & Flux/Intensity) - 1D Spectra
                    - NAXIS==2 (RA & DEC) - 2D map
                    - NAXIS==3 (RA & DEC & Flux/Intensity) 3D Spectral map
                    - Polarization data?
                    (i.e, in SD spectra need to get rid of 3 axes
                        self.d = self.d[0][0][0])
        TODO : make loadcube delete an axis, along with the hdr keywords if all
               the axis keywords/values are empty/null (delet hdr keyword really needed?)
                    o only to loaded data, not save to raw data (fits file)

        TODO : choose big or small endian, and convert accordingly
        
        OVERALL change:

        make it load the fits info in steps. start with the RA and DEC keywords
        then go over to loading frequency/velocity array, and so on...
        lastly determine what type it is



        """

        #imports
        #~ from pyfits import open as fitsopen
        from astropy.io.fits import open as fitsopen
        #from  sys import
        from os.path import getsize
        from scipy import where, array, nan
        from string import upper
        from sys import exit as sysexit
        import adapy.libs.cgsconst as _cgs
        #

        # create the class, but without any init script.
        # a class (object) the easy way
        print(u'Loading fitsfile :  %s ' % stylify(str(fitsfile),fg='g'))
        s  = getsize(fitsfile)
        print(" Size %0.2f MB" % (s/(1024.*1024.)))
        f = fitsopen(fitsfile, **kwargs)
        if endian == 'little':
            self.hdr, self.d = f[0].header, f[0].data.byteswap().newbyteorder()
        else:
            self.hdr, self.d = f[0].header, f[0].data
        #self.d = self.d[0] # this is if the stokes axis is present,
        # but it should not be there anymore
        f.close()
        # save the fitsfile, perhaps the path too, for updating it
        self.fitsfile = fitsfile
        # the telescope diameter
        # first check if there was keyword sent in
        if telescope!=None:
            self.hdr.update('TELESCOP', telescope)
            self.telescope = str(telescope)
        #
        if 'TELESCOP' in self.hdr.keys():
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
        if 'LINE' in self.hdr.keys():
            self.linename = self.hdr['LINE']
        #
        #
        # spectra, 1 : 3 axis and 3rd axis is >1 in size
        # image, 2 : 2 axis (or 3 axis, 3rd is =1 in size)
        # cube,3 : spectral cube
        #
        # simple solution to the common extra empty STOKES axis
        # and sometimes even an extra empty axis for ?
        from numpy import diff, arange
        #~ while self.d.shape[0] == 1:
            #~ self.d = self.d[0]
        # TODO: Horrible implementation! 
        # Check if I can go over to radio_tools spectral cube instead
        try:
            self.restfreq = Unit(self.hdr['RESTFREQ'],'Hz' ) # in Hertz
        except KeyError:
            try:
                self.restfreq = Unit(self.hdr['RESTFRQ'],'Hz' ) # in Hertz
            except KeyError:
                print ('No frequency information.')

        if self.hdr['NAXIS']==4 and self.d.shape[0:2] == (1,1):
            self.datatype = ('IMAGE',2)
            self.d = self.d[0][0]
        #naxis = self.hdr['NAXIS']
        #axshape = self.d.shape
        #if axshape[0] array([i>1 for i in a.shape[1:]]).all()
        # an image, only 2 dimensions
        elif self.hdr['NAXIS']==2 and self.hdr['NAXIS1']>1 and self.hdr['NAXIS2']>1:
            #if self.hdr['NAXIS']==3 and self.hdr['NAXIS1']>1 and self.hdr['NAXIS2']>1 and self.hdr['NAXIS3']==1:
            # image, not SD spectra or anything,
            # really 2D and greater extent than 1x1
            self.datatype = ('IMAGE',2)
            pass
        #
        # spectral image cube (extra axis for frequency/velocity)
        elif self.hdr['NAXIS']==3 and self.hdr['NAXIS1']>1 and self.hdr['NAXIS2']>1 and self.hdr['NAXIS3']==1:
            # _load_IMAGE_data()
            self.datatype = ('IMAGE',2)
            # extra if the continuum image has the freq and width
            self.freq = self.hdr['CRVAL3']
            self.freqwidth = self.hdr['CDELT3']
        # a spectra! the 3rd axis is longer than 1
        elif self.hdr['NAXIS']>=3 and self.hdr['NAXIS3']>1:
            # spectral cube
            # _load_CUBE_data()
            # only support for velo-lsr in 3rd axis
            self.datatype = ('CUBE',3)
            # load the third axis
            # need frequency!
            while self.d.shape[0] == 1:
                self.d = self.d[0]
            ##### have to add loading of frequency and calculate velocity
            # UGLY HACK BELOW, BEWARE!
            # need to be changed to a more flexible code...
            hdr_values = [self.hdr[i] for i in self.hdr.keys() if not i == 'HISTORY']
            #~ self.hdr_values = hdr_values
            #~ return None
            # need to match VELO, VELO-LSR, VELOCITY and VRAD
            _velname = [i for i in hdr_values if ("VELO" in str(i) or "VRAD" in str(i))]
            if _velname != []:
                _velname = _velname[0]
                velax = str([x for x in self.hdr.keys() if x[:-1]=='CTYPE' and _velname in self.hdr[x]][0][-1:])
                vel_info = True
            elif _velname == []:
                print('No velocity axis defined')
                vel_info = False
            else:
                print('No velocity axis defined')
                vel_info = False
            ##### FUGLY hack END
            if vel_info:
                self.v_type = velax
                self.v_crpix = self.hdr['CRPIX'+self.v_type]-1
                self.v_crval = self.hdr['CRVAL'+self.v_type]
                self.v_ctype = self.hdr['CTYPE'+self.v_type]
                self.v_cdelt = self.hdr['CDELT'+self.v_type]
                self.v_naxis = self.hdr['NAXIS'+self.v_type]
                self.v_cdeltkms = self.v_cdelt/float(1e3)
            # load frequency and calculate velocity stuff
            if not vel_info:
                from scipy import sign
                if 'FREQ' in hdr_values:
                    freqax = str([x for x in self.hdr.keys() if x[:-1]=='CTYPE' and 'FREQ' in self.hdr[x]][0][-1:])
                    self.f_type = freqax
                    self.f_crpix = self.hdr['CRPIX'+self.f_type]-1
                    self.f_crval = self.hdr['CRVAL'+self.f_type]
                    self.f_ctype = self.hdr['CTYPE'+self.f_type]
                    self.f_cdelt = self.hdr['CDELT'+self.f_type]
                    self.f_naxis = self.hdr['NAXIS'+self.f_type]
                    #self.f_cdeltkms = self.f_cdelt/float(1e3)
                    self.f_arr = ((arange(0,self.f_naxis)-self.f_crpix)*self.f_cdelt+self.f_crval) # in Hz
                else:
                    print('No velocity or frequency axis defined')
                    raise FitsError('Could not load FITS file')
                # velocity
                # UGLY hack warning...
                self.v_crpix = self.f_crpix
                self.v_crval = calc_vlsr (self.f_crval, self.restfreq)*1e3
                self.v_ctype = 'VELO'
                self.v_cdelt = abs(calc_vlsr (self.f_arr[0], self.restfreq)*1e3-calc_vlsr (self.f_arr[1], self.restfreq)*1e3)*sign(self.f_cdelt)*(-1)
                self.v_naxis = self.f_naxis
                self.v_cdeltkms = self.v_cdelt/float(1e3)
                #self.f_arr = ((arange(0,self.f_naxis)-self.f_crpix)*self.f_cdelt+self.f_crval)
                # END ugly hack
            #data = loadvelocity(header)
            # loading velocity information

            # plus one because to start at 0 is wrong, need 1 to v_naxis <- this is WRONG
            # start at 0 because we
            self.v_arr = ((arange(0,self.v_naxis)-self.v_crpix)*self.v_cdelt+self.v_crval)/float(1e3) # so it is i kms
            self.v_rangekms = self.v_arr.max()-self.v_arr.min()
            # not good if vcdletkms has more than 3 significant digits.
            #self.v_arr = self.v_arr.round(3)
            #self.v_cdeltkms = round(self.v_cdeltkms,2)

            #start = self.v_crval-self.v_cdelt*(self.v_crpix-1)
            #stop =  self.v_crval+self.v_cdelt*(self.v_naxis-self.v_crpix)
            #arr = arange(start,stop-1,self.v_cdelt)/float(1e3)
            #print self.v_arr-arr
            # calculate the FOV = 58.4*lambda/D*3600 asec
           
            self.fov = 58.4*(3.e8/self.restfreq)/float(self.diameter)*3600.
            print 'Field of view: %.2f asecs, for dish size: %.1f m' % (self.fov, self.diameter)
            #print self.veltype, self.v_crpix, self.v_crval, self.v_cdeltkms, self.v_naxis
            print 'Velocity range \t: {0:.2f} km/s'.format(self.v_rangekms)
            print 'Velocity step \t: {0:2.4f} km/s'.format(self.v_cdeltkms)
            #
            # now if we want to have the spectral array as well to use
            #~ already on line 1480
            #~ if self.hdr.has_key('RESTFREQ'):
                #~ self.restfreq = self.hdr['RESTFREQ']
            #~ elif self.hdr.has_key('RESTFRQ'):
                #~ self.restfreq = self.hdr['RESTFRQ']
            #if self.hdr['NAXIS']==4 and  self.hdr['NAXIS4']==1:
            #    self.d = self.d[0]
            #
            # this was just a test
            # SD pointing spectra
            # single dish
        elif self.hdr['NAXIS']>1 and self.hdr['NAXIS2']==1 and self.hdr['NAXIS3']==1:
            # _load_SD_data(self)
            self.datatype = ('SDSPECT',1)
            self.v_cdelt = self.hdr['DELTAV']
            self.v_cdeltkms = self.hdr['DELTAV']/float(1e3)
            self.v_crpix = self.hdr['CRPIX1']-1
            self.v_naxis = self.hdr['NAXIS1']
            self.v_crval = self.hdr['VELO-LSR']
            self.v_arr = ((arange(0,self.v_naxis)-self.v_crpix)*self.v_cdelt+self.v_crval)/float(1e3)
            self.restfreq = self.hdr['RESTFREQ'] # in Hertz
            # huh?
            self.fov = 58.4*(3e8/self.restfreq)/(self.diameter)*3600
            if 'BEAMEFF' in self.hdr:
                self.beameff = self.hdr['BEAMEFF']
            if 'FORWEFF' in self.hdr:
                self.forweff = self.hdr['FORWEFF']
            #self.d = self.d[0][0][0] # specific for this data...
        #~ elif 'Miriad fits' in self.hdr['ORIGIN']:
        # below to load CLASS bits -32
        #~ elif 'FITS_rec' in str(type(self.d)) and not self.hdr['NAXIS']:
            #~ self.d = self.d[0][0]
            #~ self.datatype = 'SDSPECT',1
            #~ #
            #~ # self.d.dtype shows SPECTRUM and WAVE for CLASS data
            #~ #
            #~ self.v_cdelt = self.hdr['DELTAV']
            #~ self.v_cdeltkms = self.hdr['DELTAV']/float(1e3)
            #~ self.v_crpix = self.hdr['CRPIX1']-1
            #~ self.v_naxis = self.hdr['NAXIS1']
            #~ self.v_crval = self.hdr['VELO-LSR']
            #~ self.v_arr = ((arange(0,self.v_naxis)-self.v_crpix)*self.v_cdelt+self.v_crval)/float(1e3)
            #~ self.restfreq = self.hdr['RESTFREQ'] # in Hertz
            #~ self.fov = 58.4*(3e8/self.restfreq)/(self.diameter)*3600
        else:
            # if it is not an image or a spectral cube
            print_error('The dimensions of the data is wrong\n at least the header keywords indicate that.\n The data has '+str(self.hdr['NAXIS'])+' axes. \n\n Perhaps use the removeaxis script?\n')
            sysexit()
        print 'Datatype : {0}'.format(self.datatype[0])
        # perhaps check in the header?
        # velref probably at what velocity that middle of spectra is?
        self.v_sys = float(vsys)
        self.dist = float(distance)
        #
        # FREQUENCY ARRAY
        #
        # construct the frequency array!
        # the 3rd axis longer than 1, and 4th axis is the frequency
        # if the data is constructed in gildas
        try:
            self.f_arr = self.restfreq * (1. - (self.v_arr - self.v_sys)*1e5 / _cgs.CC) 
        except:
            print('no frequency array created')
    
        if self.datatype[0] in ['CUBE', 'SDSPECT']:
            self.v_arr_syscorr = self.v_arr - self.v_sys
        #
        # load the coordinate parameters
        # for the CRPIXNax parameter I take -1 because
        # FITS starts at 1 and Python starts at 0, hence in
        # an array, crpix-1 will show the Python position of the crpix
        # DEC
        decax = str([x for x in self.hdr.keys() if x[:-1]=='CTYPE' and 'DEC' in self.hdr[x]][0][-1:])
        self.dec_cdelt = self.hdr['CDELT'+decax]*3600 # arcs
        #TODO make npix dynamically determined, so if we cut in the image
        # it updates it, and the crpix
        self.dec_npix = self.hdr['NAXIS'+decax] 
        self.y_npix = self.hdr['NAXIS'+decax]
        #TODO crpix has to be updated when cutting in the image!
        self.dec_crpix = self.hdr['CRPIX'+decax]-1
        
        self.dec_crval = self.hdr['CRVAL'+decax]
        # RA
        raax = str([x for x in self.hdr.keys() if x[:-1]=='CTYPE' and 'RA' in self.hdr[x]][0][-1:])
        self.ra_cdelt = self.hdr['CDELT'+raax]*3600 # arcs
        self.ra_npix = self.hdr['NAXIS'+raax]
        self.x_npix = self.hdr['NAXIS'+raax]
        self.ra_crpix = self.hdr['CRPIX'+raax]-1
        self.ra_crval = self.hdr['CRVAL'+raax]
        if self.datatype[0] in ['CUBE','IMAGE']:
            # create a extent keyword
            #~ ylen, xlen = self.d[0].shape
            #~ ycoords = arange(-ylen/2,ylen/2,1)*self.dec_cdelt
            #~ xcoords = arange(-xlen/2,xlen/2,1)*self.ra_cdelt
            #~ left, right = xcoords[0],xcoords[-1]
            #~ bottom, top = ycoords[0],ycoords[-1]
            #~ extent=(left,right,bottom,top)
            #TODO make the extent keyword update dynamically with how
            # many pixels that are there...
            X = array([0,self.ra_npix-1]) # self.*_npix-1 because we're
            Y = array([0,self.dec_npix-1]) # slicing the python-way
            left,right = (X-self.ra_crpix)*self.ra_cdelt
            bottom,top = (Y-self.dec_crpix)*self.dec_cdelt
            self.extent = (left,right,bottom,top)
            #self.extent = (left,right,bottom,top)
            #~ xcoords = arange(-(self.ra_crpix),(self.ra_npix-self.ra_crpix),1)*self.ra_cdelt
            #~ ycoords = arange(-(self.dec_crpix),(self.dec_npix-self.dec_crpix),1)*self.dec_cdelt
            #~ print xcoords[0],xcoords[-1]
            #~ print left,right
            #~ print ycoords[0],ycoords[-1]
            #~ print bottom,top
        try:
            # convert Beam size from degrees to asecs
            self.bmaj = Unit(self.hdr['BMAJ']*3600, 'asecs')
            self.bmin = Unit(self.hdr['BMIN']*3600, 'asecs')
            self.bpa = Unit(self.hdr['BPA'], 'degrees?')
        except KeyError, ex:
            msg='Header keywords (bmaj,bmin,bpa) incomplete and not loaded.'
            print(msg)
            #~ self.bmaj = None
            #~ self.bmin = None
            #~ self.bpa = None
            #~ self.gain = None
        if 'BUNIT' in self.hdr:
            self.unit = self.hdr['BUNIT']
            # units
            if 'JY/BEAM' in upper(self.unit):
                self.unitpixel = u"Jy\u00b7beam\u207b\u00b9\u00b7channel\u207b\u00b9"
                self.unitint = u"Jy\u00b7beam\u207b\u00b9\u00b7" + KMS
            elif 'K' in upper(self.unit):
                self.unitpixel = u"K\u00b7channel\u207b\u00b9"
                self.unitint = u"K\u00b7" + KMS
        else:
            print('No beam unit in header.')
            self.unitpixel = "INTENSITY"
            self.unitint = "INTEGRATED-INTENSITY"
        # calculate the GAIN of the observations (interferometric observations?)
        if self.datatype[0] in ['CUBE','SDSPECT'] and hasattr(self,'restfreq') and hasattr(self,'bmin'):
            # gain depends on restfreq being there
            self.gain = 8.168e-25*(self.restfreq)**2*self.bmin*self.bmaj
        #
        # Object name
        self.obj = self.hdr['OBJECT']
    def __str__(self):
        print '\n','='*40
        print ' '*8,'FITS file\n'
        print 'Data type : %s' % str(self.datatype[0])
        if self.datatype[1] in [3]:
            print 'Shape of image cube : {0}'.format(self.d.shape)
        print 'Object : %s' % self.obj
        if hasattr(self,'beameff'):
            print 'Beam Efficiency : {0:3.4f}'.format(self.beameff)
        if hasattr(self,'forweff'):
            print 'Fwd Efficiency : {0:3.4f}'.format(self.forweff)
        #
        print ''
        if self.datatype[0] != 'SDSPECT':
            self.ra_size = abs(self.ra_cdelt)*self.ra_npix
            self.dec_size = abs(self.dec_cdelt)*self.dec_npix
            print 'Spatial size of image\n RA\t: %2.3f asec\n DEC\t: %2.3f asec' % (self.ra_size, self.dec_size)
        print 'Phase center '
        print '  RA : {0}'.format(parse_ra(self.ra_crval,string=1))
        print ' DEC : {0}'.format(parse_dec(self.dec_crval,string=1))
        if hasattr(self,'bmaj') and hasattr(self,'bmin') and hasattr(self,'bpa'):
            print '\nBeam info'
            print ' Beam major axis : {0}'.format(self.bmaj)
            print ' Beam minor axis : {0}'.format(self.bmin)
            print ' Beam position angle : {0}'.format(self.bpa)
        #
        print ''
        if hasattr(self,'restfreq'):
            if (1E-9*self.restfreq)<1:
                freq = 1E-6*self.restfreq
                freq_unit = 'MHz'
            else:
                freq = 1E-9*self.restfreq
                freq_unit = 'GHz'
            print 'Rest frequency of data : {0} {1}'.format(freq,freq_unit)
        return '\n ADAVIS - Fitsfile Object \n'
    def parse_pxlcoord (self, x, y):
        """ Function doc """
        #TODO : use pywcs to parse
        xoffset = (x-self.ra_crpix)*self.ra_cdelt
        yoffset = (y-self.dec_crpix)*self.dec_cdelt
        return xoffset, yoffset
    def parse_region(self, region, f=False):
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

        *2011/10/03 incorporated into the Fits class

        """
        #TODO : use pywcs to parse
        from scipy import ceil, floor, array
        from sys import exit as sysexit
        if len(region)==4:
            xcheck = region[0]==region[2]
            ycheck = region[1]==region[3]
            #~ if region[0]<region[2]: # if you enter it as in miriad i.e. (-5,-5,5,5)
                #~ reg2 = region[2]
                #~ reg0 = region[0]
                #~ region[0] = reg2
                #~ region[2] = reg0
            #x1, x2 = (data.ra_npix+1)/2 + array([region[0],region[2]])/abs(data.ra_cdelt) + array([0,xcheck])
            #y1, y2 = (data.dec_npix+1)/2+ array([region[1],region[3]])/abs(data.dec_cdelt)+ array([0,ycheck])
            #
            x1, x2 = array([region[0],region[2]])/self.ra_cdelt + self.ra_crpix + array([0,xcheck])
            y1, y2 = array([region[1],region[3]])/self.dec_cdelt + self.dec_crpix + array([0,ycheck])
            #
        elif len(region)==3:
            check = region[2]==0
            #x1, x2 = (data.ra_npix+1)/2 + array([-region[2],region[2]])/(2*abs(data.ra_cdelt)) + region[0]/data.ra_cdelt + array([0,check])
            #y1, y2 = (data.dec_npix+1)/2+ array([-region[2],region[2]])/(2*abs(data.dec_cdelt)) +region[1]/data.dec_cdelt+ array([0,check])
            #
            x1, x2 = self.ra_crpix + region[0]/self.ra_cdelt + array([-region[2],region[2]])/abs(2*self.ra_cdelt) + array([0,check])
            y1, y2 = self.dec_crpix + region[1]/self.dec_cdelt + array([-region[2],region[2]])/abs(2*self.dec_cdelt) + array([0,check])
            #
        elif len(region)==2:
            xcheck = region[0]==0
            ycheck = region[1]==0
            #x1, x2 = (data.ra_npix+1)/2 + array([-1,1])*region[0]/abs(data.ra_cdelt)  + array([0,xcheck])
            #y1, y2 = (data.dec_npix+1)/2+ array([-1,1])*region[1]/abs(data.dec_cdelt) + array([0,ycheck])
            #
            x1, x2 = array([-region[0],region[0]])/(2*abs(self.ra_cdelt)) + self.ra_crpix + array([0,xcheck])
            y1, y2 = array([-region[1],region[1]])/(2*abs(self.dec_cdelt)) + self.dec_crpix + array([0,ycheck])
            #
        elif():
            print ('Error, region keyword malformed')
            sysexit(1)
            #
        # so that we are returning usable pixel coordinates
        if f==False:
            x1,x2,y1,y2 = array([x1,x2,y1,y2]).round().astype('int')
        return x1,x2,y1,y2
    def calc_fov(self):
        # method to calculate FOV after the correct telescope name/diameter
        # has been input and thus correcting the current FOV of
        # the DataObject
        if self.telescope!=None:
            self.diameter = get_telescope_diameter(self.telescope)
        elif self.diameter == 1:
            print 'You have not changed either the diameter of the telescope or the telescope name'
        self.fov = 58.4*(3.e8/self.restfreq)/float(self.diameter)*3600.
    def calc_rms(self, nvals, area):
        from scipy import sqrt,array
        i1,i2,j1,j2 = self.parse_region(area)
        n_channels = get_indices(self.v_arr, nvals)
        # just to find out which channels (start, stop) to print
        if len(nvals)==2:
            n = array([n_channels.min(),n_channels.max()])
            nv = self.v_arr[n]
            print "RMS calculated in intervals {0} ({1}) and region {2}".format(n, nv,nvals,area)
        if len(nvals)==4:
            n_1 = get_indices(self.v_arr,array(nvals)[:2])
            n_1min = min(n_1)
            n_1max = max(n_1)
            n_2 = get_indices(self.v_arr,array(nvals)[2:])
            n_2min = min(n_2)
            n_2max = max(n_2)
            #n = array([n_channels.min(),n_channels.max()])
            #nv = self.v_arr[n]
            print "RMS calculated in intervals {0} and {1} ({2}) and region {3}".format([n_1min,n_1max], [n_2min,n_2max],nvals,area)
        rms_data = self.d[n_channels]
        self.rms = sqrt(((rms_data[:, j1:j2, i1:i2])**2).mean())
        del rms_data
    def add_line(self, name, frequency=None, channels=None, width=None):
        """
        Add identified line(s) to the class

        TODO : update the fits file as well?
        TODO : move this to the spectrum class?
        '"""
        try:
            known_lines = self.known_lines
        except AttributeError, ex:
            known_lines = {}
        known_lines[204.38343] = {'name' : 'SO$_2$','frequency' : frequency, 'channels' : channels, 'width' : width}
    #
    def phase_center_string(self):
        ra = parse_ra(self.ra_crval, string = True)
        dec = parse_dec(self.dec_crval, string = True)
        center = [ra, dec]
        return center
    
    def calc_offset(self, InputData):
        #~ ra, dec = self.phase_center_string()
        ra, dec = self.ra_crval, self.dec_crval
        return calc_offset(ra, dec, data = InputData, display = False)
    # method to change the v_sys
    def change_v_sys (self, v_sys):
        self.v_sys = v_sys
        # now, change the v_arr_syscorr array as well
        if self.datatype[0] in ['CUBE', 'SDSPECT']:
            self.v_arr_syscorr = self.v_arr - self.v_sys
    #
    def change_dist (self, dist):
        self.dist = dist # unit of pc

    def box_cut(self,region=[-10,10,-10,10]):
        pass

# UV-FITS DATA CLASS
class Uvfits(object):
    """
    Read uv-fits data
    --------------------------------------------------------------------
    Normal structure of UV-fits data:

    Header : same as for normal fits

    Data : Group data

    --------------------------------------------------------------------

    TODO :  Assumes that CRVAL4 is frequency, is that always true?
            Make it more robust, look for the frequency keyword, either as
            "restfreq" or as a "crvalX"

    TODO :  UV fit method
    TODO : __str__ method, information about:
                - Phase center
                - No correlations
                - No baselines
                - No antennas
                - Telescope (if present)
    """
    def __init__(self, uvfitsfile, telescope=None, vsys=0, distance=0, endian=None, **kwargs):
        """

        Reads the uvfits and calculates useful things, e.g. u,v,w,
        phase and amplitude

        .byteswap().newbyteorder() is applied in various places to
        convert to little endian

        """
        print('Depricated in favour of uvfits.py in same catalog')
        #~ from pyfits import open as pfopen
        from astropy.io.fits import open as pfopen
        
        from scipy import sqrt, pi, arctan2
        import numpy as _np
        import adapy
        from adapy.libs import cgsconst
        from astropy import wcs
        f = pfopen(uvfitsfile, **kwargs)
        self.loadendian = endian
        if f[0].header['NAXIS1'] != 0:
            print "error: this file may not be a UV FITS."
            raise FileError('File format error.')
        #~ f.info()
        try:
            self.hdu = f[0]
        except:
            print "error: cannot open uv data HDU."
        self.hdr = self.hdu.header
        self.data = self.hdu.data
        self.WCS = wcs.WCS(self.hdr)
        
        if self.hdr['NAXIS4'] > 1:
            self.datatype = ('CUBE', 3)
        else:
            self.datatype = ('IMAGE', 2)
        
        # find spectral axis
        axis_types = self.WCS.get_axis_types()
        ax_types = np.array([i['coordinate_type'] for i in axis_types])
        try:
            spec_axis = ('spectral' == ax_types).nonzero()[0][0]
            freq = self.hdu.header['CRVAL{0}'.format(spec_axis+1)]
            # assumes the frequency given in Hz
            self.freq = freq
            self.freq_unit = freq * un.Hz
        except (IndexError):
            print('No spectral axis in header.')
            spec_axis = -1
            self.freq = None
           
       
        if 'RESTFREQ' in self.hdu.header.keys():
            self.restfreq = self.hdu.header['RESTFREQ']
            self.restfreq_unit = self.hdu.header['RESTFREQ'] * u.Hz
        else:
            raise StandardError('No restfrequency found, NEED it!')
        #TODO : Read in velocity and frequency array if present
        """
        The standard unit is to give UU and VV in seconds (??!?)
        So we have to convert to whatever we want.
        """
        # standard storing unit here is kilo-lambdas
        # save a million lines of code!
        u.add_enabled_equivalencies(lambdas_equivalencies(self.restfreq_unit))
        self.u = (self.data.par('UU') * u.s).to(klambdas)
        self.v = (self.data.par('VV') * u.s).to(klambdas)
        self.w = (self.data.par('WW') * u.s).to(klambdas)
        # unit nano seconds
        #~ self.u_nsec = self.data.par('UU') * 1.0e+9
        #~ self.v_nsec = self.data.par('VV') * 1.0e+9
        #~ self.w_nsec = self.data.par('WW') * 1.0e+9
        #CC_cm = a.CC*1e2 # light speed in cm/s
        #lmd = lsp / freq
        # u_klam = uu * CC_cm / (CC_cm/freq)
        # unit kilo lamda
        self.u_lam = self.data.par('UU') * freq
        self.v_lam = self.data.par('VV') * freq
        self.w_lam = self.data.par('WW') * freq
        # unit lamda
        self.u_klam = self.data.par('UU') * freq * 1.0e-3
        self.v_klam = self.data.par('VV') * freq * 1.0e-3
        self.w_klam = self.data.par('WW') * freq * 1.0e-3
        # unit meters
        self.u_m = self.data.par('UU') * cgsconst.CC * 1.0e-2
        self.v_m = self.data.par('VV') * cgsconst.CC * 1.0e-2
        self.w_m = self.data.par('WW') * cgsconst.CC * 1.0e-2
        # uv distance
        #~ self.uvdist_nsec = sqrt(self.u_nsec**2 +self.v_nsec**2 + self.w_nsec**2)
        #~ self.uvdist_klam = sqrt(self.u_klam**2 +self.v_klam**2  + self.w_klam**2)
        #~ self.uvdist_lam = sqrt(self.u_lam**2 +self.v_lam**2  + self.w_lam**2)
        #~ self.uvdist_m = sqrt(self.u_m**2 +self.v_m**2 + self.w_m**2)
        self.uvdist_klam = sqrt(self.u_klam**2 +self.v_klam**2)
        self.uvdist_lam = sqrt(self.u_lam**2 +self.v_lam**2)
        self.uvdist_m = sqrt(self.u_m**2 +self.v_m**2)

        # BASELINE
        self.baseline = self.hdu.data.par('BASELINE').byteswap().newbyteorder()
        # DATES
        self.jdate = self.hdu.data.par('DATE')
        self.date = _sp.array([jd2gd(i) for i in self.jdate])
        self.date0 = self.date.transpose()
        fields = ['year', 'month', 'day', 'hour', 'minute', 'sec']
        self.date1 = {key:value for key,value in zip(fields, self.date0)}
        # convert to datetime objects
        # LOSES the sub-second resolution
        self.date2 = [_dt(int(i[0]), int(i[1]), int(i[2]), int(i[3]), int(i[4]), int(i[5])) for i in self.date]
        
        # get number of tracks
        # TODO : rough hack, separate track if diff day is >1
        tmp = _sp.where(_sp.diff(_sp.unique(self.jdate.round(0)))>1)[0]
        self.ntracks = len(tmp)+1
        
        ################################################################
        # NB : need to streamline this.
        # only load the complex visibilities, into a complex array
        # AND then work on that
        
        
        # COMPLEX VISIBILITY
        visi_index = len(self.data.parnames)
        if self.hdu.header['NAXIS']  == 7:
            self.visdata = self.data.par(visi_index)[:,0,0,0,0,0,:].byteswap().newbyteorder()
        #~ self.visdata = self.hdu.data.data[:,0,0,0,0,0,:]
        elif self.hdu.header['NAXIS']  == 6:
            self.visdata = self.data.par(visi_index)[:,0,0,0,0,:].byteswap().newbyteorder()
        # load the re, im and weight arrays
        self.re, self.im, self.wt = self.visdata[:,:].T
        #~ self.re = self.visdata[:,0][:]
        #~ self.im = self.visdata[:,1][:]
        #~ self.wt = self.visdata[:,2][:]
        # complex numbers
        #~ self.comp = self.visdata[:,:2].astype(_np.float64).view(_np.complexfloating)
        #~ self.comp = 1j*self.visdata[:,1][:]
        #~ self.comp += self.visdata[:,0][:]
        self.comp = self.visdata[:,:2].astype(_np.float).view(_np.complex)
        """
        with complex array, you can do
        amp = np.abs(vis)
        np.angle(vis)   
        vis.real
        vis.imag
        
        """
        # the data is not shifted
        self.isshifted = (False, [0,0])
        # AMPLITUDE 
        self.amp = sqrt(self.re**2 + self.im**2)
        # PHASE
        self.pha = arctan2(self.im, self.re)
        self.pha_deg = self.pha / pi * 180.
        # ERROR / SIGMA
        #TODO : check
        # following 1.0e6 is just for GILDAS, change if needed
        #~ print('NB : Error calculated from weights assuming GILDAS '
        #~ 'data (i.e. frequencies in MHz).')
        self.sigma_alt = 1/sqrt(self.wt*1.0e6)
        # Daniels way of calculating sigma
        # test this first
        self.sigma = _sp.sqrt(0.5 / ( self.wt * float(self.amp.shape[0]) ) )
        #np.sqrt( 0.5/self.wt/float(self.amp.shape[0]) )

    def load_model(self, modelfile, endian = None):
        if endian != None: # overrides the endianness of data loading
            self.Model = Uvfits(modelfile, endian = endian)
        else:
            # make sure it loads the same endian format as data
            self.Model = Uvfits(modelfile, endian = self.loadendian)

    def bin_data_DMC(self,ruv=None, binsize=10):
        """
        Function to bin data
        
        """
        class BinnedDMC:
            pass

        # Bin model
        if self.__dict__.has_key('Model'):
            # If model is loaded, bin that as well
            # to the same bins
            pass
        if ruv is not None:
            uvdist = ruv
        else:
            uvdist = self.uvdist_klam
    
        uvmin = uvdist.min()
        uvmax = uvdist.max()
        # Define the bins
        nbin = int( (uvmax-uvmin)/binsize)+5
        arr_bins = _sp.arange(nbin)
        arr_bins = binsize * arr_bins
        arr_bins1 = 0.5*(arr_bins[1:]+arr_bins[:-1])
        print 'Bin Size: {0}, {1}, {2}'.format(binsize, arr_bins.min(), arr_bins.max())
        # in klamda
        print 'UV Dist: {0:.1f} - {1:.1f} klam'.format(uvmin, uvmax)
        # prepare the data structures to store result in
        uvampdat = _sp.zeros([nbin-1,3,3])  # bins for real, img, amp with n points, mean, dispersion
        expt = _sp.zeros(nbin-1)            # Expected value for no signal
        sn = _sp.zeros(nbin-1)              # signal to noise
        for ibin in range(nbin-1):
            # ibin - index of current working bin
            # to store stuff in the prepared arrays
            minbin = arr_bins[ibin]
            maxbin = arr_bins[ibin]+binsize
            isubs = ( (uvdist < maxbin) == (uvdist >= minbin) ).nonzero()[0]
            npoints = len(isubs)
            if npoints > 0:
                # real
                reals = self.re[isubs]
                wts = self.wt[isubs]
                # Get rid of the negative weights
                wtsubs = (wts >= 0.0).nonzero()[0]
                wts = wts[wtsubs]
                reals = reals[wtsubs]
                npts = int(len(wtsubs))
                # points in each interval(?)
                uvampdat[ibin,0,0] = int(len(wtsubs))
                # mean real value
                uvampdat[ibin,0,1] = (reals).sum()/(npoints)
                uvampdat[ibin,0,2] = _sp.sqrt(( (reals*reals).sum() - (npoints*uvampdat[ibin,0,1]*uvampdat[ibin,0,1]))/(npoints-1))
                # Imaginary
                reals = self.im[isubs]
                uvampdat[ibin,1,0] = int(len(wtsubs))
                uvampdat[ibin,1,1] = (reals).sum()/(npoints)
                uvampdat[ibin,1,2] = _sp.sqrt(( (reals*reals).sum() - (npoints*uvampdat[ibin,1,1]*uvampdat[ibin,1,1]))/(npoints-1))
                # amplitudes
                reals = self.amp[isubs]
                # take real and imaginary part, calculate amplitude
                uvampdat[ibin,2,0] = int(len(wtsubs))
                x = uvampdat[ibin,0,1]
                xerr = uvampdat[ibin,0,2]
                y = uvampdat[ibin,1,1]
                yerr = uvampdat[ibin,1,2]
                temp_amp = _sp.sqrt(x*x + y*y)
                uvampdat[ibin,2,1] = temp_amp
                sigtot = (x*xerr/(temp_amp))**(2.0) + (y*yerr/(temp_amp))**(2.0)
                uvampdat[ibin,2,2] =  _sp.sqrt(sigtot/(npts-2))
                if uvampdat[ibin,2,2] > 0.0:
                    sn[ibin] = temp_amp/uvampdat[ibin,2,2]
                else:
                    sn[ibin] = 0.0
                expt[ibin] = (_sp.sqrt(_sp.pi/2.0))*uvampdat[ibin,2,2]
            else:
                pass
                
        BinnedDMC.nbin = nbin
        BinnedDMC.bins = arr_bins1
        BinnedDMC.uvamp = uvampdat
        BinnedDMC.expt = expt
        self.BinnedDMC = BinnedDMC

    def bin_data(self, ruv=None, binsize=10, nbins=30, ignore_wt=False, **kwargs):
        """
        Function to bin UV data, both vector and scalar average is calculated
        creates Bin.Sca and Bin.Vec objects in self
        
        needs : uvdist_klam
                re, im, wt, amp
        TODO: move core calcs to separate function for reuse
        """
     
        if self.__dict__.has_key('Model'):
            if ruv is not None:
                uvdist = ruv
            else:
                uvdist = self.Model.uvdist_klam
            mre = self.Model.re
            mim = self.Model.im
            if ignore_wt:
                mwt = _sp.ones_like(self.Model.re)
            else:
                mwt = self.Model.wt
            self.Model.BinVec = uv_bin_vector(uvdist, mre, mim, mwt, binsize=binsize, nbins=nbins, **kwargs)
            self.Model.BinSca = uv_bin_scalar(uvdist, mre, mim, mwt, binsize=binsize, nbins=nbins, **kwargs)
        if ruv is not None:
            uvdist = ruv
        else:
            uvdist = self.uvdist_klam
        if ignore_wt:
                wt = _sp.ones_like(self.re)
        else:
                wt = self.wt
        self.BinVec = uv_bin_vector(uvdist, self.re, self.im, wt, binsize=binsize, nbins=nbins, **kwargs)
        self.BinSca = uv_bin_scalar(uvdist, self.re, self.im, wt, binsize=binsize, nbins=nbins, **kwargs)
        
    def shift(self, offset):
        if 'isshifted' in self.__dict__.keys():
            print('Data already shifted once, aborting')
            return False
        # create input
        uv = _sp.array([self.u_klam, self.v_klam])
        reim = _sp.array([self.re, self.im])
        # shift/translate the data
        phas, re, im = translate(self.u_klam, self.v_klam, offset)
        # store in self
        self.re = re
        self.im = im
        self.isshifted = (True, offset)
        print('Only shifts the current object')

    def rotate(self, deg, force=False):
        if 'isrotated' in self.__dict__.keys() and not force:
            print('Data already rotated once, aborting')
            return False
        # kilo-lambda
        uv = _sp.array([self.u_klam, self.v_klam])
        self.u_klam, self.v_klam = rotate_field(uv, deg)
        # meters
        uv = _sp.array([self.u_m, self.v_m])
        self.u_m, self.v_m = rotate_field(uv, deg)
        # nano seconds
        #~ uv = _sp.array([self.u_nsec, self.v_nsec])
        #~ self.u_nsec, self.v_nsec = rotate_field(uv, deg)
        # set isrotated to True, so we can check how much it was rotated
        self.isrotated = (True, deg)
        # print('Only rotates the current object.')
        # calculate new uvdistances
        # print('Calculating new uvdistances, better way to implement this,\
        #  need base entities that are used on the fly to calc. other')
        #~ self.uvdist_nsec = _sp.sqrt(self.u_nsec**2 +self.v_nsec**2 + self.w_nsec**2)
        self.uvdist_klam = _sp.sqrt(self.u_klam**2 +self.v_klam**2  + self.w_klam**2)
        self.uvdist_m = _sp.sqrt(self.u_m**2 +self.v_m**2 + self.w_m**2)
        
    def incline(self, deg):
        # print('incline only works on kilo-lamda uv points')
        # klam
        uv = _sp.array([self.u_klam, self.v_klam])
        self.uvdist_klam = incline(uv, deg)
        # set flag isinclined to True and the amount of degrees
        self.isinclined = (True, deg)
        # print('Only inclines the current object, if binned b4, bin again')
        
    def deproject(self, PA, inc):
        uvin = _sp.array([self.u_klam, self.v_klam])
        newuv_klam, ruv_klam = deproject(uvin, PA, inc)
        
        # store original values
        class UV_original: pass
        UV_original.uvdist_klam = self.uvdist_klam[:]
        UV_original.u_klam = self.u_klam[:]
        UV_original.v_klam = self.v_klam[:]
        self.UV_original = UV_original
        
        self.uvdist_klam = ruv_klam
        self.u_klam = newuv_klam[0]
        self.v_klam = newuv_klam[1]
        self.uvdist_lam = ruv_klam*1e3
        self.u_lam = newuv_klam[0]*1e3
        self.v_lam = newuv_klam[1]*1e3
        self.uvdist_m = ruv_klam / (self.freq * 1.0e-3) * co.c.cgs.value * 1.0e-2
        self.u_m = newuv_klam[0] / (self.freq * 1.0e-3) * co.c.cgs.value * 1.0e-2
        self.v_m = newuv_klam[1] / (self.freq * 1.0e-3) * co.c.cgs.value * 1.0e-2
        
        self.isrotated = (True, PA)
        self.isinclined = (True, inc)
        
    def reset_projection(self):
        
        if 'UV_original' in self.__dict__.keys():
            self.uvdist_klam = self.UV_original.uvdist_klam[:]
            self.u_klam = self.UV_original.u_klam[:]
            self.v_klam = self.UV_original.v_klam[:]
            self.uvdist_lam = self.UV_original.uvdist_klam[:]*1e3
            self.u_lam = self.UV_original.u_klam[:]*1e3
            self.v_lam = self.UV_original.v_klam[:]*1e3
            self.uvdist_m = self.UV_original.uvdist_klam[:] / (self.freq * 1.0e-3) * co.c.cgs.value * 1.0e-2
            self.u_m = self.UV_original.u_klam[:] / (self.freq * 1.0e-3) * co.c.cgs.value * 1.0e-2
            self.v_m = self.UV_original.v_klam[:] / (self.freq * 1.0e-3) * co.c.cgs.value * 1.0e-2
        else:
            print self.isrotated
            print self.isinclined
            raise StandardError('No orignal UV points saved.')
            
        
        
    def __str__():
        return 'Not implemented yet...'

#########################

def uv_bin_vector(uvdist, re, im, wt, start='zero', binsize=10, nbins=50, weighted=False):
    """

    Vector averaging of amplitudes
    Calculate the binned amplitude and various related things.
    The binned amplitude is calculated from the real and imaginary
    part of the visibilities.
    
    
    zero : where to start the binning, at uvdist = 0, or min(uvdist)

    Description
    ===========
    Vector binning of the amplitude, first bin the real and
    imaginary parts as
    RE = sum(RE_i)/Np (Mean) (not the weighted mean, should be?)
    RE_sig = sqrt( ( sum(RE_i^2) - Np * RE^2 ) / (Np - 1) )
    (-1 because we determined the mean)
    the same goes for the Imaginary part.
    
    the square root of the sum of the squared real and imaginary parts
    A = sqrt( RE^2 + IM^2 )

    and the error propagation of the
    variance of the real and imaginary parts
    A_sig = sqrt( ((RE*RE_sig/A)^2 + (IM*IM_sig/A)^2) / (Np - 2) )
    

    NOTES
    =====
    Some parts divide with possible zeros.
    This operation will create 'nan' entries which messes things
    when running calculations on it, i.e. nan*2 = nan
    therefore I've started using masked arrays.

    
    """
    class Binned_Vector(object):
            pass
    ##### CORE CALC START #####
    if start in ['zero', 0, '0']:
        uvmin = 0.0
    elif start in ['min']:
        uvmin = uvdist.min()
    uvmax = uvmin + binsize * (int(nbins) + 0.5)
    # Define the bins, from uvmin to uvmax
    arr_bins = _sp.arange(_sp.floor(uvmin),
                            _sp.ceil(uvmax),
                            binsize)
    # mid-points of the bins
    arr_bins1 = 0.5*(arr_bins[1:] + arr_bins[:-1])
    minmax = zip(arr_bins[:-1], arr_bins[1:])
    # only choose data with positive weigths
    pos_wt = wt>= 0.0
    def filter_points(i,j):
        # find the indices of data within the limits and
        # with positive weigths
        # i:lower boundary, j:upper boundary
        return ( (uvdist>=i) * (uvdist<j) * pos_wt).nonzero()[0]
    isubs = [filter_points(i,j) for i,j in minmax]
    npoints = _sp.array([len(i) for i in isubs])       # points in each interval
    ###########################################################################
    # Real and Imaginary data binning
    data = _sp.array([re[:], im[:]])
    # mean for Re and Im separately
    if not weighted:
        # changed this
        #~ data_mean = _sp.array([data[:,i].mean(axis=1) for i in isubs])
        # to this instead, got some problems with not explicitly setting
        # value to nan, do not rely on mean or average to take care of it
        # here we use a masked array, which handles the nan much better
        # removed masked arrays again!
        # print('method takes into account nan raw data values')
        data_mean =  _sp.array([_sp.nanmean(data[:,i], axis=1) if j>0 else _sp.array([_sp.nan, _sp.nan]) for i,j in zip(isubs,npoints)])
        #~ check = _sp.array([npoints==0, npoints==0]).T
        #~ data_mean = _sp.ma.masked_array(data_mean, check, fill_value=_sp.nan)
        #~ data_mean = _sp.ma.masked_array(data_mean,_sp.isnan(data_mean), fill_value=_sp.nan)
    elif weighted:
        print ('Calculating weighted average real and imaginary amplitudes')
        print ('method does not take into account nan raw data values')
        # doesn't work if isubs is empty somewhere
        #~ data_mean = _sp.array([_sp.average(data[:,i], axis=1, weights=wt[i]) for i in isubs])
        data_mean = _sp.array([_sp.average(data[:,i], axis=1, weights=wt[i]) if j>0 else _sp.array([_sp.nan, _sp.nan]) for i,j in zip(isubs,npoints)], dtype='float')
        #~ data_mean = _sp.ma.masked_array(data_mean,_sp.isnan(data_mean))
    # Error of real and imaginary data
    #~ data_var = _sp.array([_sp.var(data[:,i], ddof=1, axis=1) if j>0 else _sp.array([_sp.nan, _sp.nan]) for i,j in zip(isubs,npoints)])
    # ddof = j-1, the number of points in bin, minus the parameter determined
    # i.e. the mean.
    data_var = _sp.array([_sp.var(data[:,i], ddof=1, axis=1) if j>0 else _sp.array([_sp.nan, _sp.nan]) for i,j in zip(isubs,npoints)])
    #~ data_var = _sp.ma.masked_array(data_var,_sp.isnan(data_var), fill_value=_sp.nan)

    #~ data_var[data_var==-0] = _sp.nan
    #~ data_var = _sp.ma.masked_array(data_var, data_var==-0, fill_value=_sp.nan)

    #~ data_std = _sp.ma.sqrt(data_var)
    data_std = data_var**0.5 # used sqrt here before, got floating point error
    # Amplitude binning
    amp_mean = ( (data_mean**2).sum(axis=1) )**0.5
    #~ amp_mean = _sp.sqrt( (data_mean**2).sum(axis=1) )
    amp_tmp = amp_mean.reshape((len(amp_mean), 1))
    # calculate the variance of the amplitude
    # error propagation of the variance of the imaginary
    # and real parts
    # if the amp_temp is close to zero, we can end up with
    # inf in variance.
    pars=2
    dof = _sp.array([float(i-pars) if i>0 else 0.0 for i in npoints])
    amp_var = (( ( data_mean * data_var / amp_tmp )**2).sum(axis=1)
        / ( dof ) )**0.5
    amp_std = amp_var**0.5
    # Signal to Noise (SNR), _sp.divide gives 0 when dividing by 0
    amp_snr = _sp.divide( amp_mean, amp_var )
    # expectation value when no signal
    amp_expt = _sp.sqrt( _sp.pi / 2. ) * amp_var
    ###########################################################################
    # get the binned real and imaginary parts
    re_mean, im_mean = data_mean.T
    re_var, im_var = data_var.T
    re_std, im_std = data_std.T
    # Signal to Noise (SNR), _sp.divide gives 0 when dividing by 0
    re_snr, im_snr = _sp.divide(data_mean, data_var).T
    # expectation value when no signal
    re_expt, im_expt = _sp.sqrt( _sp.pi / 2. ) * data_var.T

    ###########################################################################
    ##### CORE CALC END #####

    # store in class        
    #~ Binned_Vector.nbin = nbin
    Binned_Vector.npoints = npoints
    Binned_Vector.bins = arr_bins1
    Binned_Vector.uvdist_klam = arr_bins1
    Binned_Vector.amp = amp_mean
    Binned_Vector.amp_var = amp_var
    Binned_Vector.amp_std = amp_std
    Binned_Vector.data = data_mean
    Binned_Vector.data_var = data_var
    Binned_Vector.data_std = data_std
    Binned_Vector.snr = amp_snr
    Binned_Vector.expt = amp_expt
    # store Re in class        
    Binned_Vector.re = re_mean
    Binned_Vector.re_var = re_var
    Binned_Vector.re_snr = re_snr
    Binned_Vector.re_expt = re_expt
    # store Im in class        
    Binned_Vector.im = im_mean
    Binned_Vector.im_var = im_var
    Binned_Vector.im_snr = im_snr
    Binned_Vector.im_expt = im_expt
    
    return Binned_Vector

def uv_bin_scalar(uvdist, re, im, wt, start='zero', binsize=10, nbins=50, weighted=False):
    """
    Scalar averaging amplitudes
    
    NOTES
    =====
    Some parts divide with possible zeros.
    This operation will create 'nan' entries which messes things
    when running calculations on it, i.e. nan*2 = nan
    therefore I've started using masked arrays.
    
    """
    class Binned_Scalar(object):
            pass
    ##### CORE CALC START #####
    if start in ['zero', 0, '0']:
        uvmin = 0.0
    elif start in ['min']:
        uvmin = uvdist.min()
    uvmax = uvmin + binsize * (int(nbins) + 0.5)
    #~ binsize = int(round(((uvmax-uvmin)/nbins), 0 ))
    # Define the bins, from uvmin to uvmax
    #~ arr_bins = _sp.linspace(uvmin, uvmax, nbins)
    arr_bins = _sp.arange(_sp.floor(uvmin),
                            _sp.ceil(uvmax),
                            binsize)
    #~ print ('{0} bins with {1} binsize'.format(nbins, binsize))
    #~ print len(arr_bins)
    # mid-points of the bins
    arr_bins1 = 0.5*(arr_bins[1:] + arr_bins[:-1])
    minmax = zip(arr_bins[:-1], arr_bins[1:])
    # only choose data with positive weigths
    pos_wt = wt>= 0.0
    def filter_points(i,j):
        # find the indices of data within the limits and
        # with positive weigths
        # i:lower boundary, j:upper boundary
        return ( (uvdist>=i) * (uvdist<j) * pos_wt).nonzero()[0]
    isubs = [filter_points(i,j) for i,j in minmax]
    npoints = _sp.array([len(i) for i in isubs])       # points in each interval
    ###########################################################################
    # AMPLITUDE 
    amp = _sp.sqrt(re**2 + im**2)
    # PHASE
    pha = _sp.arctan2(im, re)
    pha_deg = pha / _sp.pi * 180.
    # put amp and pha in an array
    data = _sp.array([amp, pha])
    # ERROR / SIGMA
    #TODO : check
    # following 1.0e6 is just for GILDAS, change if needed
    #~ print('NB : Error calculated from weights assuming GILDAS '
    #~ 'data (i.e. frequencies in MHz).')
    #~ self.sigma = 1/sqrt(self.wt*1.0e6)
    # Daniels way of calculating sigma
    # test this first
    sigma = _sp.sqrt(0.5 / ( wt * float(amp.shape[0]) ) )
    
    if not weighted:
        data_mean = _sp.array([_sp.nanmean(data[:,i], axis=1) if j>0 else _sp.array([_sp.nan, _sp.nan]) for i,j in zip(isubs,npoints)])
        # above operation create some 'nan' entries which messes things up
        # later on if we're not using a masked array
        #~ data_mean = _sp.ma.masked_array(data_mean,_sp.isnan(data_mean))
    elif weighted:
        print ('Calculating weighted average amplitudes')
        data_mean = _sp.array([_sp.average(data[:,i], axis=1, weights=wt[i]) if j>0 else _sp.array([_sp.nan, _sp.nan])  for i,j in zip(isubs,npoints)])
        #~ data_mean = _sp.ma.masked_array(data_mean,_sp.isnan(data_mean), fill_value=_sp.nan)
    # variance and standard deviation
    data_var = _sp.array([_sp.var(data[:,i], ddof=1, axis=1) if j>0 else _sp.array([_sp.nan, _sp.nan]) for i,j in zip(isubs,npoints)])
    #~ data_var[data_var==-0] = _sp.nan
    #~ data_var = _sp.ma.masked_array(data_var, data_var == -0, fill_value=_sp.nan)
    data_std = data_var**0.5
    
    amp_mean, pha_mean = data_mean.T
    amp_var, pha_var = data_var.T
    amp_std, pha_std = data_std.T
    
    # Signal to Noise (SNR), _sp.divide gives 0 when dividing by 0
    amp_snr, pha_snr = _sp.divide(data_mean, data_var).T
    # expectation value when no signal
    amp_expt, pha_expt = _sp.sqrt( _sp.pi / 2. ) * data_var.T
    
    ###########################################################################
    ##### CORE CALC END #####

    # store in class        
    #~ Binned.nbin = nbin
    Binned_Scalar.npoints = npoints
    Binned_Scalar.bins = arr_bins1
    Binned_Scalar.uvdist_klam = arr_bins1
    Binned_Scalar.data = data_mean
    Binned_Scalar.data_var = data_var
    Binned_Scalar.amp = amp_mean
    Binned_Scalar.amp_var = amp_var
    Binned_Scalar.amp_snr = amp_snr
    Binned_Scalar.amp_expt = amp_expt
    Binned_Scalar.pha = pha_mean
    Binned_Scalar.pha_var = pha_var
    Binned_Scalar.pha_snr = pha_snr
    Binned_Scalar.pha_expt = pha_expt
    
    # send back an object with all the data structures
    return Binned_Scalar

def translate(uv_klam, reim, offset):
    print ('Has a -1 multiplied here, is this right?')
    phas = -1.0*( ((uv_klam[0])*(offset[0]/pc2au)) +
            ((uv_klam[1])*(offset[1]/pc2au)))*2.0*pi
    re = (reim[0]*_sp.cos(phas)) - (reim[1]*_sp.sin(phas))
    im = (reim[0]*_sp.sin(phas)) + (reim[1]*_sp.cos(phas))
    return phas, re, im

def deproject(uv, PA, inc):
    """
    Rotate and deproject individual visibility coordinates.
    From Hughes et al. (2007) - "AN INNER HOLE IN THE DISK AROUND 
    TW HYDRAE RESOLVED IN 7 mm DUST EMISSION".
    """
    R = ( (uv**2).sum(axis=0) )**0.5
    #~ phi = _sp.arctan(uv[1]/uv[0] - deg2rad(PA))
    phi = _sp.arctan2(uv[1],uv[0]) - deg2rad(PA)
    #~ phi = _sp.arctan2( (uv[1] - deg2rad(PA) * uv[0]) , uv[0])
    newu = R * _sp.cos(phi) * _sp.cos( deg2rad(inc) )
    newv = R * _sp.sin(phi)
    newuv = _sp.array([newu, newv])
    ruv = (newuv**2).sum(axis=0)**.5
    return newuv, ruv

def rotate_field(uv, PA, U_RA_align = True):
    """
    Rotates a coordinate system (UV plane) by PA
    degrees.
    uv : 2-D array with uv[0] U and uv[1] coordinated
    PA : Position Angle, in degrees
    U_RA_align : for ALMA and PdBI the U-axis and RA are aligned
                 and thus one form of the equation must be used
                 While for SMA/CARMA (USA, meh), they are not aligned
                 and thus some sign changes have to impliemented from
                 that presented in Berger & Segransan (2007)
    
    """
    direction =  [-1, 1][int(U_RA_align)]
    u_new = uv[0] * _sp.cos( deg2rad(PA) ) + direction * uv[1] * _sp.sin( deg2rad(PA) )
    v_new = -1 * direction * uv[0] * _sp.sin( deg2rad(PA) ) + uv[1] * _sp.cos( deg2rad(PA) )
    return u_new, v_new
    
def incline(uv, inc):
    #~ ruv = ( uv[0]**2 + (uv[1] * _sp.cos(deg2rad(inc)) )**2  )**.5 
    # the PA goes from North to East in the image plane, and the 
    # Major axis is flipped 90 degrees going from
    # image to UV plane (Major in image in minor in UV)
    ruv = ( uv[0]**2 * _sp.cos(deg2rad(inc))**2 + uv[1]**2  )**.5 
    return ruv

    
