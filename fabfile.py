import time
from datetime import datetime
from fabric.api import env, local, lcd, roles, run, parallel, cd, put, execute, settings, shell_env, abort, hide, task, prefix
#------------------------------------------------------------------------------
# Author: Daniel Porto  - d.porto@gsd.inesc-id.pt
# Last Update: may, 2 2018
#------------------------------------------------------------------------------


#------------------------------------------------------------------------------
#environment variables
#------------------------------------------------------------------------------
# force read configuration in .ssh/config
env.use_ssh_config=True 
# create a new ssh configuration with proxyjump support
ssh_config_file = "~/.ssh/cloudtm"
ssh_head_node = "inesc-head"  #ip or ssh config name for the headnode
ssh_identity_file = "~/.ssh/key_openstack.pem"



# cloud properties ------------------------------------------------------------
# | ID  | Name           | Memory_MB | Disk | Ephemeral | Swap | VCPUs | RXTX_Factor | Is_Public | extra_specs |
# | 141 | m4.large       | 8192      | 20   | 0         |      | 2     | 1.0         | True      | {}          |
# | 134 | m4.xlarge      | 16384     | 30   | 0         |      | 4     | 1.0         | True      | {}          |
# | 135 | m4.2xlarge     | 32768     | 40   | 0         |      | 8     | 1.0         | True      | {}          |
cloud_flavor="141"
#  cloud images: centos7, kaioken-kernel-3.10 , kaioken-kernel-4.14 ,  kaioken-kernel-4.15  
cloud_image="kaioken-kernel-4.15"
cloud_keyname="key_openstack"
cloud_availability_zones=["node01","node02","node03","node04","node05","node06","node07","node08","node09","node10"]

# cloud credentials
cloud_url="http://10.100.0.21:5000/v2.0"
tenant_id="XXXX"
tenant_name="YYY"
tenant_user="YYYY"
tenant_pw="PPPP"


# define the number of instances to create
clients = 5



# nodes are from ssh config file or you can place the IPS directly
env.roledefs={
    'headnode': ['inesc-head'],
    'manager' : ['172.10.0.12'],
    'replicas' : ['172.10.0.20','172.10.0.21','172.10.0.22'],
}

#------------------------------------------------------------------------------
# internal tasks
#------------------------------------------------------------------------------
@task
@parallel
@roles('headnode', 'replicas', 'manager')
def check_storage():
    with hide('commands'):
        str1 = run("df -h ")
        time.sleep(5)
        print"node "+env.host_string+" storage: "+str1

@task
@parallel
@roles('headnode', 'replicas', 'manager')
def check_load():
    with hide('commands'):
        str1 = run("uptime")
        time.sleep(5)
        print"node "+env.host_string+" load:"+str1
   

#------------------------------------------------------------------------------
# cluster management tasks
#------------------------------------------------------------------------------
@task
@roles('headnode')
def list_clients():
    with hide('commands'), shell_env(OS_AUTH_URL=cloud_url,OS_TENANT_ID=tenant_id,\
        OS_TENANT_NAME=tenant_name,OS_USERNAME=tenant_user,OS_PASSWORD=tenant_pw,\
        OS_NO_CACHE="1"):
        str1 = run("nova list")
        if (len(str1)==0):
            print "There is no client running at openstack!"
        else: 
            print str1

@task
@roles('headnode')
def launch_client_instances():
    with hide('commands'), shell_env(OS_AUTH_URL=cloud_url,OS_TENANT_ID=tenant_id,\
        OS_TENANT_NAME=tenant_name,OS_USERNAME=tenant_user,OS_PASSWORD=tenant_pw,\
        OS_NO_CACHE="1"):
        for i in range(clients):
            command = "nova boot"
            command += " --image "+cloud_image
            command += " --flavor="+cloud_flavor
            command += " --key-name "+cloud_keyname
            command += " client"+str(i) # instance name
            command += " --availability-zone nova:"+cloud_availability_zones[i]
            print command
            str1 = run(command)
            print str1

@task
@roles('headnode')
def list_failed_clients():
    with hide('commands'), shell_env(OS_AUTH_URL=cloud_url,OS_TENANT_ID=tenant_id,\
        OS_TENANT_NAME=tenant_name,OS_USERNAME=tenant_user,OS_PASSWORD=tenant_pw,\
        OS_NO_CACHE="1"):
        str1 = run("nova list | grep ERROR")
        if (len(str1)==0):
            print "There is no client running at openstack!"
        else: 
            print str1

@task
@roles('headnode')
def terminate_failed_clients():
    with hide('commands'), shell_env(OS_AUTH_URL=cloud_url,OS_TENANT_ID=tenant_id,\
        OS_TENANT_NAME=tenant_name,OS_USERNAME=tenant_user,OS_PASSWORD=tenant_pw,\
        OS_NO_CACHE="1"):
        try: 
            str1 = run("nova list | grep ERROR")
        except:
            print "There is no failed client running at openstack!"
            return

        if len(str1)> 0:
            clients = str1.split("\n")
            for client in clients:
                client_id = client.split(" ")[1]
                print client_id
                command = "nova delete "+ client_id
                run(command)

@task
@roles('headnode')
def terminate_all_clients():
    with hide('commands'), shell_env(OS_AUTH_URL=cloud_url,OS_TENANT_ID=tenant_id,\
        OS_TENANT_NAME=tenant_name,OS_USERNAME=tenant_user,OS_PASSWORD=tenant_pw,\
        OS_NO_CACHE="1"):
        try: 
            str1 = run("nova list | grep '|' | grep -v Status")
        except:
            print "There is no client running at openstack!"
            return

        if len(str1)> 0:
            clients = str1.split("\n")
            for client in clients:
                client_id = client.split(" ")[1]
                print client_id
                command = "nova delete "+ client_id
                run(command)

@task
@roles('headnode')
def list_client_ips():
    with hide('commands'), shell_env(OS_AUTH_URL=cloud_url,OS_TENANT_ID=tenant_id,\
        OS_TENANT_NAME=tenant_name,OS_USERNAME=tenant_user,OS_PASSWORD=tenant_pw,\
        OS_NO_CACHE="1"):
        try: 
            str1 = run("nova list | grep net")
        except:
            print "There is no failed client running at openstack!"
            return

        if len(str1)> 0:
            clients = str1.split("\n")
            for client in clients:
                output = client.replace("|"," ") 
                output = " ".join(output.split()) # remove white spaces within the string
                output = output.split(" ") # properly separate fields of the string
                #print output
                client_id = output[0]
                client_name = output[1]
                client_ip = output[3].split("=")[1]
                print client_id, client_name, client_ip
                # command = "nova delete "+ client_id
                # run(command)




@task
@roles('headnode')
def generate_client_sshconfig():
    with hide('commands'), shell_env(OS_AUTH_URL=cloud_url,OS_TENANT_ID=tenant_id,\
        OS_TENANT_NAME=tenant_name,OS_USERNAME=tenant_user,OS_PASSWORD=tenant_pw,\
        OS_NO_CACHE="1"):
        try: 
            str1 = run("nova list | grep net")
        except:
            print "There is no failed client running at openstack!"
            return

        if len(str1)> 0:
            clients = str1.split("\n")
            print "Writing this output to "+ssh_config_file+" for local ssh connection and generating ansible inventory"

           # initialize ssh configuration
            local("echo '' > "+ssh_config_file)
            entry=list()
            client_list=list()
            client_list_ip=list()
            for client in clients:
                output = client.replace("|"," ") 
                output = " ".join(output.split()) # remove white spaces within the string
                output = output.split(" ") # properly separate fields of the string
                print output
                client_name = output[1]
                client_ip = output[3].split("=")[1]
                client_list.append(client_name)
                client_list_ip.append(client_ip)
                print "Ping node",client_ip,"to activate..."
                run("ping -c3 "+client_ip) # just to ativate the node
                entry.append("Host "+ client_name)
                entry.append("    proxyjump "+ssh_head_node)
                entry.append("    hostname "+ client_ip)
                entry.append('    identityfile "'+ssh_identity_file+'"')
                entry.append("    user centos")
                entry.append("    port 22")
                entry.append("    StrictHostKeyChecking no")

            for line in entry:
                local("echo '"+line+"' >> "+ssh_config_file)
            print "Update this file with the following client list:"
            print client_list_ip
            print "you can ssh directly to the nodes from your machine:"
            print "ssh ",client_list[0]



@roles('headnode')
def get_client_ip_list():
    client_ips = list()
    with hide('commands'), shell_env(OS_AUTH_URL=cloud_url,OS_TENANT_ID=tenant_id,\
    OS_TENANT_NAME=tenant_name,OS_USERNAME=tenant_user,OS_PASSWORD=tenant_pw,\
    OS_NO_CACHE="1"):
        try: 
            str1 = run("nova list | grep net")
        except:
            print "There is no failed client running at openstack!"
            return

        if len(str1)> 0:
            clients = str1.split("\n")
            for client in clients:
                output = client.replace("|"," ") 
                output = " ".join(output.split()) # remove white spaces within the string
                output = output.split(" ") # properly separate fields of the string
                client_ip = output[3].split("=")[1] # get client ip
                client_ips.append(client_ip)
    return client_ips

@task
@roles('headnode')
def ping_clients():
    clients = get_client_ip_list()
    for client_ip in clients:
        out = run("ping -c2 "+client_ip) # just to ativate the node
        print "Ping node",client_ip,"to activate:", out.split("\n")[-1]

         
#------------------------------------------------------------------------------
# public tasks
#------------------------------------------------------------------------------
def __public_tasks():
    pass


@task
@roles('headnode') 
def check_headnode():
    run("uptime")


