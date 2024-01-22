#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Archive .app to DMG file and create appcast for Sparkle.

USAGE:
    ./createappcast.py
"""

import os
import plistlib
import re
import shutil
import sys
from email.utils import formatdate
from string import Template


__date__ = '2018-01-14'
__author__ = '1024jp'
__copyright__ = '© 2018-2022 1024jp'

# const
APPCAST_NAME = 'appcast.xml'
TEMPLATE_PATH = 'appcast-template.xml'
SRC_PATH = 'CotEditor'


class Style:
    OK = '\033[32m'
    WARNING = '\033[33m'
    FAIL = '\033[31m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


ARROW = Style.OK + '==>' + Style.END + ' '


def main(src_path: str = SRC_PATH):
    """Create DMG and appcast.xml files from given directory.

    Arguments:
    src_path -- Path to the directory to be DMG.
    """
    # find application in the working directory
    for file_ in os.listdir(src_path):
        if file_.endswith('.app'):
            app_path = os.path.join(src_path, file_)
            break
    else:
        sys.exit(Style.FAIL + '[Error]' + Style.END +
                 ' No application found in the source folder.')

    # check existance of Sparkle.framework
    sparkle_path = app_path + "/Contents/Frameworks/Sparkle.framework"
    if not os.path.isdir(sparkle_path):
        sys.exit(Style.FAIL + '[Error]' + Style.END +
                 ' Sparkle framework is not bundled.')

    # get app info from Info.plist
    plist_path = os.path.join(app_path, 'Contents', 'Info.plist')
    with open(plist_path, 'rb') as fp:
        plist = plistlib.load(fp)
    app_name = plist['CFBundleName']
    version = plist['CFBundleShortVersionString']
    build_number = plist['CFBundleVersion']
    min_system_version = plist['LSMinimumSystemVersion']
    is_prerelease = re.search('[a-z]', version)

    channel = '<sparkle:channel>prerelease</sparkle:channel>' if is_prerelease\
        else ''

    print('📦 ' + Style.BOLD + app_name + ' ' + version + Style.END +
          ' ({}) ≧ macOS {}'.format(build_number, min_system_version))

    # create DMG
    print(ARROW + "Archiving to DMG file...")
    dmg_name = 'CotEditor_{}.dmg'.format(version)
    if not archive(src_path, dmg_name):
        sys.exit(Style.FAIL + 'Failed.' + Style.END)
    length = os.path.getsize(dmg_name)

    # run generate_appcast
    print(ARROW + "Generating edSignature...")
    shutil.move(dmg_name, 'archive')
    run_command('./generate_appcast archive')

    print(ARROW + "Creating appcast...")

    # read template
    template_file = open(TEMPLATE_PATH, 'r')
    template = Template(template_file.read())

    # replace template variables
    appcast = template.substitute({
                  'app_name': app_name,
                  'version': version,
                  'build_number': build_number,
                  'channel': channel,
                  'date': formatdate(localtime=True),
                  'min_system_version': min_system_version,
                  'dmg_name': dmg_name,
                  'length': length,
                  'edSignature': '',
              })

    # write appcast to file
    with open(APPCAST_NAME, 'w') as f:
        f.write(appcast)

    print('☕️ Done.')


def archive(src_path: str, dmg_path: str):
    """Create DMG file in HFS+ format.

    Arguments:
    src_path -- Path to the source folder.
    dmg_path -- Path to the distination of the created DMG file.
    """
    command = ('hdiutil create -format UDBZ -srcfolder {} {}'
               .format(src_path, dmg_path))

    return run_command(command)


def run_command(command: str) -> str:
    """Run shell command.

    Arguments:
    command -- Shell command.

    Return:
    result -- Returned value of the command.
    """
    process = os.popen(command)
    retval = process.readline()
    process.close()

    return retval.rstrip()


if __name__ == "__main__":
    main()
