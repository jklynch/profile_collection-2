import bluesky as bs
import bluesky.plans as bp
import bluesky.plan_stubs as bps
import numpy
import os
import re
import subprocess

run_report(__file__)

# p = scan_metadata(inifile='/home/bravel/commissioning/scan.ini', filename='humbleblat.flarg', start=10)
# (energy_grid, time_grid, approx_time) = conventional_grid(p['bounds'],p['steps'],p['times'],e0=p['e0'])
# then call bmm_metadata() to get metadata in an XDI-ready format

CS_BOUNDS     = [-200, -30, 15.3, '14k']
CS_STEPS      = [10, 0.5, '0.05k']
CS_TIMES      = [0.5, 0.5, '0.25k']
CS_MULTIPLIER = 1.425
CS_DEFAULTS   = {'bounds':        [-200, -30, 15.3, '14k'],
                 'steps':         [10, 0.5, '0.05k'],
                 'times':         [0.5, 0.5, '0.25k'],

                 'folder':        os.environ.get('HOME')+'/data/',
                 'filename':      'data.dat',
                 'experimenters': '',
                 'e0':            7112,
                 'element':       'Fe',
                 'edge':          'K',
                 'sample':        '',
                 'prep':          '',
                 'comment':       '',
                 'nscans':        1,
                 'start':         0,
                 'inttime':       1,
                 'snapshots':     True,
                 'htmlpage':      True,
                 'bothways':      False,
                 'channelcut':    True,
                 'mode':          'transmission',

                 'npoints':       0,
                 'dwell':         1.0,
                 'delay':         0.1}


#import inspect
import configparser
    #folder=None, filename=None,
    #e0=None, element=None, edge=None, sample=None, prep=None, comment=None,
    #nscans=None, start=None, inttime=None,
    #snapshots=None, bothways=None, channelcut=None, focus=None, hr=None,
    #mode=None, bounds=None, steps=None, times=None):

def next_index(folder, stub):
    listing = os.listdir(folder)
    r = re.compile(stub + '\.\d\d\d')
    results = sorted(list(filter(r.match, listing)))
    if len(results) == 0:
        return 1
    return int(results[-1][-3:]) + 1


def scan_metadata(inifile=None, **kwargs):
    """Typical use is to specify an INI file, which contains all the
    metadata relevant to a set of scans.  This function is called with
    one argument:

      parameters = scan_metadata(inifile='/path/to/inifile')

      inifile:  fully resolved path to INI file describing the measurement.

    A dictionary of metadata is returned.

    As part of a multi-scan plan (i.e. a macro), individual metadata
    can be specified as kwargs to override values in the INI file.
    The kwarg keys are the same as the keys in the dictionary which is
    returned:

      folder:       [str]   folder for saved XDI files
      filename:     [str]   filename stub for saved XDI files
      experimenters [str]   names of people involved in this measurements
      e0:           [float] edge energy, reference value for energy grid
      element:      [str]   one- or two-letter element symbol
      edge:         [str]   K, L3, L2, or L1
      sample:       [str]   description of sample, perhaps stoichiometry
      prep:         [str]   a short statement about sample preparation
      comment:      [str]   user-supplied comment about the data
      nscan:        [int]   number of repetitions
      start:        [int]   starting scan number, XDI file will be filename.###
      snapshots:    [bool]  True = capture analog and XAS cameras before scan sequence
      htmlpage:     [bool]  True = capture dossier of a scan sequence as a static html page
      bothways:     [bool]  True = measure in both monochromator directions
      channelcut:   [bool]  True = measure in pseudo-channel-cut mode
      mode:         [str]   transmission, fluorescence, or reference -- how to display the data
      bounds:       [list]  scan grid boundaries (not kwarg-able at this time)
      steps:        [list]  scan grid step sizes (not kwarg-able at this time)
      times:        [list]  scan grid dwell times (not kwarg-able at this time)

    Any or all of these can be specified.  Values from the INI file
    are read first, then overridden with specified values.  If values
    are specified neither in the INI file nor in the function call,
    (possibly) sensible defaults are used.

    """
    #frame = inspect.currentframe()          # see https://stackoverflow.com/a/582206 and
    #args  = inspect.getargvalues(frame)[3]  # https://docs.python.org/3/library/inspect.html#inspect.getargvalues

    parameters = dict()

    if inifile is None:
        print(colored('\nNo inifile specified\n', 'lightred'))
        return {}, {}
    if not os.path.isfile(inifile):
        print(colored('\ninifile does not exist\n', 'lightred'))
        return {}, {}

    config = configparser.ConfigParser(interpolation=None)
    config.read_file(open(inifile))

    found = dict()

    ## ----- scan regions
    for a in ('bounds', 'steps', 'times'):
        found[a] = False
        if a not in kwargs:
            parameters[a] = []
            try:
                for f in config.get('scan', a).split():
                    try:
                        parameters[a].append(float(f))
                    except:
                        parameters[a].append(f)
                    found[a] = True
            except:
                parameters[a] = CS_DEFAULTS[a]
    parameters['bounds_given'] = parameters['bounds'].copy()

    ## ----- strings
    for a in ('folder', 'experimenters', 'element', 'edge', 'filename', 'comment',
              'mode', 'sample', 'prep'):
        found[a] = False
        if a not in kwargs:
            try:
                parameters[a] = config.get('scan', a)
                found[a] = True
            except configparser.NoOptionError:
                parameters[a] = CS_DEFAULTS[a]
        else:
            parameters[a] = str(kwargs[a])
            found[a] = True

    if not os.path.isdir(parameters['folder']):
        print(colored('\nfolder %s does not exist\n' % parameters['folder'], 'lightred'))
        return {}, {}

            
    ## ----- start value
    if 'start' not in kwargs:
        try:
            parameters['start'] = str(config.get('scan', 'start'))
            found['start'] = True
        except configparser.NoOptionError:
            parameters['start'] = CS_DEFAULTS['start']
    else:
        parameters['start'] = str(kwargs['start'])
        found['start'] = True
    try:
        if parameters['start'] == 'next':
            parameters['start'] = next_index(parameters['folder'],parameters['filename'])
        else:
            parameters['start'] = int(parameters['start'])
    except ValueError:
        print(colored('\nstart value must be a positive integer or "next"', 'lightred'))
        parameters['start'] = -1
        found['start'] = False

    ## ----- integers
    for a in ('nscans', 'npoints'):
        found[a] = False
        if a not in kwargs:
            try:
                parameters[a] = int(config.get('scan', a))
                found[a] = True
            except configparser.NoOptionError:
                parameters[a] = CS_DEFAULTS[a]
        else:
            parameters[a] = int(kwargs[a])
            found[a] = True

    ## ----- floats
    for a in ('e0', 'inttime', 'dwell', 'delay'):
        found[a] = False
        if a not in kwargs:
            try:
                parameters[a] = float(config.get('scan', a))
                found[a] = True
            except configparser.NoOptionError:
                parameters[a] = CS_DEFAULTS[a]
        else:
            parameters[a] = float(kwargs[a])
            found[a] = True

    ## ----- booleans
    for a in ('snapshots', 'htmlpage', 'bothways', 'channelcut'):
        found[a] = False
        if a not in kwargs:
            try:
                parameters[a] = config.getboolean('scan', a)
                found[a] = True
            except configparser.NoOptionError:
                parameters[a] = CS_DEFAULTS[a]
        else:
            parameters[a] = bool(kwargs[a])
            found[a] = True

    return parameters, found


## need more error checking:
##   * sanitize the '#.#k' strings
##   * check that bounds are float or float+'k'
##   * negative boundaries must be floats
##   * steps cannot be negative
##   * times cannot be negative
##   * steps smaller than, say, '0.01k'
##   * steps smaller than 0.01
##   * k^2 times
##   * switch back to energy units afetr a k-valued boundary?
##   * out of order boundaries -- sort?
def conventional_grid(bounds=CS_BOUNDS, steps=CS_STEPS, times=CS_TIMES, e0=7112):
    '''Input:
       bounds:   (list) N relative energy values denoting the region boundaries of the step scan
       steps:    (list) N-1 energy step sizes
       times:    (list) N-1 integration time values
       e0:       (float) edge energy, reference for boundary values
    Output:
       grid:     (list) absolute energy values
       timegrid: (list) integration times
       approximate_time: (float) a very crude estimate of how long in minutes the scan will take

    Boundary values are either in eV units or wavenumber units.
    Values in eV units are floats, wavenumber units are strings of the
    form '0.5k' or '1k'.  String valued boundaries indicate a value to
    be converted from wavenumber to energy.  E.g. '14k' will be
    converted to 746.75 eV, i.e. that much above the edge energy.

    Step values are either in eV units (floats) or wavenumber units
    (strings).  Again, wavenumber values will be converted to energy
    steps as appropriate.  For example, '0.05k' will be converted into
    energy steps such that the steps are constant 0.05 invAng in
    wavenumber.

    Time values are either in units of seconds (floats) or strings.
    If strings, the integration time will be a multiple of the
    wavenumber value of the energy point.  For example, '0.5k' says to
    integrate for a number of seconds equal to half the wavenumber.
    So at 5 invAng, integrate for 2.5 seconds.  At 10 invAng,
    integrate for 5 seconds.

    Examples:
       -- this is the default (same as (g,it,at) = conventional_grid()):
       (grid, inttime, time) = conventional_grid(bounds=[-200, -30, 15.3, '14k'],
                                                 steps=[10, 0.5, '0.05k'],
                                                 times=[0.5, 0.5, '0.25k'], e0=7112)

       -- more regions
       (grid, inttime, time) = conventional_grid(bounds=[-200.0, -20.0, 30.0, '5k', '14.5k'],
                                                 steps=[10.0, 0.5, 2, '0.05k'],
                                                 times=[1, 1, 1, '1k'], e0=7112)

       -- many regions, energy boundaries, k-steps
       (grid, inttime, time) = conventional_grid(bounds=[-200, -30, -10, 15, 100, 300, 500, 700, 900],
                                                 steps=[10, 2, 0.5, '0.05k', '0.05k', '0.05k', '0.05k', '0.05k'],
                                                 times=[0.5, 0.5, 0.5, 1, 2, 3, 4, 5], e0=7112)

       -- a one-region xanes scan
       (grid, inttime, time) = conventional_grid(bounds=[-10, 40],
                                                 steps=[0.25,],
                                                 times=[0.5,], e0=7112)
    '''
    if (len(bounds) - len(steps)) != 1:
        return (None, None, None)
    if (len(bounds) - len(times)) != 1:
        return (None, None, None)
    for i,s in enumerate(bounds):
        if type(s) is str:
            this = float(s[:-1])
            bounds[i] = ktoe(this)

    grid = list()
    timegrid = list()
    for i,s in enumerate(steps):
        if type(s) is str:
            step = float(s[:-1])
            ar = e0 + ktoe(numpy.arange(etok(bounds[i]), etok(bounds[i+1]), step))
        else:
            ar = numpy.arange(e0+bounds[i], e0+bounds[i+1], steps[i])
        grid = grid + list(ar)
        grid = list(numpy.round(grid, decimals=2))
        if type(times[i]) is str:
            tar = etok(ar-e0)*float(times[i][:-1])
        else:
            tar = times[i]*numpy.ones(len(ar))
        timegrid = timegrid + list(tar)
        timegrid = list(numpy.round(timegrid, decimals=2))
    approximate_time = (sum(timegrid) + float(len(timegrid))*CS_MULTIPLIER) / 60.0
    return (grid, timegrid, round(approximate_time, 1))

## vor.count_mode.put(0)               put the Struck in OneCount mode (1 is AutoCount)
## vor.preset_time.put(0.5)            set the OneCount accumulation time
## vor.auto_count_time.put(0.5)        set the AutoCount accumulation time
## vor.count.put(1)                    trigger a OneCount
## ... then can get the channel values

## quadem1.acquire_mode.put(0)                Continuous acquire mode
## quadem1.acquire_mode.put(1)                Multiple acquire mode
## quadem1.acquire_mode.put(2)                Single acquire mode
## quadem1.acquire.put(1)                     trigger acquisition in any of the modes
## ... then can get the channel values

## -----------------------
##  energy step scan plan concept
##  1. collect metadata from an INI file
##  2. compute scan grid
##  3. move to center of angular range
##  4. drop into pseudo channel cut mode
##  5. set OneCount and Single modes on the detectors
##  6. begin scan repititions, for each one
##     a. scan:
##          i. make metadata dict, set md argument in call to scan plan
##         ii. move
##        iii. set acquisition time for this point
##         iv. trigger
##          v. collect
##     b. grab dataframe from Mongo
##        http://nsls-ii.github.io/bluesky/tutorial.html#aside-access-saved-data
##     c. write XDI file
##  8. return to fixed exit mode
##  9. return detectors to AutoCount and Continuous modes


def channelcut_energy(e0, bounds):
    for i,s in enumerate(bounds):
        if type(s) is str:
            this = float(s[:-1])
            bounds[i] = ktoe(this)
    amin = dcm.e2a(e0+bounds[0])
    amax = dcm.e2a(e0+bounds[-1])
    aave = amin + 1.0*(amax - amin) / 2.0
    wavelength = dcm.wavelength(aave)
    eave = e2l(wavelength)
    return eave


def ini_sanity(found):
    ok = True
    missing = []
    for a in ('bounds', 'steps', 'times', 'e0', 'element', 'edge', 'folder', 'filename', 'nscans', 'start'):
        if found[a] is False:
            ok = False
            missing.append(a)
    return (ok, missing)



##########################################################
# --- export a database energy scan entry to an XDI file #
##########################################################
def db2xdi(datafile, key):
    '''
    Export a database entry for an XAFS scan to an XDI file.

       db2xdi('/path/to/myfile.xdi', 1533)

    or

       db2xdi('/path/to/myfile.xdi', '0783ac3a-658b-44b0-bba5-ed4e0c4e7216')

    The arguments are th resolved path to the output XDI file and
    a database key.
    '''
    if os.path.isfile(datafile):
        print(colored('%s already exists!  Bailing out....' % datafile, 'lightred'))
        return
    header = db[key]
    ## sanity check, make sure that db returned a header AND that the header was an xafs scan
    write_XDI(datafile, header, header.start['XDI,_mode'][0], header.start['XDI,_comment'][0])
    print(colored('wrote %s' % datafile, 'white'))

from pygments import highlight
from pygments.lexers import PythonLexer, IniLexer
from pygments.formatters import HtmlFormatter

def scan_sequence_static_html(inifile       = None,
                              filename      = None,
                              start         = None,
                              end           = None,
                              experimenters = None,
                              seqstart      = None,
                              seqend        = None,
                              e0            = None,
                              edge          = None,
                              element       = None,
                              scanlist      = None,
                              motors        = None,
                              sample        = None,
                              prep          = None,
                              comment       = None,
                              mode          = None,
                              pccenergy     = None,
                              bounds        = None,
                              steps         = None,
                              times         = None,
                              clargs        = '',
                              websnap       = '',
                              anasnap       = '',
                              ):
    '''
    Gather information from various places, including html_dict, a temporary dictionary 
    filled up during an XAFS scan, then write a static html file as a dossier for a scan
    sequence using a bespoke html template file
    '''
    if filename is None or start is None:
        return None
    firstfile = "%s.%3.3d" % (filename, start)
    if not os.path.isfile(os.path.join(DATA, firstfile)):
        return None
    
    with open(os.path.join(DATA, 'dossier', 'sample.tmpl')) as f:
        content = f.readlines()
    basename     = filename
    htmlfilename = os.path.join(DATA, 'dossier/',   filename+'-01.html')
    seqnumber = 1
    if os.path.isfile(htmlfilename):
        seqnumber = 2
        while os.path.isfile(os.path.join(DATA, 'dossier', "%s-%2.2d.html" % (filename,seqnumber))):
            seqnumber += 1
        basename     = "%s-%2.2d" % (filename,seqnumber)
        htmlfilename = os.path.join(DATA, 'dossier', "%s-%2.2d.html" % (filename,seqnumber))


    ## write out the project file & crude processing image for this batch of scans
    save = ''
    try:
        save = os.environ['DEMETER_FORCE_IFEFFIT']
    except:
        save = ''
    if save is None: save = ''
    os.environ['DEMETER_FORCE_IFEFFIT'] = '1'
    try:
        ##########################################################################################
        # Hi Tom!  Yes, I am making a system call right here.  Again.  And to run a perl script, #
        # no less!  Are you having an aneurysm?  If so, please get someone to film it.  I'm      #
        # going to want to see that!  XOXO, Bruce                                                #
        ##########################################################################################
        result = subprocess.run(['toprj.pl',
                                 "--folder=%s" % DATA,
                                 "--name=%s"   % filename,
                                 "--base=%s"   % basename,
                                 "--start=%d"  % int(start),
                                 "--end=%d"    % int(end),
                                 "--bounds=%s" % bounds,
                                 "--mode=%s"   % mode        ], stdout=subprocess.PIPE)
        png = open(os.path.join(DATA, 'snapshots', basename+'.png'), 'wb')
        png.write(result.stdout)
        png.close()
    except:
        pass
    os.environ['DEMETER_FORCE_IFEFFIT'] = save
    
    with open(os.path.join(DATA, inifile)) as f:
        initext = ''.join(f.readlines())
        
    o = open(htmlfilename, 'w')
    pdstext = '%s (%s)' % (get_mode(), describe_mode())
    o.write(''.join(content).format(filename      = filename,
                                    basename      = basename,
                                    experimenters = experimenters,
                                    gup           = BMM_xsp.gup,
                                    saf           = BMM_xsp.saf,
                                    seqnumber     = seqnumber,
                                    seqstart      = seqstart,
                                    seqend        = seqend,
                                    mono          = 'Si(%s)' % dcm._crystal,
                                    pdsmode       = pdstext,
                                    e0            = '%.1f' % e0,
                                    edge          = edge,
                                    element       = element,
                                    date          = BMM_xsp.date,
                                    scanlist      = scanlist,
                                    motors        = motors,
                                    sample        = sample,
                                    prep          = prep,
                                    comment       = comment,
                                    mode          = mode,
                                    pccenergy     = '%.1f' % pccenergy,
                                    bounds        = bounds,
                                    steps         = steps,
                                    times         = times,
                                    clargs        = highlight(clargs, PythonLexer(), HtmlFormatter()),
                                    websnap       = '../snapshots/'+websnap,
                                    anasnap       = '../snapshots/'+anasnap,
                                    initext       = highlight(initext, IniLexer(), HtmlFormatter()),
                                ))
    o.close()

    manifest = open(os.path.join(DATA, 'dossier', 'MANIFEST'), 'a')
    manifest.write(htmlfilename + '\n')
    manifest.close()

    write_manifest()
    return(htmlfilename)


import bluesky.preprocessors
from bluesky.preprocessors import subs_decorator
import pprint
pp = pprint.PrettyPrinter(indent=4)


def write_manifest():
    with open(os.path.join(DATA, 'dossier', 'MANIFEST')) as f:
        lines = [line.rstrip('\n') for line in f]

    experimentlist = ''
    for l in lines:
        if not os.path.isfile(l):
            continue
        experimentlist += '<li><a href="%s">%s</a></li>\n' % (l, os.path.basename(l))
        
    with open(os.path.join(DATA, 'dossier', 'manifest.tmpl')) as f:
        content = f.readlines()
    indexfile = os.path.join(DATA, 'dossier', '00INDEX.html')
    o = open(indexfile, 'w')
    o.write(''.join(content).format(date           = BMM_xsp.date,
                                    experimentlist = experimentlist,
                                ))
    o.close()
    


#########################
# -- the main XAFS scan #
#########################
def xafs(inifile, **kwargs):
    '''
    Read an INI file for scan matadata, then perform an XAFS scan sequence.
    '''
    def main_plan(inifile, **kwargs):
        if '311' in dcm._crystal and dcm_x.user_readback.value < 0:
            BMM_xsp.final_log_entry = False
            print(colored('The DCM is in the 111 position, configured as 311', 'lightred'))
            print(colored('\tdcm.x: %.2f mm\t dcm._crystal: %s' % (dcm_x.user_readback.value, dcm._crystal), 'lightred'))
            yield from null()
            return
        if '111' in dcm._crystal and dcm_x.user_readback.value > 0:
            BMM_xsp.final_log_entry = False
            print(colored('The DCM is in the 311 position, configured as 111', 'lightred'))
            print(colored('\tdcm_x: %.2f mm\t dcm._crystal: %s' % (dcm_x.user_readback.value, dcm._crystal), 'lightred'))
            yield from null()
            return

        
        verbose = False
        if 'verbose' in kwargs and kwargs['verbose'] is True:
            verbose = True
            
        supplied_metadata = dict()
        if 'md' in kwargs and type(kwargs['md']) == dict:
            supplied_metadata = kwargs['md']

        if verbose: print(colored('checking clear to start (unless force=True)', 'lightcyan')) 
        if 'force' in kwargs and kwargs['force'] is True:
            (ok, text) = (True, '')
        else:
            (ok, text) = BMM_clear_to_start()
            if ok is False:
                BMM_xsp.final_log_entry = False
                print(colored('\n'+text, 'lightred'))
                print(colored('Quitting scan sequence....\n', 'white'))
                yield from null()
                return

        ## make sure we are ready to scan
        #yield from abs_set(_locked_dwell_time.quadem_dwell_time.settle_time, 0)
        #yield from abs_set(_locked_dwell_time.struck_dwell_time.settle_time, 0)
        _locked_dwell_time.quadem_dwell_time.settle_time = 0
        _locked_dwell_time.struck_dwell_time.settle_time = 0


        ## --*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--
        ## user input, find and parse the INI file
        if verbose: print(colored('time estimate', 'lightcyan')) 
        inifile, estimate = howlong(inifile, interactive=False, **kwargs)
        if estimate == -1:
            BMM_xsp.final_log_entry = False
            yield from null()
            return
        (p, f) = scan_metadata(inifile=inifile, **kwargs)
        if not any(p):          # scan_metadata returned having printed an error message
            return(yield from null())

        bad_characters = re.search('[*:"<>|/+\\\]', p['filename'])
        if bad_characters is not None:
            BMM_xsp.final_log_entry = False
            print(colored('\nA filename should contain any of these characters:', 'lightred'))
            print(colored('\n\t* : " < > | / + \\', 'lightred'))
            print(colored('\nFilenames with those characters cannot be copied onto most memory sticks', 'lightred'))
            yield from null()
            return

        if len(p['filename']) > 250:
            BMM_xsp.final_log_entry = False
            print(colored('\nYour filename is too long,', 'lightred'))
            print(colored('\nFilenames longer than 255 characters cannot be copied onto most memory sticks,', 'lightred'))
            yield from null()
            return
        
        ## --*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--
        ## user verification (disabled by BMM_xsp.prompt)
        if verbose: print(colored('computing pseudo-channelcut energy', 'lightcyan')) 
        eave = channelcut_energy(p['e0'], p['bounds'])
        length = 0
        if BMM_xsp.prompt:
            text = '\n'
            for k in ('bounds', 'bounds_given', 'steps', 'times'):
                addition = '      %-13s : %-50s\n' % (k,p[k])
                text = text + addition
                if len(addition) > length: length = len(addition)
            for (k,v) in p.items():
                if k in ('bounds', 'bounds_given', 'steps', 'times'):
                    continue
                if k in ('npoints', 'dwell', 'delay', 'inttime', 'channelcut', 'bothways'):
                    continue
                addition = '      %-13s : %-50s\n' % (k,v)
                text = text + addition
                if len(addition) > length: length = len(addition)
            boxedtext('How does this look?', text, 'green', width=length+4) # see 05-functions

            outfile = os.path.join(p['folder'], "%s.%3.3d" % (p['filename'], p['start']))
            print('\nFirst data file to be written to "%s"' % outfile)

            bail = False
            count = 0
            for i in range(p['start'], p['start']+p['nscans'], 1):
                count += 1
                fname = "%s.%3.3d" % (p['filename'], i)
                datafile = os.path.join(p['folder'], fname)
                if os.path.isfile(datafile):
                    print(colored('%s already exists!' % datafile, 'lightred'))
                    bail = True
            if bail:
                print(colored('\nOne or more output files already exist!  Quitting scan sequence....', 'lightred'))
                BMM_xsp.final_log_entry = False
                yield from null()
                return
            print(estimate)

            if not dcm.suppress_channel_cut:
                print('\nPseudo-channel-cut energy = %.1f' % eave)
            action = input("\nBegin scan sequence? [Y/n then Enter] ")
            if action.lower() == 'q' or action.lower() == 'n':
                BMM_xsp.final_log_entry = False
                yield from null()
                return

        with open(inifile, 'r') as fd: content = fd.read()
        output = re.sub(r'\n+', '\n', re.sub(r'\#.*\n', '\n', content)) # remove comment and blank lines
        clargs = str(kwargs)
        BMM_log_info('starting XAFS scan using %s:\n%s\ncommand line arguments = %s' % (inifile, output, str(kwargs)))
        BMM_log_info(motor_status())

        ## --*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--
        ## set up a plotting subscription, anonymous functions for plotting various forms of XAFS
        trans = lambda doc: (doc['data']['dcm_energy'], log(doc['data']['I0'] / doc['data']['It']))
        ref   = lambda doc: (doc['data']['dcm_energy'], log(doc['data']['It'] / doc['data']['Ir']))
        Yield = lambda doc: (doc['data']['dcm_energy'], -1*doc['data']['Iy'] / doc['data']['I0'])
        fluo  = lambda doc: (doc['data']['dcm_energy'], (doc['data']['DTC1'] +
                                                         doc['data']['DTC2'] +
                                                         doc['data']['DTC3'] +
                                                         doc['data']['DTC4']) / doc['data']['I0'])
        if 'fluo'    in p['mode'] or 'flou' in p['mode']:
            plot =  DerivedPlot(fluo,  xlabel='energy (eV)', ylabel='absorption (fluorescence)')
        elif 'trans' in p['mode']:
            plot =  DerivedPlot(trans, xlabel='energy (eV)', ylabel='absorption (transmission)')
        elif 'ref'   in p['mode']:
            plot =  DerivedPlot(ref,   xlabel='energy (eV)', ylabel='absorption (reference)')
        elif 'yield' in p['mode']:
            plot =  DerivedPlot(Yield, xlabel='energy (eV)', ylabel='absorption (electron yield)')
        elif 'both'  in p['mode']:
            plot = [DerivedPlot(trans, xlabel='energy (eV)', ylabel='absorption (transmission)'),
                    DerivedPlot(fluo,  xlabel='energy (eV)', ylabel='absorption (fluorescence)')]
        else:
            print(colored('Plotting mode not specified, falling back to a transmission plot', 'lightred'))
            plot =  DerivedPlot(trans, xlabel='energy (eV)', ylabel='absorption (transmission)')


        ## --*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--
        ## engage suspenders right before starting scan sequence
        if 'force' in kwargs and kwargs['force'] is True:
            pass
        else:
            BMM_suspenders()
            
        ## --*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--
        ## begin the scan sequence with the plotting subscription
        @subs_decorator(plot)
        def scan_sequence(clargs):
            ## perhaps enter pseudo-channel-cut mode
            if not dcm.suppress_channel_cut:
                BMM_log_info('entering pseudo-channel-cut mode at %.1f eV' % eave)
                print(colored('entering pseudo-channel-cut mode at %.1f eV' % eave, 'white'))
                dcm.mode = 'fixed'
                yield from mv(dcm.energy, eave)
                dcm.mode = 'channelcut'


            ## --*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--
            ## compute energy and dwell grids
            print(colored('computing energy and dwell time grids', 'white'))
            (energy_grid, time_grid, approx_time) = conventional_grid(p['bounds'], p['steps'], p['times'], e0=p['e0'])
            if energy_grid is None or time_grid is None or approx_time is None:
                print(colored('Cannot interpret scan grid parameters!  Bailing out....' % outfile, 'lightred'))
                BMM_xsp.final_log_entry = False
                yield from null()
                return


            ## --*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--
            ## organize metadata for injection into database and XDI output
            print(colored('gathering metadata', 'white'))
            md = bmm_metadata(measurement   = p['mode'],
                              experimenters = p['experimenters'],
                              edge          = p['edge'],
                              element       = p['element'],
                              edge_energy   = p['e0'],
                              direction     = 1,
                              scantype      = 'step',
                              channelcut    = p['channelcut'],
                              mono          = 'Si(%s)' % dcm._crystal,
                              i0_gas        = 'N2', #\
                              it_gas        = 'N2', # > these three need to go into INI file
                              ir_gas        = 'N2', #/
                              sample        = p['sample'],
                              prep          = p['prep'],
                              stoichiometry = None,
                              mode          = p['mode'],
                              comment       = p['comment'],
                          )

            ## --*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--
            ## show the metadata to the user
            for (k, v) in md.items():
                print('\t%-28s : %s' % (k[4:].replace(',','.'),v))

            ## --*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--
            ## this dictionary is used to populate the static html page for this scan sequence
            html_scan_list = ''
            html_dict['filename']      = p['filename']
            html_dict['start']         = p['start']
            html_dict['end']           = p['start']+p['nscans']-1
            html_dict['seqstart']      = now('%A, %B %d, %Y %I:%M %p')
            html_dict['e0']            = p['e0']
            html_dict['element']       = p['element']
            html_dict['edge']          = p['edge']
            html_dict['motors']        = motor_sidebar()
            html_dict['sample']        = p['sample']
            html_dict['prep']          = p['prep']
            html_dict['comment']       = p['comment']
            html_dict['mode']          = p['mode']
            html_dict['pccenergy']     = eave
            html_dict['bounds']        = ' '.join(map(str, p['bounds_given'])) # see https://stackoverflow.com/a/5445983
            html_dict['steps']         = ' '.join(map(str, p['steps']))
            html_dict['times']         = ' '.join(map(str, p['times']))
            html_dict['clargs']        = clargs

            ## --*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--
            ## snap photos
            if p['snapshots']:
                ahora = now()

                html_dict['websnap'] = "%s_XASwebcam_%s.jpg" % (p['filename'], ahora)
                image = os.path.join(p['folder'], 'snapshots', html_dict['websnap'])
                annotation = 'NIST BMM (NSLS-II 06BM)      ' + p['filename'] + '      ' + ahora
                snap('XAS', filename=image, annotation=annotation)

                html_dict['anasnap'] = "%s_analog_%s.jpg" % (p['filename'], ahora)
                image = os.path.join(p['folder'], 'snapshots', html_dict['anasnap'])
                snap('analog', filename=image, sample=p['filename'])

            ## --*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--
            ## write dotfile
            with open(dotfile, "w") as f:
                f.write(str(datetime.datetime.timestamp(datetime.datetime.now())) + '\n')
                f.write('%.1f\n' % (approx_time * int(p['nscans']) * 60))
                
            ## --*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--
            ## loop over scan count
            count = 0
            for i in range(p['start'], p['start']+p['nscans'], 1):
                count += 1
                fname = "%s.%3.3d" % (p['filename'], i)
                datafile = os.path.join(p['folder'], fname)
                if os.path.isfile(datafile):
                    ## shouldn't be able to get here, unless a file
                    ## was written since the scan sequence began....
                    print(colored('%s already exists!  Bailing out....' % datafile, 'lightred'))
                    yield from null()
                    return
                print(colored('starting scan %d of %d, %d energy points' %
                              (count, p['nscans'], len(energy_grid)), 'white'))

                ## --*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--
                ## compute trajectory
                energy_trajectory    = cycler(dcm.energy, energy_grid)
                dwelltime_trajectory = cycler(dwell_time, time_grid)

                ## --*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--
                ## need to set certain metadata items on a per-scan basis... temperatures, ring stats
                ## mono direction, ... things that can change during or between scan sequences
                md['XDI,Mono,direction'] = 'forward'
                if p['bothways'] and count%2 == 0:
                    energy_trajectory    = cycler(dcm.energy, energy_grid[::-1])
                    dwelltime_trajectory = cycler(dwell_time, time_grid[::-1])
                    md['XDI,Mono,direction'] = 'backward'
                rightnow = metadata_at_this_moment() # see 62-metadata.py


                ## --*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--
                ## call the stock scan_nd plan with the correct detectors
                if 'trans' in p['mode'] or 'ref' in p['mode'] or 'yield' in p['mode']:
                    yield from scan_nd([quadem1], energy_trajectory + dwelltime_trajectory,
                                       md={**md, **rightnow, **supplied_metadata})
                else:
                    yield from scan_nd([quadem1, vor], energy_trajectory + dwelltime_trajectory,
                                       md={**md, **rightnow, **supplied_metadata})
                header = db[-1]
                write_XDI(datafile, header, p['mode'], p['comment']) # yield from ?
                print(colored('wrote %s' % datafile, 'white'))
                BMM_log_info('energy scan finished, uid = %s, scan_id = %d\ndata file written to %s'
                             % (header.start['uid'], header.start['scan_id'], datafile))

                ## --*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--
                ## generate left sidebar text for the static html page for this scan sequence
                js_text = '<a href="javascript:void(0)" onclick="toggle_visibility(\'%s\');" title="This is the scan number for %s, click to show/hide its UID">#%d</a><div id="%s" style="display:none;"><small>%s</small></div>' \
                          % (fname, fname, header.start['scan_id'], fname, header.start['uid'])
                printedname = fname
                if len(p['filename']) > 11:
                    printedname = fname[0:6] + '&middot;&middot;&middot;' + fname[-5:]
                html_scan_list += '<li><a href="../%s" title="Click to see the text of %s">%s</a>&nbsp;&nbsp;&nbsp;&nbsp;%s</li>\n' \
                                  % (fname, fname, printedname, js_text)
                html_dict['scanlist'] = html_scan_list


            ## --*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--
            ## finish up, close out
            print('Returning to fixed exit mode and returning DCM to %1.f' % eave)
            dcm.mode = 'fixed'
            yield from mv(dcm.energy, eave)
            html_dict['seqend'] = now('%A, %B %d, %Y %I:%M %p')

        ## --*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--
        ## execute this scan sequence plan
        yield from scan_sequence(clargs)

    def cleanup_plan(inifile):
        print('Cleaning up after an XAFS scan sequence')
        RE.clear_suspenders()
        if os.path.isfile(dotfile):
            os.remove(dotfile)

        ## db[-1].stop['num_events']['primary'] should equal db[-1].start['num_points'] for a complete scan
        how = 'finished'
        if db[-1].stop['num_events']['primary'] != db[-1].start['num_points']:
            how = 'stopped'
        if BMM_xsp.final_log_entry is True:
            BMM_log_info('XAFS scan sequence %s\nmost recent uid = %s, scan_id = %d'
                         % (how, db[-1].start['uid'], db[-1].start['scan_id']))
            htmlout = scan_sequence_static_html(inifile=inifile, **html_dict)
            if htmlout is not None:
                print(colored('wrote dossier %s' % htmlout, 'white'))
                BMM_log_info('wrote dossier to\n%s' % htmlout)
        #else:
        #    BMM_log_info('XAFS scan sequence finished early')
        dcm.mode = 'fixed'
        yield from abs_set(_locked_dwell_time.struck_dwell_time.setpoint, 0.5)
        yield from abs_set(_locked_dwell_time.quadem_dwell_time.setpoint, 0.5)
        yield from bps.sleep(2.0)
        yield from abs_set(dcm_pitch.kill_cmd, 1)
        yield from abs_set(dcm_roll.kill_cmd, 1)

    dotfile = '/home/xf06bm/Data/.xafs.scan.running'
    html_scan_list = ''
    html_dict = {}
    BMM_xsp.final_log_entry = True
    RE.msg_hook = None
    ## encapsulation!
    yield from bluesky.preprocessors.finalize_wrapper(main_plan(inifile, **kwargs), cleanup_plan(inifile))
    RE.msg_hook = BMM_msg_hook


def howlong(inifile, interactive=True, **kwargs):
    ## --*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--
    ## user input, find and parse the INI file
    ## try inifile as given then DATA + inifile
    ## this allows something like RE(xafs('myscan.ini')) -- short 'n' sweet
    orig = inifile
    if not os.path.isfile(inifile):
        inifile = DATA + inifile
        if not os.path.isfile(inifile):
            print(colored('\n%s does not exist!  Bailing out....\n' % orig, 'yellow'))
            return(orig, -1)
    print(colored('reading ini file: %s' % inifile, 'white'))
    (p, f) = scan_metadata(inifile=inifile, **kwargs)
    (ok, missing) = ini_sanity(f)
    if not ok:
        print(colored('\nThe following keywords are missing from your INI file: ', 'lightred'),
              '%s\n' % str.join(', ', missing))
        return(orig, -1)
    (energy_grid, time_grid, approx_time) = conventional_grid(p['bounds'], p['steps'], p['times'], e0=p['e0'])
    text = '\nEach scan (%d points) will take about %.1f minutes\n' % (len(energy_grid), approx_time)
    text +='The sequence of %s will take about %.1f hours' % (inflect('scan', p['nscans']), approx_time * int(p['nscans'])/60)
    if interactive:
        print(text)
    else:
        return(inifile, text)
