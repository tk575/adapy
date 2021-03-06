#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
#  splatsearch.py
#
#  Simple script to search Splatalogue from cli
#
#  Copyright 2012 Magnus Persson <http://vilhelm.nu>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  version 1.0b
#

"""
Script with functions to perform different actions on interferometric/SD
radio fits cubes/arrays.

Need :  o scipy (and numpy)
        o matplotlib
        o mechanize module (standard in Python >2.6/2.7?)
        o urllib2 module (standard Python module)
        o beautiful soup/xml (xml standard in Python >2.6/2.7?)

"""

"""


---[ Change log ]---


[*] 08.05.2012 Now tries to load first ClientForm and
    then Mechanise modules, both works fine.

[*] 19.03.2012
    Fixed bug causing search on upper energy level to fail
    Various un-logged changes up until now.
        - New colorify function
        - Fixed form handling after they changed the table export
          form on Splatalogue.net.

[*] 19.05.2011
    Script created
"""




#What to do

#TODO : Grab the color of the TD tag in each row. The color represents
#       a certain ALMA band, store this as well.

#TODO : Separate data handling and UI

#TODO : Solve the parsing, the removal of tags... (huh?)

#TODO : Should be able to search on specific molecules
#        - but how? molecular weight, and or just text?
#        - available in cmd version?

#IDEA : get the export-to-file directly from splatalogue?
#        - initial testing indicates that it does not work

#TODO : add so that one can enter the wavelength/wavenumber in m, cm / m-1, cm-1
#       just translate to frequency after input 
#       v = wl / c
#       wn = 1/wl -> v = 1 / (wn * c)

#TODO : figure out prettier printing of linelists... colors, web-adresses?
#        so when linelists choosen, print e.g.
#        "Line lists choosen:
#        JPL         http://jpl.nasa.gov/molecules/etc
#        CDMS        http://cologne.de/CDMS/whatever"

#TODO : Page output if it is long, i.e. input a pause and clear screen

#TODO : Control display-output more, now a broad window is needed to
#        display everything

#TODO : Change dictionary key-names in return-dictionary

#TODO : Implement new stylify help function


###########################################
# MAIN FUNCTION


def splatsearch(**arg):
    """
    This script queries Splatalogue.net from the command line

    Returns a data structure or displays the requested information
    from Splatalogue.

    Usage:
        splatsearch(**kwargs)

    Needs internet connection to work (duh!).

    Keyword arguments (kwargs)

        Frequency
          o parameter name : freq
                [f1, f2]  or f
                frequency interval to query
          o parameter name : dfreq
                if freq only f, a dfreq must be given
                center frequency (f) and bandwidth (df)
          o parameter name : funit
                possible values : 'GHz' or 'MHz'
                freqyency unit
            Note: low ranked plans to implement searching by
                  wavelength/wavenumber (m,cm,mm/m-1) exists

        Line list
          o parameter name : 'linelist'
                type : list
                a list of strings ['item1', 'item2']
                conainting the line list catalogs that you want
                to search in. Possible entries:
                ['Lovas', 'SLAIM', 'JPL', 'CDMS', 'ToyaMa',\
                            'OSU', 'Recomb', 'Lisa', 'RFI']
                or linelists = 'all' for all of them

        Energy range
          o parameter name : e_from
                type : int/float
          o parameter name : e_to
                type : int/float
          o parameter name : e_type
                type :  string
                one of ['el_cm1', 'eu_cm1', 'el_k', 'eu_k']
                unit and type, in cm-1 or K
                if not given, defaults to eu_k

        Line Intensity Lower Limit
          o parameter name : lill
                type : list
                list in the form [value, 'type']
                possible types:
                    'cdms_jpl' : CDMS/JPL Intensity given in log10
                     'Sij mu^2' : Sij mu^2 in Debye^2
                         'Aij' : Aij in log10
                example lill = [-5, 'cdms_jpl']
                for CDMS/JPL Intensity of 10^(-5)
        Transition
          o parameter name : transition
                type : string
                example transition = '1-0'

        OUTPUT

        display - Display output
        Frequency




        freq measured if exist otherwise computed

    """
    #~ arg = kwargs
    #
    if arg.has_key('display'):
        if arg['display'] == 1:
            def print_greeting():
                text_splat_colors = [stylify(i,fg='rand') for i in 'SPLATSEARCH']
                text_splat_colors = ''.join(text_splat_colors)
                print "\n    "+"*"*40
                print "    *"+" "*38+"*"
                print "    *\t           "+text_splat_colors+"             *"
                print "    *\t  Splatalogue.net search script    *"
                print "    *\t    Magnus Vilhelm Persson         *"
                print "    *\t        magnusp@nbi.dk             *"
                print "    *"+" "*38+"*"
                print "    "+"*"*40+"\n"
            if not arg.has_key('send'):
                print_greeting()
            elif arg.has_key('send') and not arg['send']:
                print_greeting()
    ### import dependencies
    try:
        from urllib2 import urlopen, URLError
    except (ImportError):
        print 'You need the module \'urllib2\''
    try:
        from ClientForm import ParseResponse
    except (ImportError):
        try:
            from mechanize import ParseResponse
        except (ImportError):
            print 'You need at least one of the two modules '
            'Mechanize or ClientForm for this script to work.'
            print '\'ClientForm\' http://wwwsearch.sourceforge.net/old/ClientForm/'
    #from BeautifulSoup import BeautifulSoup as bfs
    from scipy import array, where, arange
    #from string import lower, upper

    # get the form from the splatalogue search page
    try:
        response = urlopen("http://www.cv.nrao.edu/php/splat/b.php")
    except URLError:
        import sys
        sys.stderr.write(stylify('ERROR : ',f='b',fg='r')+stylify(' You have to be connected to the internet to access the splatalogue.net database.',f='b',fg='k'))
        return None
    forms = ParseResponse(response, backwards_compat=False)
    response.close()
    form = forms[0]

    if arg.has_key('dbg_snd_form'): # for test purposes
        return form
    ####################################################################
    ####                                                            ####
    ####                        PARSE INPUT                         ####
    ####                                                            ####
    ####################################################################
    #
    #### FREQUENCY
    #
    #
    #           No frequency given, what then?
    #           a looooot of hits returned, perhaps pause and ask if 
    #           user wants to continue??
    #
    #
    #
    if arg.has_key('freq'):
        if type(arg['freq']) == type([1,2]):
            if len(arg['freq']) == 1:
                raise ParError(arg['freq'])
            f1, f2 = arg['freq']
            form['from'] = str(f1)
            form['to'] = str(f2)
        elif type(arg['freq']) == type(1) or type(arg['freq']) == type(1.):
            if type(arg['freq']) == type(1):
                arg['freq'] = float(arg['freq'])
            if not arg.has_key('dfreq'):
                print 'Please either give a frequency interval (freq=[f1,f2])\n\
                OR a center frequency and a bandwidth (freq=f, dfreq=df)'
                raise ParError('freq='+str(arg['freq'])+' and dfreq=None')
            elif arg.has_key('dfreq'):
                f1, f2 = arg['freq']+array([-1,1])*arg['dfreq']/2.
            else:
                raise ParError(arg['dfreq'])
            form['from'] = str(f1)
            form['to'] = str(f2)
    elif not arg.has_key('freq') and arg.has_key('dfreq'):
        print 'Only delta-frequency (dfreq) given, no frequency to look for'
        raise ParError('freq=None and dfreq='+str(arg['dfreq']))
    elif not arg.has_key('freq') and not arg.has_key('dfreq') and len(arg.keys()) != 0:
        # no frequency given, but other parameters
        #tmp = str(raw_input('No frequency limits given, continue? Press Enter to continue, Ctrl+C to abort.'))
        f1 = ''
        f2 = ''
    else:
        # if no frequency is given, just run example
        # this is not visible when running from outside python
        # check "if __main__ ..." part
        print stylify('Example run... setting f1,f2 = 203.406, 203.409 GHz',fg='m')
        form['from'] = '203.406'
        form['to'] = '203.409'
    #
    #### FREQUENCY UNIT
    #
    if arg.has_key('funit'):
        if arg['funit'].lower() in ['ghz', 'mhz']:
            form['frequency_units'] = [arg['funit']]
        else:
            print 'Allowed frequency units : \'GHz\' or \'MHz\''
    elif not arg.has_key('funit'):
        arg['funit'] = 'GHz'
        form['frequency_units'] = ['GHz']
    #
    #### MOLECULAR SPECIES
    #
    #Get species molecular number, ordered by mass
    # TODO : perhaps be able to search in this one
    #        either by mass or by species, text of chem formula
    # TODO : after getting it, should sort the list of dictionaries
    #        clean it up a bit
    # get the avaliable species from the form
    #~ sel_species = [i.attrs for i in form.find_control('sid[]').items]
    #
    #### LINE LIST
    #
    # define a reference list of names
    mylinelist = ['lovas', 'slaim', 'jpl', 'cdms', 'toyama', 'osu', \
    'recomb', 'lisa', 'rfi']
    # list of strings with the format that the search form wants
    formcontrol_linelist = ["displayLovas", "displaySLAIM", \
    "displayJPL", "displayCDMS", "displayToyaMA", "displayOSU", \
    "displayRecomb", "displayLisa", "displayRFI"]
    if arg.has_key('linelist'):
        if type(arg['linelist'])==type('string'):
            # if linelist is given as linelist='all'
            if arg['linelist'].lower() == 'all':
                # if we want to set all, just copy mylinelist
                arg['linelist'] = mylinelist
            else:
                print 'Linelist input not understood'
                raise ParError(arg['linelist'])
        elif type(arg['linelist'])==type(['list']):
            # get all values to lower case, to accept capitals
            arg['linelist'] = [x.lower() for x in arg['linelist']]
        else:
            print 'Linelist input not understood'
            raise ParError(arg['linelist'])
    else:
        # if none given, search with all
        arg['linelist'] = mylinelist

    # now set the linelist search form
    # check for every linelist, if it exists in the input linelist
    for i,j in zip(mylinelist, formcontrol_linelist):
        if i in arg['linelist']:
            form.find_control(j).get().selected = True
        else:
            form.find_control(j).get().selected = False
    # ['Lovas', 'SLAIM', 'JPL', 'CDMS', 'ToyaMA', 'OSU', \
    #'Recomb', 'Lisa', 'RFI']
    # Figure out prettier printing here...
    #    web-adresses?
    #
    ### Energy Range
    #
    # form['energy_range_from/to'] is a text field in the form
    # while it is called e_from/to in the function
    #
    if arg.has_key('e_from') or arg.has_key('e_to'):
        e_type_ref = ['el_cm1', 'eu_cm1', 'el_k', 'eu_k']
        # check that unit is given, and correct
        # or set default (eu_k)

        if arg.has_key('e_from'):
            form['energy_range_from'] = str(arg['e_from'])
        if arg.has_key('e_to'):
            form['energy_range_to'] = str(arg['e_to'])
        if arg.has_key('e_from') or arg.has_key('e_to'):
            if arg.has_key('e_type'):
                if arg['e_type'].lower() in e_type_ref:
                    pass
                else:
                    print 'Energy range type keyword \'e_type\' malformed.'
                    raise ParError(arg['e_type'])
                e_type_default = 0
            else:
                e_type_default = 1
                arg['e_type'] = 'eu_k'
            # now set the radio button to the correct value
            form.find_control('energy_range_type').toggle(arg['e_type'].lower())
        if not arg.has_key('e_from') and not arg.has_key('e_to') and arg.has_key('e_type'):
            print 'You gave the Enery range type keyword, but no energy range...'
            raise ParError(arg['e_type'])
    #
    ### Specify Transition
    #
    if arg.has_key('transition'):
        form['tran'] = str(arg['transition'])
    #
    ### Line Intensity Lower Limits
    if arg.has_key('lill'):
        if arg['lill'][1].lower() == 'cdms_jpl':
            form.find_control('lill_cdms_jpl').disabled = False
            form['lill_cdms_jpl'] = str(arg['lill'][0])
        elif arg['lill'][1].lower() == 'sijmu2':
            form.find_control('lill_sijmu2').disabled = False
            form['lill_sijmu2'] = str(arg['lill'][0])
        elif arg['lill'][1].lower() == 'aij':
            form.find_control('lill_aij').disabled = False
            form['lill_aij'] = str(arg['lill'][0])
    #
    ### FREQUENCY ERROR LIMIT
    #

    #### Line Strength Display
    form.find_control("ls1").get().selected = True
    form.find_control("ls2").get().selected = True
    form.find_control("ls3").get().selected = True
    form.find_control("ls4").get().selected = True
    form.find_control("ls5").get().selected = True
    #### Energy Levels
    form.find_control("el1").get().selected = True
    form.find_control("el2").get().selected = True
    form.find_control("el3").get().selected = True
    form.find_control("el4").get().selected = True
    #### Miscellaneous
    form.find_control("show_unres_qn").get().selected = True
    form.find_control("show_upper_degeneracy").get().selected = True
    form.find_control("show_molecule_tag").get().selected = True
    form.find_control("show_qn_code").get().selected = True

    ####################################################################
    ####                                                            ####
    ####               DISPLAY SEARCH PARAMETERS                    ####
    ####                                                            ####
    ####################################################################
    print stylify('** SEARCH PARAMETERS **',fg='b')
    if arg.has_key('freq'):
        print stylify('Frequency range :',fg='g')+' '+str(f1)+' - '+str(f2)
        print stylify('Frequency unit \t:',fg='g')+' '+arg['funit']
    else:
        print 'No frequency range specified'
    print stylify('Line list(s) \t:',fg='g')+' '+', '.join(arg['linelist'])
    if arg.has_key('e_from') or arg.has_key('e_to'):
        if arg.has_key('e_from') and not arg.has_key('e_to'):
            print stylify('Energy range \t:',fg='g')+'from '+str(arg['e_from'])+'( Type : %s)' % str([arg['e_type'],'def (EU(K))'][e_type_default])
        elif not arg.has_key('e_from') and arg.has_key('e_to'):
            print stylify('Energy range \t:',fg='g')+'to '+str(arg['e_to'])+'( Type : %s)' % str([arg['e_type'],'def (EU(K))'][e_type_default])
        else:
            #print stylify('Energy range \t:',fg='g')+upper(arg['e_type'][:2])+' from '+str(arg['e_from'])+' to '+str(arg['e_to'])+' 'upper(arg['e_type'][3:])+'( Type : %s)' % str([arg['e_type'],'yes'][e_type_default])
            print (
            stylify('Energy range \t:',fg='g')+
            ' {0} from {1} to {2} {3} (Type : {4})'.format(
                    arg['e_type'][:2].upper(),
                    str(arg['e_from']),
                    str(arg['e_to']),
                    arg['e_type'][3:].upper(),
                    str([arg['e_type'], 'yes'][e_type_default])))
    if arg.has_key('lill'):
        if arg['lill'][1].lower() == 'cdms_jpl':
            print stylify('Line lower lim \t:',fg='g')+' 1E('+str(arg['lill'][0])+') - CDMS/JPL Intensity'
        elif arg['lill'][1].lower() == 'sijmu2':
            print stylify('Line lower lim \t:',fg='g')+' '+str(arg['lill'][0])+' Debye^2 - Sijmu^2'
        elif arg['lill'][1].lower() == 'aij':
            print stylify('Line lower lim \t:',fg='g')+' 1E('+str(arg['lill'][0])+') - Aij'
    if arg.has_key('transition'):
        print stylify('Transition \t:',fg='g')+' '+arg['transition']
    #~ if arg.has_key(''):
    print ''

    ####################################################################
    ####                                                            ####
    ####                        GET RESULTS                         ####
    ####                                                            ####
    ####################################################################
    # 'click' the form
    # need to click the form first
    clicked_form = form.click()
    # then get the results page
    result = urlopen(clicked_form)

    #### EXPORTING RESULTS FILE
    # so what I do is that I fetch the first results page,
    # click the form/link to get all hits as a colon separated
    # ascii table file
    #
    # get the form
    resultform = ParseResponse(result, backwards_compat=False)
    result.close()
    resultform = resultform[0]
    # set colon as dilimeter of the table (could use anything I guess)
    #~ resultform.find_control('export_delimiter').items[1].selected =  True
    resultform.find_control('export_delimiter').toggle('colon')
    resultform_clicked = resultform.click()
    result_table = urlopen(resultform_clicked)
    data = result_table.read()
    result_table.close()
    ####################################################################
    ####                                                            ####
    ####                        PARSE RESULT                        ####
    ####                                                            ####
    ####################################################################
    # get each line (i.e. each molecule)
    lines = data.split('\n')
    # get the names of the columns
    column_names = lines[0]
    lines = lines[1:-1]
    column_names = column_names.split(':')
    hits = len(lines)
    if hits == 0:
        print '\nNo lines found!'
        return None
    lines = [i.split(':') for i in lines]
    #return column_names
    species, name, cfreq, cfreqerr, mfreq, mfreqerr, res_qns, ures_qns, cdmsjpl_I, \
    Smu2, Sij, log10Aij, lovasAST_I, ELcm, ELK, EUcm, EUK, u_degen, \
    mol_tag, QNr, llist = array(lines).transpose()
    # parse the columns
    # first change empty values to Nan
    cfreq[where(cfreq == '')] = 'nan'
    cfreqerr[where(cfreqerr == '')] = 'nan'
    mfreq[where(mfreq == '')] = 'nan'
    mfreqerr[where(mfreqerr == '')] = 'nan'
    # create arrays
    cfreqerr = array(cfreqerr, dtype='float')
    cfreq = array(cfreq, dtype='float')
    mfreqerr = array(mfreqerr, dtype='float')
    mfreq = array(mfreq, dtype='float')
    # create global frequency array, and a
    # array telling if it is measured or computed
    # empty arrays
    from scipy import zeros
    freq = zeros(cfreq.shape)
    freqerr  = zeros(cfreqerr.shape)
    freqtype = []
    # use measured frequency if exists
    # otherwise use computed
    for i in arange(hits):
        if str(mfreq[i]) == 'nan':
            freq[i] = cfreq[i]
            freqerr[i] = cfreqerr[i]
            freqtype.append('C')
        else:
            freq[i] = mfreq[i]
            freqerr[i] = mfreqerr[i]
            freqtype.append('M')
    N = arange(hits)+1
    ####################################################################
    ####                                                            ####
    ####                     DISPLAY RESULTS                        ####
    ####                                                            ####
    ####################################################################
    if arg.has_key('display') and arg['display']:
        print stylify('** RESULTS **',fg='b')
        print 'Got %s hits!' % stylify(str(hits),fg='r')
        print stylify('{0:2} {1:15} {2:23}\t{3:10}\t{4:9}\t{5:10}\t{6:3}\t{7:6}',fg='m').format('N', 'Form', \
        'Res Qnr','Freq', 'Smu^2', 'EU(K)','C/M', 'List')
        for i in arange(hits):
            if i%2:
                print '{0:2} {1:15} {2:26}\t{3:10}\t{4:9}\t{5:10}\t{6:3}\t{7:6} '.format(N[i], \
                species[i], res_qns[i], freq[i], Smu2[i], EUK[i], freqtype[i], llist[i])
            else:
                print stylify('{0:2} {1:15} {2:23}\t{3:10}\t{4:9}\t{5:10}\t{6:3}\t{7:6} '.format(N[i], \
                species[i], res_qns[i], freq[i], Smu2[i], EUK[i], freqtype[i], llist[i]), bg='a', fg='r')
    if arg.has_key('send'):
        if arg['send']=='dict':
            # TODO : change the output dictionary keys, a bit complicated now
            return {'N': N, 'Chem. Species': species, 'Chem. Name': name, \
            'Comp. Freq': cfreq,'Comp.Freq Err': cfreqerr, \
            'Meas. Freq': mfreq, 'Meas.Freq Err': mfreqerr,  \
            'Freq': freq, 'Freq Err': freqerr,  \
            'FreqType': freqtype, \
            'Res. QNr': res_qns,  'URes. QNr': ures_qns, \
            'CDMS/JPL I': cdmsjpl_I, 'Smu2': Smu2, 'Sij': Sij, \
            'log10Aij': log10Aij, 'Lovas/AST I': lovasAST_I, \
            'EL (cm-1)': ELcm, 'EL (K)': ELK, 'EU (cm-1)': EUcm, \
            'EU (K)': EUK, 'Upper Degeneracy': u_degen, \
            'Molecular Tag': mol_tag, 'Quantum Nr': QNr, \
            'Line List': llist}
        if arg['send'] == 'list' or arg['send']:
            if arg.has_key('silent'):
                if not arg['silent']:
                    print 'Sending:\n\
             Number\n Chemical Species\n Chemical Name\n Computed Frequency\n Computed Frequency Error\n\
             Measured Frequency\n Measured Frequency Error\n Resolved Quantum Numbers\n Uresolved Quantum Numbers\n\
             CDMS/JPL Intensity\n Smu**2\n Sij\n log10(Aij)\n Lovas/AST Intensity'
                elif arg['silent']:
                    pass
            return N, species, name, freq, freqerr, freqtype, cfreq, cfreqerr, mfreq, mfreqerr, res_qns, ures_qns, cdmsjpl_I, \
            Smu2, Sij, log10Aij, lovasAST_I, ELcm, ELK, EUcm, EUK, u_degen, \
            mol_tag, QNr, llist
    else:
        pass

def get_mol_species():
    """Function to get the molecular species...
    only started...
    Best to take the list/dictionary as input (more like a matching function)?
    Should return a structure compilant with the form input
    """


###########################################
# ERROR CLASSES


class ParError(Exception):
    # input parameter error
    def __init__(self, value):
        """ Parameter Error Class
        Takes the wrong parameter as input.
        """
        self.value = value
    def __str__(self):
        """ Prints a message and the wrong parameter with value """
        s1 = '\nWrong format/number of parameters. You input:\n    '
        s2 = '\nas parameters. Check it/them.'
        return s1+str(self.value)+s2
#
###########################################
# HELP FUNCTIONS
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
             "rand" random
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


    Changelog :

    *2011/10/24 added fg = "rand" for random foreground color

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

    if fg=="rand":
        from random import randint
        c_tmp = ["k","r","g","y","b","m","c","a","d"]
        fg = c_tmp[randint(0,len(c_tmp)-1)]
    #
    try:
        style = [format_and_colors[f.lower()],
                format_and_colors[fg.lower()],
                format_and_colors[bg.lower()]]
        style = [str(x) for x in style]
        formatted_text = CSI+';'.join(style)+'m'
        formatted_text += s + end
    except KeyError:
        raise ParError((f,fg,bg))

    return formatted_text
