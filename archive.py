#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Archive .app to DMG file and create appcast for Sparkle.

USAGE:
    ./createappcast.py
"""

from __future__ import print_function
import os
import plistlib
import re
import sys
from email.utils import formatdate
from string import Template


__date__ = '2018-01-14'
__author__ = '1024jp'
__copyright__ = '© 2018-2021 1024jp'

# const
APPCAST_NAME = 'appcast.xml'
APPCAST_BETA_NAME = 'appcast-beta.xml'
TEMPLATE_PATH = 'appcast-template.xml'
PRIVATE_KEY_PATH = 'sparkle/dsa_priv.pem'
SRC_PATH = 'CotEditor'
CODESIGN_IDENTITY = 'Developer ID Application: Mineko IMANISHI (HT3Z3A72WZ)'


class Style:
    OK = '\033[32m'
    WARNING = '\033[33m'
    FAIL = '\033[31m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


ARROW = Style.OK + '==>' + Style.END + ' '


def main(src_path=SRC_PATH):
    """Create DMG and appcast.xml files from given directory.

    Arguments:
    src_path (str) -- Path to the directory to be DMG.
    """
    # find application in the working directory
    for file_ in os.listdir(src_path):
        if file_.endswith('.app'):
            app_path = os.path.join(src_path, file_)
            break
    else:
        sys.exit(Style.FAIL + '[Error]' + Style.END +
                 ' No application found in the source folder.')

    # get app info from Info.plist
    plist_path = os.path.join(app_path, 'Contents', 'Info.plist')
    plist = plistlib.readPlist(plist_path)
    app_name = plist['CFBundleName']
    version = plist['CFBundleShortVersionString']
    build_number = plist['CFBundleVersion']
    min_system_version = plist['LSMinimumSystemVersion']
    is_prerelease = re.search('[a-z]', version)

    print('📦 ' + Style.BOLD + app_name + ' ' + version + Style.END +
          ' ({}) ≧ macOS {}'.format(build_number, min_system_version))

    # create DMG
    print(ARROW + "Archiving to DMG file...")
    dmg_name = 'CotEditor_{}.dmg'.format(version)
    if not archive(src_path, dmg_name):
        sys.exit(Style.FAIL + 'Failed.' + Style.END)
    codesign(CODESIGN_IDENTITY, dmg_name)
    length = os.path.getsize(dmg_name)

    # create DSA signature
    print(ARROW + "Creating DSA signature...")
    dsa = create_dsa_signature(dmg_name, PRIVATE_KEY_PATH)

    print(ARROW + "Creating appcast...")

    # read template
    template_file = open(TEMPLATE_PATH, 'rU')
    template = Template(template_file.read())

    # replace template variables
    appcast = template.substitute({
                  'app_name': app_name,
                  'version': version,
                  'build_number': build_number,
                  'date': formatdate(localtime=True),
                  'min_system_version': min_system_version,
                  'dmg_name': dmg_name,
                  'length': length,
                  'dsaSignature': dsa,
              })

    # write appcast to file
    with open(APPCAST_BETA_NAME, 'w') as f:
        f.write(appcast)
    if not is_prerelease:
        with open(APPCAST_NAME, 'w') as f:
            f.write(appcast)

    print('☕️ Done.')


def archive(src_path, dmg_path):
    """Create DMG file in HFS+ format.

    HFS+ format is forcedly used because the APFS is first introduced
    on macOS High Sierra.

    Arguments:
    src_path (str) -- Path to the source folder.
    dmg_path (str) -- Path to the distination of the created DMG file.
    """
    command = ('hdiutil create -format UDBZ -fs HFS+ -srcfolder {} {}'
               .format(src_path, dmg_path))

    return run_command(command)


def codesign(identity, dmg_path):
    """Codesign DMG file with the given identity.

    rguments:
    identity (str) -- Codesign identity.
    dmg_path (str) -- Path to the DMG file to sign.
    """
    command = 'codesign --force --sign "{}" {}'.format(identity, dmg_path)

    run_command(command)


def create_dsa_signature(filepath, key_path):
    """Create DSA signature for Sparkle framework.

    Arguments:
    filepath (str) -- Path to a file to create signature.
    key_path (str) -- Path to DSA private key file.

    Return:
    signature (str) -- Signature of given file.
    """
    command = ('openssl dgst -sha1 -binary < "{}" | '
               'openssl dgst -dss1 -sign "{}" | '
               'openssl enc -base64').format(filepath, key_path)

    return run_command(command)


def run_command(command):
    """Run shell command.

    Arguments:
    command (str) -- Shell command.

    Return:
    result (str) -- returned value of the command.
    """
    process = os.popen(command)
    retval = process.readline()
    process.close()

    return retval.rstrip()


if __name__ == "__main__":
    main()
