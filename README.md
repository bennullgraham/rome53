# Rome 53

Updates the IP address of a Route 53 record to the current host's WAN IP. If
you use Route 53 and can run this script regularly on a host behind a dynamic
IP, you can stop using a third-party dynamic DNS service.

## Installation

Unpack this script somewhere and make sure the python packages boto and py3dns
are available to it.

## Requirements

- Python 3
- Python packages boto and py3dns
- Values for `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
- A Route 53 hosted zone with an A-record subdomain

If you've been pointing a subdomain at a dynamic DNS subdomain in the past
(e.g. `subdomain.example.org -> subdomain.dyndns.com -> 1.2.3.4`), then you'll
be using a `CNAME` record. Rome 53 expects an `A` record, and to avoid
disaster, will not modify records of other types. 

To make the change, you should first manually update the subdomain to use an A
record.

## Usage

### Auth

The easiest way to provide credentials for AWS is to set the
`AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables before
running Rome 53.

### When your IP needs updating

```shell
$ python rome53.py subdomain.example.org
Looking for subdomain.example.org. in your Route 53
Updating DNS A record to 1.2.3.5 (was 1.2.3.4)
DNS update request succeeded.
You can ^C now, or await confirmation of the propagation.
Waiting for DNS update to sync... (0s)
Waiting for DNS update to sync... (5s)
subdomain.example.org 1.2.3.5
```

### When your IP is already correct

```shell
$ python rome53.py subdomain.example.org
Looking for subdomain.example.org. in your Route 53
Current WAN IP matches DNS record (1.2.3.5). Doing nothing.
```

### Choosing an address automatically

Rome 53 does this for you using `myip.opendns.com`. You can check which IP this
will currently result in using dig:

```shell
$ dig myip.opendns.com @resolver1.opendns.com +short
1.2.3.4
```

### Choosing an address manually

Use the `--ip` option. This is handy for undoing a mistake where, for example,
maybe you accidentally provided the wrong subdomain to Rome 53, and now your
payment gateway resolves to a computer in your kitchen.

```shell
$ python rome53.py gateway.example.org
Looking for gateway.example.org. in your Route 53
Updating DNS A record to 100.1.1.1 (was 50.1.1.1)
DNS update request succeeded.
# woops!

$ python rome53.py gateway.example.org --ip 50.1.1.1  # from "was..." above
Looking for gateway.example.org. in your Route 53
Updating DNS A record to 50.1.1.1 (was 100.1.1.1)
DNS update request succeeded.
```

## Automation

For scripting, use the `--quiet` option to reduce chattiness. When quiet, Rome
53 will produce no output unless an IP update occurs. If so, one line is
output: `<domain>\t<ipaddr>`. This is suitable for scripting or appending to a
log file.

Rome 53 does not check if it's already running. The await-sync stage can take
more than one minute, meaning an every-minute cron job may cause two Rome 53s
to run at once. This is probably harmless, but you may want to use `*/5`
anyway.
