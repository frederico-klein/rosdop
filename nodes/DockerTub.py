#!/usr/bin/env python
# -*- coding: utf-8 -*-

### this should be a bunch of shell scripts. IDK what I am doing.

## creates the bridge.

import rospy
from utils import DockerLoggedNamed
from docker_master import DockerMasterInterface as DMI

def flatten(nl):
    listA = []
    for item in nl:
        if isinstance(item,list):
            listA.extend(flatten(item))
        else:
            listA.append(item)
    return listA


class Tub(DockerLoggedNamed):
    """
    This can be invoked with something like:
    from DockerTub import Tub

    myTub = Tub(name="tub0")
    myTub.build()
    myTub.start()

    or launched as a node with parameters from a launch file, with the same names.

    """
    def __init__(self,
            name=                   "tub0"          ,
            imagename=              "tch_new"       ,
            network_name=           "br0"           ,
            tub_volume=             "tubvolume0"    ,
            container_hostname=               "torch_machine4",
            dockerfile_directory=   "."             ,
            containerip=              "172.28.5.31",
            use_gpu=                "True",
            dns_check = True):
        super(Tub, self).__init__()
        self.Name = name
        self.NetworkName = network_name
        self.ImageName = imagename
        self.TubVolume = tub_volume
        self.TubName = container_hostname
        self.DockerfileDirectory = dockerfile_directory
        self.IP = containerip
        self.UseGpu = use_gpu
        self.DnsCheck = dns_check

        rospy.init_node('docker_tub', anonymous=True, log_level=rospy.DEBUG)

        self.updateHostName()
        self.post_init()

    def updateBuild(self):
        ## this no longer works for some builds where I wanted nvidia to be present during the build to detect the graphics card and know what to do. I am not 100% sure it ever worked, so it is a maybe on the todo list
        rospy.loginfo("Starting build process...")
        self.lspPopen(['docker','build',"-t",
            self.ImageName,
            self.DockerfileDirectory
            ])

    def post_init(self):
        rospy.logwarn("started post_init")
        ## I want to read the private parameters here, since I already started the node, so I catkin_ws
        ## this is the best I could do with python 2.7 and my python fu

        self.afps("Name"        ,"name"          )
        self.afps("ImageName"   ,"imagename"     )
        self.afps("NetworkName" ,"network_name"  )
        self.afps("TubVolume"   ,"tub_volume"    )
        self.afps("TubName"     ,"container_hostname")
        self.afps("UseGpu"      ,"use_gpu")
        # self.afps("attachOwnHostNameToDockerNames", "hostname_as_suffix")

        self.DMI = DMI(2, dns_check = self.DnsCheck)
        ###here I need to get the TubVolume's properies.
        try:
            ##the way I am using this, volumes are all local
            self.WsPath = self.DMI.get_ws_volume_by_name(self.TubVolume+"."+self.ownHostName, tries = 1)
        except:
            rospy.loginfo("Could not get tubvolume path. Will not mount or fail.")
        #self.Display = ":0"

        self.afps("DockerfileDirectory"  , "dockerfile_directory")
        self.afps("IP"                   , "containerip"           )

        rospy.logwarn("trying to add host to HostList")

        self.DMI.addHost(self.TubName, self.ownHostName, self.IP)
        rospy.loginfo("Added host to DMI OK.")

    def create(self):
        rospy.loginfo("Mounting docker image {}".format(self.Name))

        ##check if there is a volume already
        output = self.oLspPopen(['docker','ps'])

        if self.Name in output: #if there isn't create one
            rospy.logwarn("found {} docker container found.".format(self.Name))
        else:

            ## I guess it cant be interactive this time. for interaction we will rely on sshd working
            rospy.loginfo("Docker container not found. Creating one. ")
            proc_list = ['docker','run',self.get_use_gpu(),
                 #"--rm",
                 #"-it",
                 "--name", self.Name,
                 "-t","-d",
                 "-u","root",
                 #"-e","DISPLAY=$DISPLAY",
                 #"-v","/tmp/.X11-unix:/tmp/.X11-unix",
                 self.get_own_volumes(),
                 "-h","{}".format(self.TubName+"."+self.ownHostName),
                 "--network={}".format(self.NetworkName),
                 "--ip={}".format(self.IP),
                 self.get_dns(),
                 self.ImageName,
                 self.get_entrypoint()
             ]
            #print(self.FullName())
            #print(flatten(proc_list))
            self.lspPopen(flatten(proc_list))
        rospy.on_shutdown(self.close)

    def get_dns(self):
        if self.DMI.master.UseDnsMasq:
            return ["--dns",self.DMI.dnsmasqIP]
        else:
            return []

    def get_use_gpu(self):
        if self.UseGpu:
            return ["--gpus",'"device=0"']
        else:
            return []

    def get_own_volumes(self):
        return   ["-v","{}:{}".format(self.TubVolume,self.WsPath),
                 "-v","/mnt/share:/mnt/share"]

    def get_entrypoint(self):
        return ["bash"]

    def close(self, silent = False, reset = False):
        if not silent:
            rospy.loginfo("Starting shutting down sequence for {}.".format(self.FullName()))
        if not reset:
            try:
                self.DMI.rmHost(self.TubName, self.ownHostName)
            except:
                rospy.logwarn("Could not remove host from Docker Master host list. Some docker containers, volumes or bridge may be dangling!")

        output = self.oLspPopen(['docker','ps'])

        if self.FullName() in output: #if there isn't create one
            rospy.loginfo("Found {} docker container found to be running. Now stopping... ".format(self.FullName()))
            ##docker stop kill or rm???
            self.lspPopenRetry(['docker','stop',self.FullName()])
            rospy.loginfo("Stop okay.")
        elif silent:
            pass
        else:
            rospy.logerr("Docker container {} already closed!! There are issues with the container initialization or persistence.".format(self.FullName()))

        output = self.oLspPopen(['docker','container','ls','-a'])

        if self.FullName() in output: #if there isn't create one
            rospy.loginfo("Found {} docker container found. Now deleting... ".format(self.FullName()))
            ##docker stop kill or rm???
            self.lspPopenRetry(['docker','rm',self.FullName()])
            rospy.loginfo("Delete okay. Bye!")
        elif silent:
            pass
        else:
            rospy.logerr("Unexpected. Docker container {} already deleted.".format(self.FullName()))

if __name__ == '__main__':
    try:
        myTub = Tub()
        myTub.create()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
