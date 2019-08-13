import sys
import os
import shutil
from distutils.dir_util import copy_tree
import json
import pprint

run_report(__file__)


class BMM_User():
    '''A class for managing the user interaction at BMM.

    Experiment attributes:
      * DATA:             path to folder containing data
      * prompt:           flag, True prompt at beginning of plans
      * fianl_log_entry:  flag, True write log entries during plan cleanup
      * date:             start date of experiment as YYYY-MM-DD
      * gup:              GUP number
      * saf:              SAF number
      * name:             full name of PI
      * staff:            flag, True if a staff experiment

    Current plot attributes
      * motor:            fast motor in current plot
      * motor2:           slow motor in current plot
      * fig:              matplotlib.figure.Figure object of current plot
      * ax:               matplotlib.axes._subplots.AxisSubplot object of current plot
      * x:                plucked-upon X coordinate
      * y:                plucked-upon Y coordinate


    Energy scan control attributes, default values
      * pds_mode:         photon delivery system mode (A, B, C, D, E, F, XRD)
      * bounds:           list of energy or k scan boundaries
      * steps:            list of energy ot k steps
      * times:            list of integration times
      * folder:           data folder
      * filename:         output data file stub
      * experimenters:    names of experimenters
      * e0:               edge energy, reference for bounds
      * element:          absorbing element
      * edge:             absorption edge
      * sample:           sample composition or stoichiometry
      * prep:             how sample was prepared for measurement
      * comment:          anything else of interest about the sample
      * nscans:           number of scan repititions
      * start:            starting scan number
      * snapshots:        flag for taking snapshots
      * usbstick:         flag for rewriting USB-stick-safe filenames
      * rockingcurve:     flag for doing a rocking curve scan at the pseudo-channel-cut energy
      * htmlpage:         flag for writing dossier
      * bothways:         flag for measuring in both directions on mono
      * channelcut:       flag for measuring in pseudo-channel-cut mode
      * ththth:           flag for measuring with the Si(333) reflection
      * mode:             in-scan plotting mode

    Single energy time scan attributes, default values
      * npoints:          number of time points
      * dwell:            dwell time at each time step
      * delay:            delay between time steps

    Methods for public use:
      * start_experiment(self, name=None, date=None, gup=0, saf=0)
      * end_experiment(self, force=False)
      * show_experiment(self)
    '''
    def __init__(self):
        ## experiment attributes
        self.DATA            = os.path.join(os.getenv('HOME'), 'Data', 'bucket') + '/'
        self.prompt          = True
        self.final_log_entry = True
        self.date            = ''
        self.gup             = 0
        self.saf             = 0
        self.name            = None
        self.staff           = False
        self.read_foils      = None
        self.read_rois       = None
        self.user_is_defined = False

        self.roi_channel     = None   ##################################################################
        self.roi1            = 'ROI1' # in 76-edge.py, the ROI class is defined for managing changes   #
        self.roi2            = 'ROI2' # of configured detector channels. the names of the channels are #
        self.roi3            = 'ROI3' # are stored here for use in the various calls to DerivedPlot    #
        self.roi4            = 'ROI4' # and for writing column labels to output files                  #
        self.dtc1            = 'DTC1' ##################################################################
        self.dtc2            = 'DTC2'
        self.dtc3            = 'DTC3'
        self.dtc4            = 'DTC4'
                
        ## current plot attributes    #######################################################################
        self.motor  = None            # these are used to keep track of mouse events on the plotting window #
        self.motor2 = None            # see 70-linescans.py, and 71-areascan.py                             #
        self.fig    = None            #######################################################################
        self.ax     = None
        self.x      = None
        self.y      = None
        self.prev_fig = None
        self.prev_ax  = None
        #self.all_figs = []

        ## scan control attributes
        self.pds_mode      = None
        self.bounds        = [-200, -30, 15.3, '14k']  ## scan grid parameters
        self.steps         = [10, 0.5, '0.05k']
        self.times         = [0.5, 0.5, '0.25k']
        self.folder        = os.environ.get('HOME')+'/data/'
        self.filename      = 'data.dat'
        self.experimenters = ''
        self.e0            = None
        self.element       = None
        self.edge          = 'K'
        self.sample        = ''
        self.prep          = ''
        self.comment       = ''
        self.nscans        = 1
        self.start         = 0
        self.inttime       = 1
        self.snapshots     = True
        self.usbstick      = True
        self.rockingcurve  = False
        self.htmlpage      = True
        self.bothways      = False
        self.channelcut    = True
        self.ththth        = False
        self.mode          = 'transmission'
        self.npoints       = 0     ###########################################################################
        self.dwell         = 1.0   ## parameters for single energy absorption detection, see 72-timescans.py #
        self.delay         = 0.1   ###########################################################################
        
        ## mono acceleration control
        self.acc_fast      = 0.25  ###########################################################################
        self.acc_slow      = 0.5   # after decreasing Bragg acceleration time, Bragg axis would occasionally #
                                   # freeze. these are used to try to mitigate this problem                  #
                                   ###########################################################################
        
        self.bender_xas    = 212225  #####################################################################
        self.bender_xrd    = 112239  # approximate values for M2 bender for focusing at XAS & XRD tables #
        self.bender_margin = 30000   #####################################################################

        self.filter_state  = 0
                                     
    def show(self, scan=False):
        '''
        Show the current contents of the BMMuser object
        '''
        print('Experiment attributes:')
        for att in ('DATA', 'prompt', 'final_log_entry', 'date', 'gup', 'saf', 'name', 'staff', 'read_foils',
                    'read_rois', 'user_is_defined', 'pds_mode'):
            print('\t%-15s = %s' % (att, str(getattr(self, att))))

        print('\nROI control attributes:')
        for att in ('roi_channel', 'roi1', 'roi2', 'roi3', 'roi4', 'dtc1', 'dtc2', 'dtc3', 'dtc4'):
            print('\t%-15s = %s' % (att, str(getattr(self, att))))

        print('\nCurrent plot attributes:')
        for att in ('motor', 'motor2', 'fig', 'ax', 'x', 'y'):
            print('\t%-15s = %s' % (att, str(getattr(self, att))))

        print('\nMono acceleration and bender attributes:')
        for att in ('acc_fast', 'acc_slow', 'bender_xas', 'bender_xrd', 'bender_margin'):
            print('\t%-15s = %s' % (att, str(getattr(self, att))))

        if scan:
            print('\nScan control attributes:')
            for att in ('pds_mode', 'bounds', 'steps', 'times', 'folder', 'filename',
                        'experimenters', 'e0', 'element', 'edge', 'sample', 'prep', 'comment', 'nscans', 'start', 'inttime',
                        'snapshots', 'usbstick', 'rockingcurve', 'htmlpage', 'bothways', 'channelcut', 'ththth', 'mode', 'npoints',
                        'dwell', 'delay'):
                print('\t%-15s = %s' % (att, str(getattr(self, att))))
        
    def new_experiment(self, folder, gup=0, saf=0, name='Betty Cooper'):
        '''
        Do the work of prepping a new experiment.  This will:
          * Create a folder, if needed, and set the DATA variable
          * Set up the experimental log, creating an experiment.log file, if needed
          * Write templates for scan.ini and macro.py, if needed
          * Make the snapshots, dossier, and prj folders
          * Set the GUP and SAF numbers as metadata

        Input:
          folder:   data destination
          gup:      GUP number
          saf:      SAF number
          name:     name of PI (optional)
        '''

        step = 1
        ## make folder
        if not os.path.isdir(folder):
            os.makedirs(folder)
            print('%d. Created data folder:            %-75s' % (step, folder))
        else:
            print('%d. Found data folder:              %-75s' % (step, folder))
        imagefolder = os.path.join(folder, 'snapshots')
        if not os.path.isdir(imagefolder):
            os.mkdir(imagefolder)
            print('   Created snapshot folder:        %-75s' % imagefolder)
        else:
            print('   Found snapshot folder:          %-75s' % imagefolder)
    
        global DATA
        DATA = folder + '/'
        self.DATA = folder + '/'
        self.folder = folder + '/'
        step += 1

        ## setup logger
        BMM_user_log(os.path.join(folder, 'experiment.log'))
        print('%d. Set up experimental log file:   %-75s' % (step, os.path.join(folder, 'experiment.log')))
        step += 1

        startup = os.path.join(os.getenv('HOME'), '.ipython', 'profile_collection', 'startup')

        ## write scan.ini template
        initmpl = os.path.join(startup, 'scan.tmpl')
        scanini = os.path.join(folder, 'scan.ini')
        if not os.path.isfile(scanini):
            with open(initmpl) as f:
                content = f.readlines()
            o = open(scanini, 'w')
            o.write(''.join(content).format(folder=folder, name=name))
            o.close()
            print('%d. Created INI template:           %-75s' % (step, scanini))
        else:
            print('%d. Found INI template:             %-75s' % (step, scanini))
        step += 1

        ## write macro template
        macrotmpl = os.path.join(startup, 'macro.tmpl')
        macropy = os.path.join(folder, 'macro.py')
        if not os.path.isfile(macropy):
            with open(macrotmpl) as f:
                content = f.readlines()
            o = open(macropy, 'w')
            o.write(''.join(content).format(folder=folder))
            o.close()
            print('%d. Created macro template:         %-75s' % (step, macropy))
        else:
            print('%d. Found macro template:           %-75s' % (step, macropy))
        step += 1

        ## make html folder, copy static html generation files
        htmlfolder = os.path.join(folder, 'dossier')
        if not os.path.isdir(htmlfolder):
            os.mkdir(htmlfolder)
            for f in ('sample.tmpl', 'manifest.tmpl', 'logo.png', 'style.css', 'trac.css'):
                shutil.copyfile(os.path.join(startup, f),  os.path.join(htmlfolder, f))
            manifest = open(os.path.join(DATA, 'dossier', 'MANIFEST'), 'a')
            manifest.close()
            print('%d. Created dossier folder:         %-75s' % (step,htmlfolder))
            print('   copied html generation files, touched MANIFEST')
        else:
            print('%d. Found dossier folder:           %-75s' % (step,htmlfolder))
        step += 1
     
        ## make prj folder
        prjfolder = os.path.join(folder, 'prj')
        if not os.path.isdir(prjfolder):
            os.mkdir(prjfolder)
            print('%d. Created Athena prj folder:      %-75s' % (step,prjfolder))
        else:
            print('%d. Found Athena prj folder         %-75s' % (step,prjfolder))
        step += 1
   
        self.gup = gup
        self.saf = saf
        print('%d. Set GUP and SAF numbers as metadata' % step)
        step += 1

        self.user_is_defined = True
    
        return None

    def start_experiment(self, name=None, date=None, gup=0, saf=0):
        '''
        Get ready for a new experiment.  Run this first thing when a user
        sits down to start their beamtime.  This will:
          * Create a folder, if needed, and set the DATA variable
          * Set up the experimental log, creating an experiment.log file, if needed
          * Write templates for scan.ini and macro.py, if needed
          * Copy some other useful files
          * Make snapshots, dossier, and prj folders
          * Set the GUP and SAF numbers as metadata

        Input:
          name:     name of PI
          date:     YYYY-MM-DD start date of experiment (e.g. 2018-11-29)
          gup:      GUP number
          saf:      SAF number
        '''
        if self.user_is_defined:
            print(error_msg('An experiment is already started.'))
            return()
        if name is None:
            print(error_msg('You did not supply the user\'s name'))
            return()
        if date is None:
            print(error_msg('You did not supply the start date'))
            return()
        if gup == 0:
            print(error_msg('You did not supply the GUP number'))
            return()
        if saf == 0:
            print(error_msg('You did not supply the SAF number'))
            return()
        if name in BMM_STAFF:
            self.staff = True
            folder = os.path.join(os.getenv('HOME'), 'Data', 'Staff', name, date)
        else:
            self.staff = False
            folder = os.path.join(os.getenv('HOME'), 'Data', 'Visitors', name, date)
        self.name = name
        self.date = date
        self.new_experiment(folder, saf=saf, gup=gup, name=name)

        jsonfile = os.path.join(os.environ['HOME'], 'Data', '.user.json')
        if os.path.isfile(jsonfile):
            os.chmod(jsonfile, 0o644)
        with open(jsonfile, 'w') as outfile:
            json.dump({'name': name, 'date': date, 'gup' : gup, 'saf' : saf}, outfile)
        os.chmod(jsonfile, 0o444)


    def start_experiment_from_serialization(self):
        '''In the situation where bsui needs to be stopped (or crashes) before
        an experiment is properly ended using the end_experiment()
        command, this function will read a json serialization of the
        arguments to the start_experiment() command.

        The intent is that, if that serialization file is found at
        bsui start-up, this function is run so that the session is
        immediately ready for the current user.

        In the situation where this start-up script is "%run -i"-ed,
        the fact that self.user_is_defined is True will be recognized.
        '''
        if self.user_is_defined:
            return()
        jsonfile = os.path.join(os.environ['HOME'], 'Data', '.user.json')
        if os.path.isfile(jsonfile):
            user = json.load(open(jsonfile))
            if 'name' in user:
                self.start_experiment(name=user['name'], date=user['date'], gup=user['gup'], saf=user['saf'])
            if 'foils' in user:
                self.read_foils = user['foils'] # see 76-edge.py, line 114, need to delay configuring foils until 76-edge is read
            if 'rois' in user:
                self.read_rois  = user['rois']  # see 76-edge.py, line 189, need to delay configuring ROIs until 76-edge is read

    def show_experiment(self):
        '''Show serialized configuration parameters'''
        print('DATA  = %s' % DATA)
        print('GUP   = %d' % self.gup)
        print('SAF   = %d' % self.saf)
        print('foils = %s' % ' '.join(map(str, foils.slots)))
        print('ROIs  = %s' % ' '.join(map(str, rois.slots)))

    def end_experiment(self, force=False):
        '''
        Copy data from the experiment that just finished to the NAS, then
        unset the logger and the DATA variable at the end of an experiment.
        '''
        global DATA

        if not force:
            if not self.user_is_defined:
                print(error_msg('There is not a current experiment!'))
                return(None)

            #######################################################################################
            # create folder and sub-folders on NAS server for this user & experimental start date #
            #######################################################################################
            destination = os.path.join('/nist', 'xf06bm', 'user', self.name, self.date)
            if not os.path.isdir(destination):
                os.makedirs(destination)
            for d in ('dossier', 'prj', 'snapshots'):
                if not os.path.isdir(os.path.join(destination, d)):
                    os.makedirs(os.path.join(destination, d))
            try:
                copy_tree(DATA, destination)
                report('NAS data store: "%s"' % destination, 'bold')
            except:
                print(error_msg('Unable to write data to NAS server'))
        
            #####################################################################
            # remove the json serialization of the start_experiment() arguments #
            #####################################################################
            jsonfile = os.path.join(os.environ['HOME'], 'Data', '.user.json')
            if os.path.isfile(jsonfile):    
                os.chmod(jsonfile, 0o644)
                os.remove(jsonfile)

        ###############################################################
        # unset self attributes, DATA, and experiment specific logger #
        ###############################################################
        BMM_unset_user_log()
        DATA = os.path.join(os.environ['HOME'], 'Data', 'bucket') + '/'
        self.DATA = os.path.join(os.environ['HOME'], 'Data', 'bucket') + '/'
        self.date = ''
        self.gup = 0
        self.saf = 0
        self.name = None
        self.staff = False
        self.user_is_defined = False

        return None

BMMuser = BMM_User()
BMMuser.start_experiment_from_serialization()

if BMMuser.pds_mode is None:
    try:                        # do the right then when "%run -i"-ed
        BMMuser.pds_mode = get_mode()
    except:                     # else wait until later to set this correctly, get_mode() defined in 74-mode.py
        pass


pp = pprint.pprint
    
## some backwards compatibility....
whoami           = BMMuser.show_experiment
start_experiment = BMMuser.start_experiment
end_experiment   = BMMuser.end_experiment
