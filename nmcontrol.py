#!/usr/bin/env python2

__version__ = '0.8'

import os
import sys
import inspect
import optparse
import ConfigParser
import traceback

app = {}
def main():
    # init app config
    global app
    app['conf'] = ConfigParser.SafeConfigParser()
    app['path'] = {}
    app['path']['app'] = os.path.dirname(os.path.realpath(__file__)) + os.sep

    # add import path
    sys.path.append(app['path']['app'] + 'lib')
    sys.path.append(app['path']['app'] + 'plugin')
    sys.path.append(app['path']['app'] + 'service')

    # add conf path
    import platformDep
    path = os.path.join(platformDep.getNmcontrolDir(), 'conf') + os.sep
    for argv in sys.argv:
        if argv.startswith("--confdir=") or argv.startswith("--main.confdir="):
            path = argv.split("=")[1]
            path = os.path.realpath(path) + os.sep
    app['path']['conf'] = path

    import common
    common.app = app

    log = common.get_logger(__name__)

    import console
    (cWidth, cHeight) = console.getTerminalSize()
    fmt=optparse.IndentedHelpFormatter(indent_increment=4, max_help_position=40, width=cWidth-3, short_first=1 )
    app['parser'] = optparse.OptionParser(formatter=fmt,description='nmcontrol %s' % __version__)
    app['debug'] = False

    # debug mode
    for argv in sys.argv:
        if argv in ['--debug=1','--main.debug=1']:
            app['debug'] = True
            log.info("DEBUG MODE")

    # init modules
    import re

    # init vars and main plugin
    app['services'] = {}
    app['plugins'] = {}
    import pluginMain
    app['plugins']['main'] = pluginMain.pluginMain('plugin')

    # init service & plugins
    for modType in ['service', 'plugin']:
        modules = os.listdir(os.path.join(app['path']['app'], modType))
        if modType == 'plugin': modules.remove('pluginMain.py')
        for module in modules:
            if re.match("^"+modType+".*.py$", module):
                module = re.sub(r'\.py$', '', module)
                modulename = re.sub(r'^'+modType, '', module).lower()
                try:
                    if app["debug"]:
                        log.info("launching", modType, module)
                    importedModule = __import__(module)
                    importedClass = getattr(importedModule, module)
                    app[modType+'s'][importedClass.name] = importedClass(modType)
                    importedClass.app = app
                except Exception as e:
                    log.info("Exception when loading "+modType, module, ":", e)
                    traceback.print_exc()

    # parse command line options
    # Note: There should not be plugins and services with the same name
    (options, app['args']) = app['parser'].parse_args()
    for option, value in vars(options).items():
        if value is not None:
            tmp = option.split('.')
            if len(tmp) == 1:
                app['plugins']['main'].conf[tmp[0]] = value
            else:
                module = tmp[0]
                tmp.remove(module)
                if module in app['plugins']:
                    app['plugins'][module].conf['.'.join(tmp)] = value
                if module in app['services']:
                    app['services'][module].conf['.'.join(tmp)] = value

    ###### Act as client : send rpc request ######
    if len(app['args']) > 0 and app['args'][0] != 'start':
        error, data = app['plugins']['rpc'].pSend(app['args'][:])
        if error is True or data['error'] is True:
            log.info("ERROR:", data)
        else:
            if data['result']['reply'] in [None, True]:
                log.info('ok')
            else:
                log.info(data['result']['reply'])
            if app['debug'] and data['result']['prints']: log.info("LOG:", data['result']['prints'])
        if app['args'][0] != 'restart':
            return

    # daemon mode
    if os.name == "nt":  # MS Windows
        log.info("Daemon mode not possible on MS Windows.")
    elif int(app['plugins']['main'].conf['daemon']) == 1:
        log.info("Entering background mode")
        import daemonize
        retCode = daemonize.createDaemon()

    ###### Act as server : start plugins ######
    plugins_started = []
    for plugin in app['plugins']:
        if int(app['plugins'][plugin].conf['start']) == 1 and plugin not in ['rpc','main']:
            # exit immediatly when main is stopped, unless in debug mode
            app['plugins'][plugin].daemon=True
            if app['plugins'][plugin].running is False:
                app['plugins'][plugin].start()
                plugins_started.append(app['plugins'][plugin].name)
    log.info("Plugins started :", ', '.join(plugins_started))

    for plugin in app['plugins']:
        if app['plugins'][plugin].__dict__.has_key("criticalStartException") and app['plugins'][plugin].criticalStartException:
            raise Exception(app['plugins'][plugin].criticalStartException)

    #services_started = []
    #for service in app['services']:
    #    if app['services'][service].running:
    #        services_started.append(app['services'][service].name)
    #print "Services started :", ', '.join(services_started)

    # stay there to catch CTRL + C and not exit when in daemon mode
    try:
        app['plugins']['main'].start2()
    except (KeyboardInterrupt, SystemExit):
        log.info('\n! Received keyboard interrupt, quitting threads.\n')

    # stop main program
    app['plugins']['main'].stop()


if __name__=='__main__':
    main()
