#-*- coding: utf-8 -*-

from generic import LangCheckBase


class JavaCheckBase(LangCheckBase):
    def is_applicable(self):
        if self.has_files("*.jar") or self.has_files("*.pom"):
            return True
        else:
            return False
