# -*- coding: utf8 -*-
from time import sleep
import argparse
import sys
from ipaddress import IPv4Address

from boto.route53 import Route53Connection
from boto.exception import NoAuthHandlerFound
import DNS


HEADER = '\033[95m'
OKBLUE = '\033[94m'
OKGREEN = '\033[92m'
WARNING = '\033[93m'
FAIL = '\033[91m'
ENDC = '\033[0m'

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('domain', type=str,
                        help='Domain name which should resolve to your IP.')
    parser.add_argument('--quiet', '-q', action='store_true', default=False)
    parser.add_argument('--ip', type=IPv4Address,
                        help='Use this IP instead of auto-detecting')
    return parser.parse_args()

def wan_ip():
    """
    Return the WAN IP of the host running this script.
    """
    DNS.defaults['server'] = (
        'resolver1.opendns.com',
        'resolver2.opendns.com',
        'resolver3.opendns.com',
        'resolver4.opendns.com')
    res = DNS.DnsRequest('myip.opendns.com').qry()
    return res.answers[0]['data']


def normalise_domainname(name):
    """
    Ensure domain names are fully qualified; generally folk are used to
    specifying domain names without the final period.
    """
    if not name.endswith('.'):
        name = name + '.'
    return name


def find_zone(cn, domainname):
    """
    Figure out which hosted zone we care about, from the domain name provided.
    This also validates that `domainname' belongs to the current AWS account at
    all.
    """
    zones = cn.get_zones()

    # build a map of domainname -> zone
    namemap = {}
    for zone in zones:
        namemap.update({r.name: zone for r in zone.get_records()})

    if domainname in namemap:
        return namemap[domainname]
    else:
        err('Could not find {} in this account'.format(domainname), code=4)


def get_r53_conn():
    """
    Return a connection to Route 53.
    """
    try:
        return Route53Connection()
    except NoAuthHandlerFound:
        sys.stderr.write('Could not authenticate with AWS. Have you set '
                         'AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY?')
        sys.exit(1)


def colourise(msg, colour):
    if colour:
        assert colour in (HEADER, OKBLUE, OKGREEN, WARNING, FAIL, ENDC)
        msg = colour + msg + ENDC
    return msg


def err(msg, code):
    sys.stderr.write(colourise(msg + '\n', FAIL))
    sys.exit(code)


def verbose(msg, colour=None, *args, **kwargs):
    """
    print(), but not if --quiet. Also, colours.
    """
    if quiet:
        return
    print(colourise(msg, colour), *args, **kwargs)


def await_prop(status):
    """
    Given a record-update status, wait for it to become 'in sync'. Polls
    immediately, then every n+5 seconds.
    """
    delay = 0
    try:
        while status.status == 'PENDING':
            verbose('Waiting for DNS update to sync... ({}s)'.format(delay))
            sleep(delay)
            delay += 5
            status.update()
    except KeyboardInterrupt:
        sys.exit(0)


args = parse_args()
domain = normalise_domainname(args.domain)
quiet = args.quiet

verbose('Looking for {} in your Route 53'.format(domain))

local_ip = args.ip or wan_ip()
cn = get_r53_conn()
zone = find_zone(cn, domain)
record = zone.get_a(domain)
if not record:
    # find_zone would have failed if the record didn't exist at all, so a
    # failure here must mean the record is not type A
    err('{} is not an A record. To avoid an accident, Rome53 does not '
        'operate on records of other types.', code=2)

remote_ip, *more_ips = record.resource_records
if more_ips:
    ips = ', '.join(more_ips)
    err('{} has multiple records ({}). To avoid an accident, Rome53 will do '
        'nothing.'.format(domain, ips), code=3)


if local_ip == IPv4Address(remote_ip):
    verbose('Current WAN IP matches DNS record ({}). Doing '
            'nothing.'.format(local_ip))
    sys.exit(0)

verbose('Updating DNS A record to {} (was {})'.format(local_ip, remote_ip))
status = zone.update_a(domain, str(local_ip))

verbose('DNS update request succeeded.', colour=OKGREEN)
verbose('You can ^C now, or await confirmation '
        'of the propagation.')
await_prop(status)

print('{}\t{}'.format(domain, local_ip))
