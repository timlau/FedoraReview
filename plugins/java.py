# -*- coding: utf-8 -*-
"""Java language specific checks are in a separate plugin"""

from FedoraReview import CheckBase, RegistryBase


class Registry(RegistryBase):
    ''' Register all checks in this file in group 'Java'. '''

    group = 'Java'

    def is_applicable(self):
        ''' Return True if this is a java package. '''
        if self.is_user_enabled():
            return self.user_enabled_value()
        rpms = self.checks.rpms
        return (rpms.find("*.pom") or rpms.find("pom.xml") or
                rpms.find("*.class") or rpms.find("*.jar") or
                rpms.find("*.ear") or rpms.find("*.war"))


class CheckJavaPlugin(CheckBase):
    """
    Check to warn when external plugin for reviewing Java is not installed
    """
    def __init__(self, base):
        CheckBase.__init__(self, base, __file__)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Java'
        self.text = "This seems like a Java package, please install " \
                    "fedora-review-plugin-java to get additional checks"
        self.automatic = True
        self.type = 'MUST'

    def run_on_applicable(self):
        """ Use the is_applicable() defined in main group: """
        if self.checks.is_external_plugin_installed(self.registry.group):
            self.set_passed(self.NA)
        else:
            self.set_passed(self.FAIL)

# vim: set expandtab ts=4 sw=4:
