#!/usr/bin/env python
# -*- coding: utf-8 -*-

import rospy
import os, shutil
import rospkg
from DockerTub import Tub

class DnsMasqTub(Tub):
    def __init__(self):
        super(DnsMasqTub, self).__init__()
        self.rospack = rospkg.RosPack()

        self.afps("RosDnsMasqPort","ros_dnsmasq_port", default_attribute=10053)

        self.ros_msq_dir = "/tmp/ros_dnsmasq.d/"
        if not os.path.exists(self.ros_msq_dir):
            os.makedirs(self.ros_msq_dir)
        rospy.logdebug("Using auxiliary dnsmasq in {}".format(self.ros_msq_dir))
        self.update_host_list()

    def get_own_volumes(self):
        return   ["-v", "{}:/etc/dnsmasq.conf".format(self.dnsmasqfile)]

    def get_entrypoint(self):
        return []

    def update_host_list(self):
        self.generate_dnsmasqconf()
        self.restart_dnsmasq_docker()

    def generate_dnsmasqconf(self):
        self.dnsmasqfile = self.ros_msq_dir + "/dnsmasq.conf"
        shutil.copyfile(self.rospack.get_path('rosdop') + "/dnsmasq/ros-tmp-hosts", dst=self.dnsmasqfile)
        #address=/torch_machine4.poop/172.28.5.31
        with open(self.dnsmasqfile, "a") as myfile:
            myfile.write("address=/torch_machine4.poop/172.28.5.31")

    def restart_dnsmasq_docker(self):
        ##if there is a container running as dnsmasq I have to stop it
        self.close(silent = True, reset = True)
        self.create()

if __name__ == '__main__':
    try:
        dnsmasqTub = DnsMasqTub()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass