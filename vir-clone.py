#!/usr/bin/python
#
#This program is used to clone a virt machine from remote host to localhost
#
import os,sys,getopt,subprocess
import libvirt

def copy_image(ipath,opath,to_address,pool,from_address,identify_key,remoteflag):
    temp = ipath.split('/')
    filename = temp.pop()
    filename = filename.split('.')
    Extension = '.' + filename.pop()
    filename = '.'.join(filename) + '-clone'
    vol_list = pool.listVolumes()
    clash = 1
    count = 0
    finalname = filename + Extension
    while clash:
        if finalname in vol_list:
            count +=1
            finalname = filename + '_%d'%count +Extension
        else:
            if from_address == '':
                print 'Copying the images file: '+ 'localhost:'+ ipath
            else:
                print 'Copying the images file: '+ from_address +':'+ ipath
            if to_address == '':
                print 'to: '+'localhost:' +opath + '/' + finalname
            else:
                print 'to: '+ to_address + ':' +opath + '/' + finalname
            print 'Please wait ...\n'

            if to_address == '':
                if from_address == '':   
                    subprocess.call(['cp',ipath,opath+'/'+finalname]) 
                else:
                    if identify_key == '':
                        subprocess.call(['scp',from_address+':'+ipath,opath+'/'+finalname])
                    else:
                        subprocess.call(['scp','-i',identify_key,from_address+':'+ipath,opath+'/'+finalname])
            else:
                if from_address == '':
                    if remoteflag:
                        if dentify_key == '':   
                            subprocess.call(['scp',ipath,to_address+':'+opath+'/'+finalname])
                        else:
                            subprocess.call(['scp','-i',identify_key,ipath,to_address+':'+opath+'/'+finalname])
                    else:
                        if dentify_key == '':
                            subprocess.call(['ssh',to_address,'cp '+ipath+' '+opath+'/'+finalname])
                        else:
                            subprocess.call(['ssh','-i',identify_key,to_address,'cp '+ipath+' '+opath+'/'+finalname])
                else:
                    if dentify_key == '':
                        subprocess.call(['ssh',to_address,'scp '+from_address+':'+ipath+' '+opath+'/'+finalname])
                    else:
                        subprocess.call(['ssh',to_address,'scp -i'+identify_key+' '+from_address+':'+ipath+' '+opath+'/'+finalname])
            clash = 0

    pool.refresh(0)
    try:
        pool.storageVolLookupByName(finalname)
    except:
        print 'Copy VM images failed.'
        sys.exit(2)
    return [ipath,opath+'/'+finalname]

class Disk:
    def __init__(self,diskxml):
        self.path = self.__getpath(diskxml)
        self.name = self.__getname()
        self.shareable = self.__isShareable(diskxml)
    def __getpath(self,diskxml):
        temp = diskxml.split("<source file='")[1]
        path = temp.split("'/>")[0]
        return path
    def __getname(self):
        temp = self.path.split('/')
        name = temp.pop()
        return name
    def __isShareable(self,diskxml):
        if diskxml.count('<shareable/>') == 0:
            return 0
        else:
            return 1

class DomainInfo:
    def __init__(self,VirDomain):
        self.VirDomain = VirDomain
        self.domainxml = VirDomain.XMLDesc(0)
        self._disks = self.__getDisks()
        self.path_list = self.__get_path_list()
        self.canRead = self.__canRead()

    def __get_path_list(self):
        path_list = []
        for disk in self._disks:
            path_list.append(disk.path)
        return path_list
    
    def __getDiskXMLList(self):
        diskxml_list = []
        xml = self.domainxml
        temp_list = xml.split("<disk type='file' device='disk'>")
        del temp_list[0]
        for temp in temp_list :
            diskxml_list.append(temp.split('</disk>')[0])
        return diskxml_list

    def __getDisks(self):
        disks = []
        xml_list = self.__getDiskXMLList()
        for xml in xml_list:
            disks.append(Disk(xml))
        return disks                          

    def __canRead(self):
        canread = 1
        if self.domainxml.count("<disk type='file' device='disk'>") == 0:
            return 0
        if self.VirDomain.isActive() == 0:
            return 1
        for disk in self._disks:
            if disk.shareable:
                pass
            else:
                canread = 0
        return canread

def modifyxml(xml,newname,remote = 0):
    xml = xml[:xml.find('<name>')+6] + newname + xml[xml.find('</name>'):]
    xml = xml[:xml.find('<uuid>')] + xml[xml.find('</uuid>')+9:]
    if remote:
        temp = xml.split('</interface>')
        networkxml = '''
    <interface type='network'>
        <source network='default'/>
    </interface>
'''
        xml = xml[:xml.find('<interface ')] + networkxml + temp.pop()
    else:
        pass

    return xml    
    
def main(iURI,oURI,VMName,PoolName,newVMName = '',dentify_key = ''):
####################################connect############################################
    iconn = libvirt.open(iURI)
    domain = iconn.lookupByName(VMName)
#connect and check the VM
    domaininfo = DomainInfo(domain)
    if domaininfo.canRead == 0 :
        print "Can not copy the Disk images,please shutdown the domain or change all disk of it to shareable before clone"
        sys.exit(2)

#connect an check the pool
    if oURI == '':
        oURI = iURI
    oconn = libvirt.open(oURI)

    pool = oconn.storagePoolLookupByName(PoolName)
    if pool.isActive()==1:
        pass
    else:
        print "The Storage Pool is not Active,can not clone to it."
        sys.exit(2)
    pool.refresh(0)
    poolxml = pool.XMLDesc(0)    

###################################copy image and change the image path in the xmldoc###########
    temp = poolxml.split('<path>')[1]
    pool_path = temp.split('</path>')[0]
    new_xml = domaininfo.domainxml
    if iURI == oURI:
        from_address = ''
        i_dentify_key = ''
        remote = 0
    else:
        if iURI in ('qemu:///system','xen:///'):
            from_address = ''
            remote = 1
        else:
            from_address = iURI[iURI.find('://')+3:].split('/')
            from_address = from_address[0]
            remote = 1
    if oURI in ('qemu:///system','xen:///'):
        to_address = ''
    else:
        to_address = oURI[oURI.find('://')+3:].split('/')
        to_address = to_address[0]
    if from_address == '':
        if to_address == '':
            i_dentify_key = ''
        else:
            i_dentify_key = dentify_key
    else:
        if dentify_key == '':
            i_dentify_key = ''
        else:
            if to_address =='':
                i_dentify_key = dentify_key
            else:
                i_dentify_key = '/tmp/.i_dentify_key'
                subprocess.call(['scp',dentify_key,to_address+':'+i_dentify_key])
    for path in domaininfo.path_list:
        path_changelog = copy_image(path,pool_path,to_address,pool,from_address,i_dentify_key,remote)
        new_xml = new_xml.replace(path_changelog[0],path_changelog[1])
    if i_dentify_key == '':
        pass
    else:
        if to_address == '' or from_address == '':
            pass
        else:
            subprocess.call(['ssh','-i',dentify_key,to_address,'rm -rf '+i_dentify_key])
       
##########################################change the domain name and some other thing in the xmldoc##################################
    if newVMName == '':
        newVMName = VMName + '-clone'
    count = 0
    clash = 1
    finalname = newVMName
    domainlist = oconn.listDefinedDomains()
    while clash:
        if finalname in domainlist:
            count += 1
            finalname = newVMName + '(%d)' % count
        else:
            clash = 0
    domainxml = modifyxml(new_xml,finalname)

################################################define the Domain###########################################
    oconn.defineXML(domainxml)
    print 'Clone Complete!'
    print 'The new Virtual Machine Name is [%s]' % finalname
    return 0

if __name__ == '__main__':
    oURI = ''
    poolname = 'default'
    network = 'default'
    newname = ''
    dentify_key = ''
    helpinfo = '''Please give some arguments like this:
vir-clone [-o toURI] [-p pool] [-n network] [-N newName] [-i dentify_key] URI/VMname

Example: 
    vir-clone -i ~/.ssh/id_rsa -o qemu+ssh://192.168.8.85/system qemu+ssh://192.168.8.84/system/winxp

URI 
    The libvirt URI of the host you want to clone from

VMname
    The Virtual Machine's Name

-o 
    The libvirt URI of the host you want to clone to
    Default value is: -o toURI ( toURI = URI )

-i
    The identify key file's path ,if not given it ,you should input the password several times

-p 
    The storage pool's name which you want save the disk image of the clone Virtual Machine
    Default value is: -p default

-n
    No Features
    will comply later

-N 
    defined a new name of the Virtula Machine ,if not given it,The name will be VMname-clone
'''
    if len(sys.argv) < 2:
        print helpinfo
    argv = sys.argv[1:]
    try:
        opts, args = getopt.getopt(argv,"ho:p:n:N:i:",['help'])
    except getopt.GetoptError:
        print helpinfo
        sys.exit(2)
    for opt, arg in opts:
        if opt in ('-h','--help'):
            print helpinfo
            sys.exit(2)
        elif opt in ('-o'):      
            oURI = arg
        elif opt in ('-p'):
            poolname = arg
        elif opt in ('-n'):
            network = arg
        elif opt in ('-N'):
            newname = arg
        elif opt in ('-i'):
            dentify_key = arg
        else:
            pass
    try:
        args[0]
    except:
        print 'Please give a Virtual Machine URL to clone it'
        sys.exit(2)
    temp = args[0].split('/')
    VMname = temp.pop()
    iURI = '/'.join(temp)
    main(iURI,oURI,VMname,poolname,newname,dentify_key)

