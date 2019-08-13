
import requests
import os
import datetime
from PIL import Image
from io import BytesIO

run_report(__file__)

## grab a snapshot from the XAS camera
##    snap('XAS', filename='/path/to/saved/image.jpg')
##
## grab a snapshot from the XRD camera
##    snap('XRD', filename='/path/to/saved/image.jpg')
##
## grab a snapshot from the analog camera
##    snap('analog', filename='/path/to/saved/image.jpg')

from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw 

def annotate_image(imagefile, text):
    bluesky_path_as_list = bluesky.__path__[0].split('/') # crude, but finds current collection folder
    font_path = os.path.join('/', *bluesky_path_as_list[:4], 'lib', 'python3.6', 'site-packages', 'matplotlib', 'mpl-data', 'fonts', 'ttf')
    img = Image.open(imagefile)
    width, height = img.size
    draw = ImageDraw.Draw(img, 'RGBA')
    draw.rectangle(((0, int(9.5*height/10)), (width, height)), fill=(255,255,255,125))
    font = ImageFont.truetype(font_path + '/DejaVuSans.ttf', 24)
    draw.text((int(0.2*width/10), int(9.6*height/10)), text, (0,0,0), font=font)
    img.save(imagefile)



XASURL = 'http://10.6.129.56/axis-cgi/jpg/image.cgi'
XRDURL = 'http://10.6.129.55/axis-cgi/jpg/image.cgi'
CAM_PROXIES = {"http": None, "https": None,}

def snap(which, filename=None, **kwargs):
    if which is None: which = 'XAS'
    if which.lower() == 'xrd':
        xrd_webcam(filename=filename, **kwargs)
    elif 'ana' in which.lower() :
        anacam(filename=filename, **kwargs)
    else:
        xas_webcam(filename=filename, **kwargs)

def xas_webcam(filename=None, **kwargs):
    if filename is None:
        filename = os.environ['HOME'] + '/XAS_camera_' + now() + '.jpg'
    r=requests.get(XASURL, proxies=CAM_PROXIES)
    Image.open(BytesIO(r.content)).save(filename, 'JPEG')
    if 'annotation' in kwargs:
        annotate_image(filename, kwargs['annotation'])
    report('XAS webcam image written to %s' % filename)

def xrd_webcam(filename=None, **kwargs):
    if filename is None:
        filename = os.environ['HOME'] + '/XRD_camera_' + now() + '.jpg'
    r=requests.get(XRDURL, proxies=CAM_PROXIES)
    Image.open(BytesIO(r.content)).save(filename, 'JPEG')
    if 'annotation' in kwargs:
        annotate_image(filename, kwargs['annotation'])
    report('XRD webcam image written to %s' % filename)


from os import system
from subprocess import Popen, PIPE, call
import fcntl

def anacam(filename    = None,
           sample      = None,
           folder      = os.environ['HOME'],
           device      = '/dev/video0',
           camera      = 0,
           skip        = 30,
           frames      = 5,
           brightness  = 20,
           x           = 320,
           y           = 240,
           linecolor   = 'white',
           nocrosshair = True,
           quiet       = False,
           reset       = False,
           usbid       = '534d:0021',
           title       = 'NIST BMM (NSLS-II 06BM)',
           timestamp   = '%Y-%m-%d %H:%M:%S'):

    """A class for interacting with fswebcam in a way that meets the
    needs of 06BM.

    Parameters:
        folder:      location to drop jpg image         [$HOME]
        device:      char device of camera              [/dev/video0]
        camera:      camera number                      [0]
        skip:        number of frames to skip waiting for camera to wake up [30]
        frames:      number of frames to accumulate in image [5]
        brightness:  brightness setting of camera as a percentage [20]
        x:           X-location of cross hair           [320] (middle of image)
        y:           Y-location of cross hair           [240] (middle of image)
        linecolor:   color of cross hair lines          [white]
        nocrosshair: flag to suppress cross hair        [True]
        quiet:       flag to suppress screen messages   [False]
        usbid:       vendor and product ID of camera    [534d:0021] (AV to USB device at 06BM)
        title:       title string for fswebcam banner   [NIST BMM (NSLS-II 06BM)]
        filename:    output file name                   [ISO 8601 timestamp in folder]

    """

    USBDEVFS_RESET= 21780

    if reset is True:
        if not quiet: print("resetting video device")
        try:
            lsusb_out = Popen("lsusb | grep -i %s" % usbid,
                              shell=True,
                              bufsize=64,
                              stdin=PIPE,
                              stdout=PIPE, close_fds=True).stdout.read().strip().split()
            bus = lsusb_out[1].decode('UTF-8')
            device = lsusb_out[3][:-1].decode('UTF-8')
            print("/dev/bus/usb/%s/%s"%(bus, device))
            f = open("/dev/bus/usb/%s/%s"%(bus, device), 'w', os.O_WRONLY)
            fcntl.ioctl(f, USBDEVFS_RESET, 0)
            sleep(1)
        except Exception as msg:
            print("failed to reset device:", msg)

    quiet = ''
    if quiet: quiet = '-q '
    if filename is None:
        filename = folder + '/analog_camera_' + now() + '.jpg'

    if sample is not None:
        title = title + ' - ' + sample
    command = "fswebcam %s-i %s -d %s -r 640x480 --title \"%s\" --timestamp \"%s\" -S %d -F %d --set brightness=%s%% \"%s\"" %\
              (quiet, camera, device, title, timestamp, skip, frames, brightness, filename)
    system(command)

    report('Analog camera image written to %s' % filename)

    ## crosshairs
    #if not camera.nocrosshair:
    #    camera.crosshairs()
