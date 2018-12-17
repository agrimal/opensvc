"""
nodemgr command line actions and options
"""
import node
from storage import Storage
from rcOptParser import OptParser
from optparse import Option

PROG = "nodemgr"

OPT = Storage({
    "api": Option(
        "--api", default=None, action="store", dest="api",
        help="Specify a collector api url different from the "
             "one set in node.conf."),
    "add": Option(
        "--add", default=None,
        action="store",
        help="A list member to add to the value pointed by :opt:``--param``. "
             "If :opt:``--index`` is set, insert the new element at the "
             "specified position in the list."),
    "app": Option(
        "--app", default=None, action="store", dest="app",
        help="Optional with the register command. Register the "
             "node in the specified app. If not specified, the "
             "node is registered in the first registering "
             "user's app found."),
    "attach": Option(
        "--attach", default=False,
        action="store_true", dest="attach",
        help="Attach the modulesets specified in a compliance run."),
    "author": Option(
        "--author", default=None,
        action="store", dest="author",
        help="The acker name to log when acknowledging action log errors"),
    "backlog": Option(
        "--backlog", default=None,
        action="store", dest="backlog",
        help="A size expression limiting the volume of data fetched "
             "from the log file tail. Default is 10k."),
    "begin": Option(
        "--begin", default=None,
        action="store", dest="begin",
        help="A begin date expressed as ``YYYY-MM-DD hh:mm`` limiting the "
             "timerange the action applies to."),
    "broadcast": Option(
        "--broadcast", default=None,
        action="store", dest="broadcast",
        help="A list of broadcast addresses, comma separated, the send "
             "the Wake-On-LAN packets to."),
    "color": Option(
        "--color", default="auto",
        action="store", dest="color",
        help="Colorize output. Possible values are:\n\n"
             "* auto: guess based on tty presence\n"
             "* always|yes: always colorize\n"
             "* never|no: never colorize"),
    "comment": Option(
        "--comment", default=None,
        action="store", dest="comment",
        help="A comment to log when acknowldging action log error entries."),
    "config": Option(
        "--config", default=None, action="store", dest="config",
        help="Specify a user-specific collector api connection "
             "configuration file. Defaults to '~/.opensvc-cli'."),
    "cluster": Option(
        "--cluster", default=False,
        action="store_true", dest="cluster",
        help="If set, the action is executed on all cluster nodes via each "
             "node's listener."),
    "cron": Option(
        "--cron", default=False,
        action="store_true", dest="cron",
        help="If set, the action is actually executed impersonating the "
             "scheduler thread."),
    "debug": Option(
        "--debug", default=False,
        action="store_true", dest="debug",
        help="Increase stream log verbosity up to the debug level."),
    "devices": Option(
        "--dev", default=[], action="append", dest="devices",
        help="A device path to limit or apply the action to."),
    "discard": Option(
        "--discard", default=False,
        action="store_true", dest="discard",
        help="Discard the stashed, invalid, configuration file."),
    "duration": Option(
        "--duration", default=None,
        action="store", dest="duration",
        help="A duration expression like, ``1h10m``."),
    "end": Option(
        "--end", default=None,
        action="store", dest="end",
        help="A end date expressed as ``YYYY-MM-DD hh:mm`` limiting the "
             "timerange the action applies to."),
    "eval": Option(
        "--eval", default=False,
        action="store_true", dest="eval",
        help="If set with the :cmd:`nodemgr get` action, the printed value of "
             ":opt:`--param` is evaluated, scoped and dereferenced. If set "
             "with the :cmd:`nodemgr set` action, the current value is "
             "evaluated before mangling."),
    "filter": Option(
        "--filter", default="",
        action="store", dest="jsonpath_filter",
        help="A JSONPath expression to filter a JSON output."),
    "filterset": Option(
        "--filterset", default="",
        action="store", dest="filterset",
        help="Specify a filterset to limit collector extractions."),
    "follow": Option(
        "--follow", default=False,
        action="store_true", dest="follow",
        help="Follow the logs as they come. Use crtl-c to interrupt."),
    "force": Option(
        "--force", default=False,
        action="store_true", dest="force",
        help="Force action, ignore sanity checks."),
    "format": Option(
        "--format", default=None, action="store", dest="format",
        help="Specify a data formatter. Possible values are json, csv"
             " or table."),
    "hba": Option(
        "--hba", default=None, action="store", dest="hba",
        help="Specify a hba to scan for new block devices. Example: "
             "5001438002432430 or iqn.1993-08.org.debian:01:659b4bbd68bd."),
    "help": Option(
        "-h", "--help", default=None,
        action="store_true", dest="parm_help",
        help="Show this help message and exit"),
    "id": Option(
        "--id", default=0,
        action="store", dest="id",
        help="Specify an id to act on."),
    "index": Option(
        "--index", default=None,
        action="store", type="int",
        help="The position in the list pointed by --param where to add "
             "the new list element on a set action"),
    "insecure": Option(
        "--insecure", default=None,
        action="store_true", dest="insecure",
        help="Allow communications with a collector presenting an "
             "unverified SSL certificate."),
    "kw": Option(
        "--kw", action="append", dest="kw",
        help="An expression like ``[<section>.]<keyword>[@<scope>][[<index>]]<op><value>`` where\n\n"
             "* <section> can be:\n\n"
             "  * a resource id\n"
             "  * a resource driver group name (fs, ip, ...). In this case, the set applies to all matching resources.\n"
             "* <op> can be:\n\n"
             "  * ``=``\n"
             "  * ``+=``\n"
             "  * ``-=``\n\n"
             "Multiple --kw can be set to apply multiple configuration change "
             "in a file with a single write.\n\n"
             "Examples:\n\n"
             "* app.start=false\n"
             "  Turn off app start for all app resources\n"
             "* app#1.start=true\n"
             "  Turn on app start for app#1\n"
             "* nodes+=node3\n"
             "  Append node3 to nodes\n"
             "* nodes[0]+=node3\n"
             "  Preprend node3 to nodes\n"),
    "like": Option(
        "--like", default="%",
        action="store", dest="like",
        help="A data filtering expression. ``%`` is the multi-character "
             "wildcard. ``_`` is the single-character wildcard. Leading and "
             "trailing ``%`` are automatically set."),
    "local": Option(
        "--local", default=False,
        action="store_true", dest="local",
        help="Set to disable cluster-wide operations."),
    "lun": Option(
        "--lun", default=None, action="store", dest="lun",
        help="Specify a logical unit number to scan for new block devices. "
             "Example: 1."),
    "mac": Option(
        "--mac", default=None,
        action="store", dest="mac",
        help="A list of mac addresses, comma separated, used as target of "
             "the Wake-On-LAN packets."),
    "message": Option(
        "--message", default="",
        action="store", dest="message",
        help="The message to send to the collector for logging"),
    "module": Option(
        "--module", default="",
        action="store", dest="module",
        help="Specify the modules to limit the run to. The modules must be in already attached modulesets."),
    "moduleset": Option(
        "--moduleset", default="",
        action="store", dest="moduleset",
        help="Specify the modulesets to limit the action to. The special value ``all`` "
             "can be used in conjonction with detach."),
    "node": Option(
        "--node", default="",
        action="store", dest="node",
        help="The node to send a request to. If not specified the local node is targeted."),
    "nopager": Option(
        "--no-pager", default=False,
        action="store_true", dest="nopager",
        help="Do not display the command result in a pager."),
    "opt_object": Option(
        "--object", default=[], action="append", dest="objects",
        help="An object to limit a push* action to. Multiple "
             "--object <object id> parameters can be set on a "
             "single command line."),
    "param": Option(
        "--param", default=None,
        action="store", dest="param",
        help="An expression like ``[<section>.]<keyword>`` where\n\n"
             "* <section> can be:\n\n"
             "  * a resource id\n"
             "  * a resource driver group name (fs, ip, ...). In this case, the set applies to all matching resources."),
    "password": Option(
        "--password", default=None,
        action="store", dest="password",
        help="Authenticate with the collector using the "
             "specified user credentials instead of the node "
             "credentials. Prompted if necessary but not "
             "specified."),
    "port": Option(
        "--port", default=7,
        action="store", dest="port",
        help="A list of ports, comma separated, used as target of "
             "the Wake-On-LAN packets."),
    "recover": Option(
        "--recover", default=False,
        action="store_true", dest="recover",
        help="Recover the stashed erroneous configuration file "
             "in a :cmd:`nodemgr edit config` command"),
    "refresh_api": Option(
        "--refresh-api", default=False,
        action="store_true", dest="refresh_api",
        help="Force a reload of the collector's api digest."),
    "remove": Option(
        "--remove", default=None,
        action="store",
        help="A list member to drop from the value pointed by :kw:`--param`."),
    "reverse": Option(
        "--reverse", default=False,
        action="store_true", dest="reverse",
        help="Print the tree leaf-to-root."),
    "ruleset": Option(
        "--ruleset", default="",
        action="store", dest="ruleset",
        help="Specify the rulesets to limit the action to. The special value ``all`` "
             "can be used in conjonction with detach."),
    "ruleset_date": Option(
        "--ruleset-date", default="",
        action="store", dest="ruleset_date",
        help="Use an historical ruleset, specified by its date."),
    "save": Option(
        "--save", default=False,
        action="store_true", dest="save",
        help="Save the collector cli settings to the file specified by --config or ~/.opensvc-cli by default."),
    "stats_dir": Option(
        "--stats-dir", default=None,
        action="store", dest="stats_dir",
        help="Points the directory where the metrics files are "
             "stored for pushstats."),
    "secret": Option(
        "--secret", default=None,
        action="store", dest="secret",
        help="The cluster secret used as the AES key in the cluster "
             "communications."),
    "symcli_db_file": Option(
        "--symcli-db-file", default=None,
        action="store", dest="symcli_db_file",
        help="Use symcli offline mode with the "
             "specified file. The aclx files are expected to be "
             "found in the same directory and named either "
             "<symid>.aclx or <same_prefix_as_bin_file>.aclx."),
    "sync": Option(
        "--sync", default=False,
        action="store_true", dest="syncrpc",
        help="Use synchronous collector communication. For example, "
             ":cmd:`pushasset --sync` before a compliance run makes sure "
             "the pushed data has hit the collector database before the "
             "rulesets are contextualized."),
    "tag": Option(
        "--tag", default=None,
        action="store", dest="tag",
        help="The tag name, as shown by :cmd:`nodemgr collector list tags`."),
    "target": Option(
        "--target", default=None, action="store", dest="target",
        help="Specify a target to scan for new block devices. Example: "
             "5000097358185088 or iqn.clementine.tgt1."),
    "thr_id": Option(
        "--thread-id", default=None, action="store", dest="thr_id",
        help="Specify a daemon thread, as listed in the :cmd:`nodemgr daemon "
             "status` output."),
    "time": Option(
        "--time", default=300,
        action="store", dest="time", type="int",
        help="Number of seconds to wait for an async action to "
             "finish. Default is 300 seconds."),
    "user": Option(
        "--user", default=None, action="store", dest="user",
        help="Authenticate with the collector using the "
             "specified user credentials instead of the node "
             "credentials. Required with :cmd:`nodenmgr register` "
             "when the collector is configured to refuse "
             "anonymous register."),
    "value": Option(
        "--value", default=None,
        action="store", dest="value",
        help="The value to set for the keyword pointed by :opt:`--param`"),
    "verbose": Option(
        "--verbose", default=False,
        action="store_true", dest="verbose",
        help="Include more information to some print commands output. "
             "For example, add the ``next run`` column in the output of "
             ":cmd:`nodemgr print schedule`."),
    "wait": Option(
        "--wait", default=False,
        action="store_true", dest="wait",
        help="Wait for asynchronous action termination"),
})

GLOBAL_OPTS = [
    OPT.color,
    OPT.debug,
    OPT.format,
    OPT.filter,
    OPT.help,
]

ASYNC_OPTS = [
    OPT.time,
    OPT.wait,
]

DAEMON_OPTS = [
    OPT.local,
    OPT.node,
    OPT.cluster,
]

ACTIONS = {
    "Node actions": {
        "auto_reboot": {
            "msg": "Reboot the node if in the specified schedule.",
            "options": [
                OPT.cron,
            ],
        },
        "events": {
            "msg": "Follow the daemon events",
            "options": [
                OPT.local,
                OPT.node,
            ]
        },
        "frozen": {
            "msg": "Return 0 if the services are frozen node-wide, "
                   "preventing the daemon to orchestrate them. Return 1 "
                   "otherwise",
        },
        "freeze": {
            "msg": "Freeze services node-wide, preventing the daemon to "
                   "orchestrate them. This freeze method preserves the "
                   "frozen state at service-level (with svcmgr).",
            "options": ASYNC_OPTS + DAEMON_OPTS,
        },
        "thaw": {
            "msg": "Thaw services node-wide, allowing the daemon to "
                   "orchestrate them. This thaw method does not actually "
                   "thaw services frozen at service-level (with svcmgr).",
            "options": ASYNC_OPTS + DAEMON_OPTS,
        },
        "logs": {
            "msg": "Display of the nodemgr and daemon logs.",
            "options": [
                OPT.backlog,
                OPT.follow,
                OPT.local,
                OPT.node,
            ]
        },
        "ping": {
            "msg": "Ping a cluster node or arbitrator node. The ping "
                   "validates the remote is functional.",
            "options": [
                OPT.cluster,
                OPT.node,
            ]
        },
        "shutdown": {
            "msg": "Shutdown the node to powered off state.",
            "options": DAEMON_OPTS,
        },
        "reboot": {
            "msg": "Reboot the node.",
            "options": DAEMON_OPTS,
        },
        "schedule_reboot_status": {
            "msg": "Tell if the node is scheduled for reboot.",
        },
        "schedule_reboot": {
            "msg": "Mark the node for reboot at the next allowed period. The "
                   "allowed period is defined by a 'reboot' section in "
                   "node.conf.",
        },
        "unschedule_reboot": {
            "msg": "Unmark the node for reboot at the next allowed period.",
        },
        "array": {
            "msg": "Pass a command to a supported array whose access method "
                   "and credentials are defined in auth.conf.",
        },
        "updatepkg": {
            "msg": "Upgrade the opensvc agent version. the packages must be "
                   "available behind the node.repo/packages url.",
            "options": DAEMON_OPTS,
        },
        "updatecomp": {
            "msg": "Upgrade the opensvc compliance modules. The modules must "
                   "be available as a tarball behind the :kw:`node.repocomp` "
                   "url.",
            "options": DAEMON_OPTS,
        },
        "scanscsi": {
            "msg": "Scan the scsi hosts in search of new disks.",
            "options": [
                OPT.hba,
                OPT.target,
                OPT.lun,
            ],
        },
        "dequeue_actions": {
            "msg": "Dequeue and execute actions from the collector's action "
                   "queue for this node and its services.",
            "options": [
                OPT.cron,
            ],
        },
        "rotate_root_pw": {
            "msg": "Set a new root password and store it in the collector.",
            "options": [
                OPT.cron,
            ],
        },
        "print_devs": {
            "msg": "Print the node devices tree.",
            "options": [
                OPT.devices,
                OPT.reverse,
                OPT.verbose,
            ],
        },
        "print_schedule": {
            "msg": "Print the node tasks schedule.",
            "options": [
                OPT.verbose,
            ],
        },
        "stonith": {
            "msg": "Command executed by the daemon monitor to fence peer "
                   "node upon failover when the node previously running "
                   "the service is stale.",
            "options": [
                OPT.node,
            ],
        },
        "snooze": {
            "msg": "Snooze alerts on the node for :opt:`--duration`",
            "options": [
                OPT.duration,
            ],
        },
        "unsnooze": {
            "msg": "Unsnooze alerts on the node",
            "options": [],
        },
        "wait": {
            "msg": "Wait for the condition given by --filter to become true. "
                   "The condition applies to, so are rooted to, the monitor "
                   "thread data. The condition is expressed as "
                   "[!]<jonspath>[<op><val>]. Supported ops are '=', '>', "
                   "'>=', '<', '<=', '~'. '~' is a fullmatch of the <val> "
                   "regular expression unless '^' or '$' are specified. '!' "
                   "is the negation operator. If '<op><val>' is not specified,"
                   " any value evaluated as True is considered a match "
                   "(non-zero numerics, non-empty lists, non-emptry strings).",
            "options": [
                OPT.duration,
                OPT.local,
                OPT.node,
            ]
        },
        "wol": {
            "msg": "Forge and send a udp Wake-On-LAN packet to the mac addresses "
                   "specified by :opt:`--mac` and :opt:`--broadcast` arguments.",
            "options": [
                OPT.broadcast,
                OPT.mac,
                OPT.port,
            ],
        },
        "collect_stats": {
            "msg": "Write in local files metrics not found in the standard "
                   "metrics collector. These files will be fed to the "
                   "collector by the :cmd:`pushstat` action.",
            "options": [
                OPT.cron,
            ],
        },
    },
    "Pool actions": {
        "pool_ls": {
            "msg": "List the available pools.",
        },
        "pool_status": {
            "msg": "Show pools status.",
            "options": [
                OPT.id,
            ],
        },
    },
    "Network actions": {
        "network_ls": {
            "msg": "List the available networks.",
        },
        "network_show": {
            "msg": "Show a network configuration.",
            "options": [
                OPT.id,
            ],
        },
    },
    "Service actions": {
        "discover": {
            "msg": "Discover vservices accessible from this host. Typically executed on cloud nodes.",
        },
    },
    "Node configuration": {
        "print_config": {
            "msg": "Display the node current configuration.",
        },
        "print_authconfig": {
            "msg": "Display the node current authentication configuration.",
        },
        "edit_config": {
            "msg": "Edit the node configuration.",
            "options": [
                OPT.discard,
                OPT.recover,
            ],
        },
        "edit_authconfig": {
            "msg": "Edit the node authentication configuration.",
        },
        "register": {
            "msg": "Obtain a registration id from the collector. This is is "
                   "then used to authenticate the node in collector communications.",
            "options": [
                OPT.app,
                OPT.password,
                OPT.user,
            ],
        },
        "get": {
            "msg": "Get the raw or evaluated value of a node "
                   "configuration keyword.",
            "options": [
                OPT.eval,
                OPT.param,
                OPT.kw,
            ],
        },
        "set": {
            "msg": "Set a service configuration parameter.",
            "options": [
                OPT.add,
                OPT.eval,
                OPT.kw,
                OPT.index,
                OPT.param,
                OPT.remove,
                OPT.value,
            ],
        },
        "unset": {
            "msg": "Unset a node configuration parameter.",
            "options": [
                OPT.param,
                OPT.kw,
            ],
        },
        "validate_config": {
            "msg": "Check the section names and keywords are valid.",
        },
    },
    "Node daemon management": {
        "daemon_relay_status": {
            "msg": "Show the daemon relay clients and last update timestamp.",
        },
        "daemon_blacklist_status": {
            "msg": "Show the content of the daemon senders blacklist.",
        },
        "daemon_blacklist_clear": {
            "msg": "Empty the content of the daemon senders blacklist.",
        },
        "daemon_restart": {
            "msg": "Restart the daemon.",
        },
        "daemon_running": {
            "msg": "Return with code 0 if the daemon is running, else return "
                   "with code 1",
        },
        "daemon_shutdown": {
            "msg": "Stop all local services instances then stop the daemon.",
        },
        "daemon_status": {
            "msg": "Display the daemon status.",
            "options": [
                OPT.node,
            ],
        },
        "daemon_stats": {
            "msg": "Display the daemon stats.",
            "options": [
                OPT.node,
            ],
        },
        "daemon_start": {
            "msg": "Start the daemon or a daemon thread pointed by :opt:`--thread-id`.",
            "options": DAEMON_OPTS + [
                OPT.thr_id,
            ],
        },
        "daemon_stop": {
            "msg": "Stop the daemon or a daemon thread pointed by :opt:`--thread-id`.",
            "options": DAEMON_OPTS + [
                OPT.thr_id,
            ],
        },
        "daemon_join": {
            "msg": "Join the cluster of the node specified by :opt:`--node <node>`, authenticating with :opt:`--secret <secret>`.",
            "options": [
                OPT.node,
                OPT.secret,
            ],
        },
        "daemon_rejoin": {
            "msg": "Rejoin the cluster of the node specified by :opt:`--node <node>`, authenticating with the already known secret. This will re-merge the remote node cluster-wide configurations in the local node configuration file.",
            "options": [
                OPT.node,
            ],
        },
        "daemon_leave": {
            "msg": "Inform peer nodes we leave the cluster. Make sure the "
                   "left nodes are no longer in the services nodes list "
                   "before leaving, so the other nodes won't takeover.",
        },
    },
    "Push data to the collector": {
        "pushasset": {
            "msg": "Push asset information to collector.",
            "options": [
                OPT.sync,
                OPT.cron,
            ],
        },
        "pushstats": {
            "msg": "Push performance metrics to collector. By default pushed "
                   "stats interval begins yesterday at the beginning of the "
                   "allowed interval and ends now. This interval can be "
                   "changed using --begin/--end parameters. The location "
                   "where stats files are looked up can be changed using "
                   "--stats-dir.",
            "options": [
                OPT.begin,
                OPT.end,
                OPT.stats_dir,
                OPT.cron,
            ],
        },
        "pushdisks": {
            "msg": "Push disks usage information to the collector.",
            "options": [
                OPT.cron,
            ],
        },
        "pushpkg": {
            "msg": "Push package/version list to the collector.",
            "options": [
                OPT.cron,
            ],
        },
        "pushpatch": {
            "msg": "Push patch/version list to the collector.",
            "options": [
                OPT.cron,
            ],
        },
        "pushsym": {
            "msg": "Push symmetrix configurations to the collector.",
            "options": [
                OPT.cron,
                OPT.opt_object,
                OPT.symcli_db_file,
            ],
        },
        "pushemcvnx": {
            "msg": "Push EMC CX/VNX configurations to the collector.",
            "options": [
                OPT.cron,
                OPT.opt_object,
            ],
        },
        "pushcentera": {
            "msg": "Push EMC Centera configurations to the collector.",
            "options": [
                OPT.cron,
                OPT.opt_object,
            ],
        },
        "pushnetapp": {
            "msg": "Push Netapp configurations to the collector.",
            "options": [
                OPT.cron,
                OPT.opt_object,
            ],
        },
        "pusheva": {
            "msg": "Push HP EVA configurations to the collector.",
            "options": [
                OPT.cron,
                OPT.opt_object,
            ],
        },
        "pushnecism": {
            "msg": "Push NEC ISM configurations to the collector.",
            "options": [
                OPT.cron,
                OPT.opt_object,
            ],
        },
        "pushhds": {
            "msg": "Push HDS configurations to the collector.",
            "options": [
                OPT.cron,
                OPT.opt_object,
            ],
        },
        "pushdcs": {
            "msg": "Push Datacore configurations to the collector.",
            "options": [
                OPT.cron,
                OPT.opt_object,
            ],
        },
        "pushfreenas": {
            "msg": "Push FreeNAS configurations to the collector.",
            "options": [
                OPT.cron,
                OPT.opt_object,
            ],
        },
        "pushxtremio": {
            "msg": "Push XtremIO configurations to the collector.",
            "options": [
                OPT.cron,
                OPT.opt_object,
            ],
        },
        "pushibmsvc": {
            "msg": "Push IBM SVC configurations to the collector.",
            "options": [
                OPT.cron,
                OPT.opt_object,
            ],
        },
        "pushhp3par": {
            "msg": "Push HP 3par configurations to the collector.",
            "options": [
                OPT.cron,
                OPT.opt_object,
            ],
        },
        "pushibmds": {
            "msg": "Push IBM DS configurations to the collector.",
            "options": [
                OPT.cron,
                OPT.opt_object,
            ],
        },
        "pushvioserver": {
            "msg": "Push IBM VIO server configurations to the collector.",
            "options": [
                OPT.cron,
                OPT.opt_object,
            ],
        },
        "pushgcedisks": {
            "msg": "Push Google Compute Engine disks configurations to the "
                   "collector.",
            "options": [
                OPT.cron,
                OPT.opt_object,
            ],
        },
        "pushbrocade": {
            "msg": "Push Brocade switch configuration to the collector.",
            "options": [
                OPT.cron,
                OPT.opt_object,
            ],
        },
        "pushnsr": {
            "msg": "Push EMC Networker index to the collector.",
            "options": [
                OPT.cron,
                OPT.opt_object,
            ],
        },
        "sysreport": {
            "msg": "Push system report to the collector for archiving and "
                   "diff analysis. The --force option resend all monitored "
                   "files and outputs to the collector instead of only those "
                   "that changed since the last sysreport.",
            "options": [
                OPT.cron,
                OPT.force,
            ],
        },
        "checks": {
            "msg": "Run node health checks. Push results to collector.",
            "options": [
                OPT.cron,
            ],
        },
    },
    "Misc": {
        "prkey": {
            "msg": "Show the scsi3 persistent reservation key of this node.",
        },
    },
    "Compliance": {
        "compliance_auto": {
            "msg": "Run compliance checks or fixes, depending on the autofix "
                   "module property values.",
            "options": [
                OPT.cron,
            ],
        },
        "compliance_env": {
            "msg": "Show the environment variables set during a compliance module run.",
            "options": [
                OPT.module,
                OPT.moduleset,
            ],
        },
        "compliance_check": {
            "msg": "Run compliance checks.",
            "options": [
                OPT.attach,
                OPT.force,
                OPT.module,
                OPT.moduleset,
                OPT.ruleset_date,
            ],
        },
        "compliance_fix": {
            "msg": "Run compliance fixes.",
            "options": [
                OPT.attach,
                OPT.force,
                OPT.module,
                OPT.moduleset,
                OPT.ruleset_date,
            ],
        },
        "compliance_fixable": {
            "msg": "Verify compliance fixes prerequisites.",
            "options": [
                OPT.attach,
                OPT.force,
                OPT.module,
                OPT.moduleset,
                OPT.ruleset_date,
            ],
        },
        "compliance_list_module": {
            "msg": "List the compliance modules installed on this node.",
        },
        "compliance_show_moduleset": {
            "msg": "Show compliance rules applying to this node.",
        },
        "compliance_list_moduleset": {
            "msg": "List available compliance modulesets. Setting :opt:`--moduleset f%` "
                   "limits the resultset to modulesets matching the ``f%`` pattern.",
            "options": [
                OPT.moduleset,
            ],
        },
        "compliance_list_ruleset": {
            "msg": "List available compliance rulesets. Setting :opt:`--ruleset f%` limits "
                   "the scope to rulesets matching the ``f%`` pattern.",
            "options": [
                OPT.ruleset,
            ],
        },
        "compliance_show_ruleset": {
            "msg": "Show compliance rules applying to this node.",
        },
        "compliance_show_status": {
            "msg": "Show compliance modules status.",
        },
        "compliance_attach": {
            "msg": "Attach rulesets specified by :opt:`--ruleset` and modulesets "
                   "specified by :opt:`--moduleset` to this node. Attached modulesets "
                   "are scheduled for check or autofix.",
            "options": [
                OPT.moduleset,
                OPT.ruleset,
            ],
        },
        "compliance_detach": {
            "msg": "Detach rulesets specified by :opt:`--ruleset` and modulesets "
                   "specified by :opt:`--moduleset` from this node. Detached "
                   "modulesets are no longer scheduled for check and autofix.",
            "options": [
                OPT.moduleset,
                OPT.ruleset,
            ],
        },
    },
    "Collector management": {
        "collector_cli": {
            "msg": "Open a Command Line Interface to the collector rest API. "
                   "The CLI offers autocompletion of paths and arguments, "
                   "piping JSON data from files. "
                   "If executed as root and with no :opt:`--user`, the collector is "
                   "logged in with the node credentials.",
            "options": [
                OPT.user,
                OPT.password,
                OPT.api,
                OPT.insecure,
                OPT.config,
                OPT.refresh_api,
                OPT.save,
            ],
        },
        "collector_events": {
            "msg": "Display node events during the period specified by "
                   "--begin/--end. --end defaults to now. --begin defaults to "
                   "7 days ago.",
            "options": [
                OPT.begin,
                OPT.end,
            ],
        },
        "collector_alerts": {
            "msg": "Display the node alerts.",
        },
        "collector_checks": {
            "msg": "Display the node checks.",
        },
        "collector_disks": {
            "msg": "Display the node disks list, complete with information issued by array parser.",
        },
        "collector_list_actions": {
            "msg": "List actions on the node, whatever the service, during "
                   "the period specified by --begin/--end. --end defaults to "
                   "now. --begin defaults to 7 days ago.",
            "options": [
                OPT.begin,
                OPT.end,
            ],
        },
        "collector_ack_action": {
            "msg": "Acknowledge an action error on the node. An acknowlegment "
                   "can be completed by --author (defaults to root@nodename) "
                   "and --comment",
            "options": [
                OPT.author,
                OPT.comment,
            ],
        },
        "collector_show_actions": {
            "msg": "Show actions detailed log. A single action is specified "
                   "by --id. a range is specified by --begin/--end dates. "
                   "--end defaults to now. --begin defaults to 7 days ago.",
            "options": [
                OPT.begin,
                OPT.id,
                OPT.end,
            ],
        },
        "collector_list_nodes": {
            "msg": "Show the list of nodes matching the filterset pointed by "
                   ":opt:`--filterset`.",
        },
        "collector_list_services": {
            "msg": "Show the list of services matching the filterset pointed "
                   "by :opt:`--filterset`.",
        },
        "collector_list_filtersets": {
            "msg": "Show the list of filtersets available on the collector. "
                   "If specified, :opt:`--filterset <pattern>` limits the resultset "
                   "to filtersets matching the pattern.",
        },
        "collector_log": {
            "msg": "Log a message in the collector's node log.",
            "options": [
                OPT.message,
            ],
        },
        "collector_asset": {
            "msg": "Display the asset information known to the collector.",
        },
        "collector_networks": {
            "msg": "Display network information known to the collector for "
                   "each node ip, complete with network information from the "
                   "IPAM database.",
        },
        "collector_tag": {
            "msg": "Set a node tag (pointed by --tag).",
            "options": [
                OPT.tag,
            ],
        },
        "collector_untag": {
            "msg": "Unset a node tag (pointed by --tag).",
            "options": [
                OPT.tag,
            ],
        },
        "collector_show_tags": {
            "msg": "list all node tags",
        },
        "collector_list_tags": {
            "msg": "List all available tags. Use :opt:`--like` to filter the output.",
            "options": [
                OPT.like,
            ],
        },
        "collector_create_tag": {
            "msg": "Create a new tag with name specified by :opt:`--tag`.",
            "options": [
                OPT.tag,
            ],
        },
        "collector_search": {
            "msg": "Report the collector objects matching :opt:`--like "
                   "[<type>:]<substring>`, where ``<type>`` is the object type "
                   "acronym as shown in the collector search widget.",
            "options": [
                OPT.like,
            ],
        },
    },
}

DEPRECATED_OPTIONS = []

DEPRECATED_ACTIONS = [
    "collector_json_asset",
    "collector_json_networks",
    "collector_json_list_unavailability_ack",
    "collector_json_list_actions",
    "collector_json_show_actions",
    "collector_json_status",
    "collector_json_checks",
    "collector_json_disks",
    "collector_json_alerts",
    "collector_json_events",
    "collector_json_list_nodes",
    "collector_json_list_services",
    "collector_json_list_filtersets",
    "json_schedule",
]

ACTIONS_TRANSLATIONS = {
    "unfreeze": "thaw",
}

class NodemgrOptParser(OptParser):
    """
    The nodemgr-specific options parser class
    """
    def __init__(self, args=None, colorize=True, width=None, formatter=None,
                 indent=6):
        OptParser.__init__(self, args=args, prog=PROG, options=OPT,
                           actions=ACTIONS,
                           deprecated_options=DEPRECATED_OPTIONS,
                           deprecated_actions=DEPRECATED_ACTIONS,
                           actions_translations=ACTIONS_TRANSLATIONS,
                           global_options=GLOBAL_OPTS,
                           colorize=colorize, width=width,
                           formatter=formatter, indent=indent, async_actions=node.ACTION_ASYNC)

