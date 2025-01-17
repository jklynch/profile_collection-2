
from IPython import get_ipython
user_ns = get_ipython().user_ns

def purpose(val):
    ## typo correction, lexical interpretation here
    return {'purpose' : val.lower()}

def explain_purpose(val):
    if val == 'alignment':
        text = 'An motor scan to align an element of the photon delivery system or a stage on the XAS table.'
    elif val == 'mono_calibration':
        text = 'An XAFS scan used as part of the monochromator calibration procedure.'
    elif val == 'toss':
        text = 'Any plan used for a casual measurement not intended as part of the record of an experiment.'
    elif val == 'xafs':
        text = 'An XAFS scan.'
    elif val == 'xafs_metadata':
        text = 'An event or run intended as visual metadata accompanying an XAFS measurement.  Part of a dossier.'
    elif val == 'measurement':
        text = 'Any run intended as part of the record of an experiment, but which is not an XAFS scan.'
    else:
        text = '<unknown purpose>'
    return text
        

def uid_purpose(uid):
    db = user_ns['db']
    try:
        p = db.v2[uid].metadata['start']['purpose']
    except:
        p = '<unknown>'
    return p
