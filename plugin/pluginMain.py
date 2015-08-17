from common import *
import plugin
import platform

class pluginMain(plugin.PluginThread):
    name = 'main'
    options = {
        'start':    ['Launch at startup', (1, 0)[platform.system() == 'Windows']],
        'debug':    ['Debug mode', 0, '<0|1>'],
        'daemon':    ['Background mode', 1, '<0|1>'],
        'confdir':    ['Configuration file directory', "<system conf dir>"],
        #'plugins':    ['Load only those plugins', 'main,data,rpc'],
    }

    def pStart(self):
        app['plugins']['rpc'].start2()

    def pStatus(self):
        ret = ''
        if self.running:
            ret = "Plugin " + self.name + " running"
        for plugin in app['plugins']:
            if plugin != 'main' and app['plugins'][plugin].running:
                ret += '\n' + app['plugins'][plugin].pStatus()

        return ret

    def pStop(self):
        self.running = False
        if app['debug']:    log.info("Plugin %s stopping" %(self.name))
        for plugin in app['plugins']:
            if plugin == "rpc":  # rpc plugin seems to shut down everything
                continue
            if app['plugins'][plugin].running == True:
                app['plugins'][plugin].stop()
        app['plugins']['rpc'].stop()
        log.info("Plugin %s stopped" %(self.name))

    def pRestart(self):
        self.stop()
        #self.start()

    def pLoadconfig(self):
        self.conf['start'] = 1
        if 'debug' in app:
            self.conf['debug'] = app['debug']

    def pHelp(self, args = []):
        help = plugin.PluginThread.pHelp(self, args)
        help += '\n\n'

        help += '* Available plugins :'
        for plug in app['plugins']:
            if app['plugins'][plug].running == True:
                help += '\n' + plug + ' help'

        return help

