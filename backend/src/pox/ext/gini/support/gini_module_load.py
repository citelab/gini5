#!/usr/bin/python2

"""
gini_module_load.py

Watches a particular file for the addition of new module names. The modules
with those names are imported into POX and executed. This allows modules
to be loaded from gBuilder.
"""

from pox.core import core
import pox.lib.util as poxutil
import os, time, threading, importlib

log = core.getLogger()

class ModuleFileReader(threading.Thread):
    def __init__(self, module_file_path):
        threading.Thread.__init__(self)
        self.module_file_path = module_file_path
        self.launched_modules = []

    def run(self):
        while True:
            time.sleep(5)
            
            try:
                module_file = open(self.module_file_path, "r")
                modules = module_file.readlines()
                
                for module in modules:
                    module = module.strip()
                    if module != "" and not module in self.launched_modules:
                        log.info("gini_module_load: loading module - " + module)
                        try:
                            mod = importlib.import_module(module)
                            try:
                                mod.launch()
                            except Exception as e:
                                log.error("gini_module_load: failed to launch module - " + module)
                        except Exception as e:
                            log.error("gini_module_load: module does not exist - " + module)
                        
                        self.launched_modules.append(module)
                    
                module_file.close()
            except StandardError as e:
                pass

@poxutil.eval_args
def launch(module_file_path):
    module_file_reader = ModuleFileReader(module_file_path)
    module_file_reader.start()
