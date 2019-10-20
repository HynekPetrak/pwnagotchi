__author__ = 'evilsocket@gmail.com'
__version__ = '1.1.0'
__name__ = 'auto-update'
__license__ = 'GPL3'
__description__ = 'This plugin checks when updates are available and applies them when internet is available.'

import logging
import subprocess
import requests
import platform

import pwnagotchi
from pwnagotchi.utils import StatusFile

OPTIONS = dict()
READY = False
STATUS = StatusFile('/root/.auto-update')


def on_loaded():
    global READY
    if 'interval' not in OPTIONS or ('interval' in OPTIONS and OPTIONS['interval'] is None):
        logging.error("[update] main.plugins.auto-update.interval is not set")
        return
    READY = True
    logging.info("[update] plugin loaded.")


def check(version, repo, native=True):
    logging.debug("checking remote version for %s, local is %s" % (repo, version))
    info = {
        'current': version,
        'available': None,
        'url': None
    }

    resp = requests.get("https://api.github.com/repos/%s/releases/latest" % repo)
    latest = resp.json()
    latest_ver = latest['tag_name'].replace('v', ' ')
    arch = platform.machine()
    is_arm = arch.startswith('arm')

    if latest_ver != info['current']:
        if not native:
            info['url'] = "https://github.com/%s/archive/%s.zip" % (repo, latest['tag_name'])
        else:
            # check if this release is compatible with arm6
            for asset in latest['assets']:
                download_url = asset['browser_download_url']
                if download_url.endswith('.zip') and (arch in download_url or is_arm and 'armhf' in download_url):
                    info['url'] = download_url
                    break

    return info


def on_internet_available(agent):
    global STATUS

    logging.debug("[update] internet connectivity is available (ready %s)" % READY)

    if READY:
        if STATUS.newer_then_hours(OPTIONS['interval']):
            logging.debug("[update] last check happened less than %d hours ago" % OPTIONS['interval'])
            return

        logging.info("[update] checking for updates ...")

        display = agent.view()
        prev_status = display.get('status')

        try:
            display.set('status', 'Checking for updates ...')
            display.update(force=True)

            to_install = []
            to_check = [
                (
                'bettercap/bettercap', subprocess.getoutput('bettercap -version').split(' ')[1].replace('v', ''), True),
                ('evilsocket/pwngrid', subprocess.getoutput('pwngrid -version').replace('v', ''), True),
                ('evilsocket/pwnagotchi', pwnagotchi.version, False)
            ]

            for repo, local_version, is_native in to_check:
                info = check(local_version, repo, is_native)
                if info['url'] is not None:
                    logging.warning("new update for %s is available: %s" % (repo, info['url']))
                    to_install.append(info)

            num_updates = len(to_install)
            if num_updates > 0:
                if OPTIONS['install']:
                    logging.info("[update] TODO: install %d updates" % len(to_install))
                else:
                    prev_status = '%d new update%c available!' % (num_updates, 's' if num_updates > 1 else '')

            logging.info("[update] done")

            STATUS.update()

        except Exception as e:
            logging.error("[update] %s" % e)

        logging.debug("[update] setting status '%s'" % prev_status)
        display.set('status', prev_status if prev_status is not None else '')
        display.update(force=True)