#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Create appcast for Sparkle.

USAGE:
    ./createappcast.py path_to_dmg
"""

from __future__ import print_function
import os
import plistlib
import re
import sys
from email.Utils import formatdate
from string import Template


__date__ = '2018-01-14'
__author__ = '1024jp'
__copyright__ = '© 2018 1024jp'

# const
APPCAST_NAME = 'appcast.xml'
APPCAST_BETA_NAME = 'appcast-beta.xml'
PRIVATE_KEY_PATH = 'sparkle/dsa_priv.pem'
TEMPLATE_PATH = 'appcast-template.xml'
WD_PATH = 'CotEditor'


def main(dir_path=WD_PATH):
    """Create DMG and appcast.xml files from given directory.

    Arguments:
    dir_path (str) -- Path to the directory to be DMG.
    """
    # find application in the working directory
    print('looking for application in {}'.format(dir_path))
    for file_ in os.listdir(dir_path):
        if file_.endswith('.app'):
            app_path = os.path.join(dir_path, file_)
            break
    else:
        print('[error] No application found in diskimage.')
        return

    # get app info from binary
    plist_path = os.path.join(app_path, 'Contents', 'Info.plist')
    plist = plistlib.readPlist(plist_path)
    app_name = plist['CFBundleName']
    version = plist['CFBundleShortVersionString']
    build_number = plist['CFBundleVersion']
    min_system_version = plist['LSMinimumSystemVersion']
    is_prerelease = re.search('[a-z]', version)

    print("found {} {} ({}) ≧ macOS {}".format(
        app_name, version, build_number, min_system_version))

    # Create DMG forcing using HFS+
    #   -> Because the APFS is first introduced on macOS High Sierra.
    print("creating DMG file...")
    dmg_name = 'CotEditor_{}.dmg'.format(version)
    run_command('hdiutil create -format UDBZ -fs HFS+ -srcfolder {} {}'
                .format(dir_path, dmg_name))
    length = os.path.getsize(dmg_name)

    # create DSA signature
    print("creating DSA signature...")
    dsa = create_dsa_signature(dmg_name, PRIVATE_KEY_PATH)

    print("creating appcast...")

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
                  'signature': dsa,
              })

    # write appcast to file
    with open(APPCAST_BETA_NAME, 'w') as f:
        f.write(appcast)
    if not is_prerelease:
        with open(APPCAST_NAME, 'w') as f:
            f.write(appcast)

    print('done ☕️')


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
